import unittest

import os
import time
import wsgiref.util

from zope.interface.verify import verifyClass
from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IAuthenticator
from repoze.who.interfaces import IChallenger

from cornice.auth.whoauth.digestauth import DigestAuthPlugin, make_plugin
from cornice.auth.whoauth.digestauth import SignedNonceManager
from cornice.auth.whoauth.digestauth import parse_auth_header,\
                                            calculate_digest_response,\
                                            calculate_pwdhash,\
                                            validate_digest_parameters,\
                                            validate_digest_uri

from cornice.auth.whoauth.tests.helpers import make_environ, get_response


def get_password(username):
    return username


def get_pwdhash(username, realm):
    return calculate_pwdhash(username, username, realm)


def get_challenge(plugin, environ):
    """Get a new digest-auth challenge from the plugin."""
    for name, value in plugin.forget(environ, {}):
        if name == "WWW-Authenticate":
            return parse_auth_header(value)
    raise ValueError("plugin didn't issue a challenge")


def build_response(environ, params, username, password, **kwds):
    """Build a response to the digest-auth challenge."""
    params = params.copy()
    # remove qop from the challenge parameters.
    params.pop("qop", None)
    params.update(kwds)
    params.setdefault("username", username)
    params.setdefault("uri", wsgiref.util.request_uri(environ))
    # do qop=auth unless specified otherwise in kwds
    params.setdefault("qop", "auth")
    if not params["qop"]:
        del params["qop"]
    else:
        params.setdefault("cnonce", os.urandom(8).encode("hex"))
        params.setdefault("nc", "0000001")
    resp = calculate_digest_response(environ, params, password=password)
    params["response"] = resp
    authz = ",".join('%s="%s"' % v for v in params.iteritems())
    environ["HTTP_AUTHORIZATION"] = "Digest " + authz
    return params


class EasyNonceManager(object):
    """NonceManager that thinks everything is valid."""

    def generate_nonce(self, environ):
        return "aaa"

    def is_valid_nonce(self, nonce, environ):
        return True

    def get_next_nonce(self, nonce, environ):
        return nonce + "a"

    def get_nonce_count(self, nonce):
        return None

    def set_nonce_count(self, nonce, nc):
        return None


class TestDigestAuthPlugin(unittest.TestCase):
    """Testcases for the main DigestAuthPlugin class."""

    def test_implements(self):
        verifyClass(IIdentifier, DigestAuthPlugin)
        verifyClass(IAuthenticator, DigestAuthPlugin)
        verifyClass(IChallenger, DigestAuthPlugin)

    def test_make_plugin(self):
        def ref(class_name):
            return __name__ + ":" + class_name
        plugin = make_plugin(realm="test",
                             nonce_manager=ref("EasyNonceManager"),
                             domain="http://example.com",
                             get_pwdhash=ref("get_pwdhash"),
                             get_password=ref("get_password"))
        self.assertEquals(plugin.realm, "test")
        self.assertEquals(plugin.domain, "http://example.com")
        self.failUnless(isinstance(plugin.nonce_manager, EasyNonceManager))
        self.failUnless(plugin.get_pwdhash is get_pwdhash)
        self.failUnless(plugin.get_password is get_password)

    # Tests for various cases in the identify() method.

    def test_identify_with_no_authz(self):
        plugin = DigestAuthPlugin("test")
        environ = make_environ()
        identity = plugin.identify(environ)
        self.assertEquals(identity, None)

    def test_identify_with_non_digest_authz(self):
        plugin = DigestAuthPlugin("test")
        environ = make_environ(HTTP_AUTHORIZATION="Basic lalalala")
        identity = plugin.identify(environ)
        self.assertEquals(identity, None)
        environ = make_environ(HTTP_AUTHORIZATION="BrowserID assertion=1234")
        identity = plugin.identify(environ)
        self.assertEquals(identity, None)

    def test_identify_with_invalid_params(self):
        plugin = DigestAuthPlugin("test")
        environ = make_environ(HTTP_AUTHORIZATION="Digest realm=Sync")
        self.assertEquals(plugin.identify(environ), None)

    def test_identify_with_mismatched_uri(self):
        plugin = DigestAuthPlugin("test")
        environ = make_environ(PATH_INFO="/path_one")
        params = get_challenge(plugin, environ)
        build_response(environ, params, "tester", "testing")
        self.assertNotEquals(plugin.identify(environ), None)
        environ["PATH_INFO"] = "/path_two"
        self.assertEquals(plugin.identify(environ), None)

    def test_identify_with_bad_noncecount(self):
        plugin = DigestAuthPlugin("test", get_password=lambda u: "testing")
        environ = make_environ(REQUEST_METHOD="GET", PATH_INFO="/one")
        # Do an initial auth to get the nonce.
        params = get_challenge(plugin, environ)
        build_response(environ, params, "tester", "testing", nc="01")
        self.assertNotEquals(plugin.identify(environ), None)
        # Authing without increasing nc will fail.
        environ = make_environ(REQUEST_METHOD="GET", PATH_INFO="/two")
        build_response(environ, params, "tester", "testing", nc="01")
        self.assertEquals(plugin.identify(environ), None)
        # Authing with a badly-formed nc will fail
        environ = make_environ(REQUEST_METHOD="GET", PATH_INFO="/two")
        build_response(environ, params, "tester", "testing", nc="02XXX")
        self.assertEquals(plugin.identify(environ), None)
        # Authing with a badly-formed nc will fail
        environ = make_environ(REQUEST_METHOD="GET", PATH_INFO="/two")
        build_response(environ, params, "tester", "testing", nc="02XXX")
        self.assertEquals(plugin.identify(environ), None)
        # Authing with increasing nc will succeed.
        environ = make_environ(REQUEST_METHOD="GET", PATH_INFO="/two")
        build_response(environ, params, "tester", "testing", nc="02")
        self.assertNotEquals(plugin.identify(environ), None)

    # Tests for various cases in the authenticate() method.

    def test_rfc2617_example(self):
        plugin = DigestAuthPlugin("test", nonce_manager=EasyNonceManager())
        # Calculate the response according to the RFC example parameters.
        environ = make_environ(REQUEST_METHOD="GET",
                               PATH_INFO="/dir/index.html")
        password = "Circle Of Life"
        params = {"username": "Mufasa",
                  "realm": "testrealm@host.com",
                  "nonce": "dcd98b7102dd2f0e8b11d0f600bfb0c093",
                  "uri": "/dir/index.html",
                  "qop": "auth",
                  "nc": "00000001",
                  "cnonce": "0a4f113b",
                  "opaque": "5ccc069c403ebaf9f0171e9517f40e41"}
        resp = calculate_digest_response(environ, params, password=password)
        # Check that it's as expected
        self.assertEquals(resp, "6629fae49393a05397450978507c4ef1")
        # Check that we can auth using it.
        params["response"] = resp
        authz = ",".join('%s="%s"' % v for v in params.iteritems())
        environ["HTTP_AUTHORIZATION"] = "Digest " + authz
        identity = plugin.identify(environ)
        self.assertEquals(identity["username"], "Mufasa")

    def test_auth_good_post(self):
        plugin = DigestAuthPlugin("test", get_password=lambda u: "testing")
        environ = make_environ(REQUEST_METHOD="POST", PATH_INFO="/do/stuff")
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing")
        self.assertNotEquals(plugin.authenticate(environ, params), None)

    def test_auth_good_get_with_vars(self):
        pwdhash = calculate_pwdhash("tester", "testing", "test")
        plugin = DigestAuthPlugin("test", get_pwdhash=lambda u, r: pwdhash)
        environ = make_environ(REQUEST_METHOD="GET", PATH_INFO="/hi?who=me")
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing")
        self.assertNotEquals(plugin.authenticate(environ, params), None)

    def test_auth_good_legacy_mode(self):
        plugin = DigestAuthPlugin("test", get_password=lambda u: "testing")
        environ = make_environ(REQUEST_METHOD="GET", PATH_INFO="/legacy")
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing", qop=None)
        self.failIf("qop" in params)
        self.assertNotEquals(plugin.authenticate(environ, params), None)

    def test_auth_good_authint_mode(self):
        plugin = DigestAuthPlugin("test", get_password=lambda u: "testing")
        environ = make_environ(REQUEST_METHOD="GET", PATH_INFO="/authint",
                               HTTP_CONTENT_MD5="1B2M2Y8AsgTpgAmY7PhCfg==")
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing",
                                qop="auth-int")
        self.assertNotEquals(plugin.authenticate(environ, params), None)

    def test_auth_with_no_identity(self):
        plugin = DigestAuthPlugin("test", get_password=lambda u: "testing")
        environ = make_environ()
        self.assertEquals(plugin.authenticate(environ, {}), None)

    def test_auth_with_different_realm(self):
        plugin = DigestAuthPlugin("test", get_password=lambda u: "testing")
        environ = make_environ()
        params = get_challenge(plugin, environ)
        params["realm"] = "other-realm"
        params = build_response(environ, params, "tester", "testing")
        self.assertEquals(plugin.authenticate(environ, params), None)

    def test_auth_with_no_password_callbacks(self):
        plugin = DigestAuthPlugin("test")
        environ = make_environ()
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing")
        self.assertEquals(plugin.authenticate(environ, params), None)

    def test_auth_with_bad_digest_response(self):
        plugin = DigestAuthPlugin("test", get_password=lambda u: "testing")
        environ = make_environ()
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing")
        params["response"] += "WRONG"
        self.assertEquals(plugin.authenticate(environ, params), None)

    def test_auth_with_unknown_qop(self):
        plugin = DigestAuthPlugin("test", get_password=lambda u: "testing")
        environ = make_environ()
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing")
        params["qop"] = "super-duper"
        self.assertEquals(plugin.identify(params), None)
        self.assertRaises(ValueError, plugin.authenticate, environ, params)

    def test_auth_with_failed_password_lookup(self):
        plugin = DigestAuthPlugin("test", get_pwdhash=lambda u, r: None)
        environ = make_environ()
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing")
        self.assertEquals(plugin.identify(params), None)
        self.assertRaises(ValueError, plugin.authenticate, environ, params)

    def test_auth_with_missing_nonce(self):
        plugin = DigestAuthPlugin("test", get_password=lambda u: "testing")
        environ = make_environ()
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing")
        del params["nonce"]
        self.assertEquals(plugin.identify(params), None)
        self.assertRaises(KeyError, plugin.authenticate, environ, params)

    def test_auth_with_invalid_content_md5(self):
        plugin = DigestAuthPlugin("test", get_password=lambda u: "testing")
        environ = make_environ(REQUEST_METHOD="GET", PATH_INFO="/authint",
                               HTTP_CONTENT_MD5="1B2M2Y8AsgTpgAmY7PhCfg==")
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing",
                                qop="auth-int")
        environ["HTTP_CONTENT_MD5"] = "8baNZjN6gc+g0gdhccuiqA=="
        self.assertEquals(plugin.authenticate(environ, params), None)

    # Tests for various cases in the remember() method.

    def test_remember_with_no_identity(self):
        plugin = DigestAuthPlugin("test")
        environ = make_environ()
        self.assertEquals(plugin.remember(environ, {}), None)

    def test_remember_with_no_next_nonce(self):
        plugin = DigestAuthPlugin("test")
        environ = make_environ()
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing")
        self.assertEquals(plugin.remember(environ, params), None)

    def test_remember_with_next_nonce(self):
        plugin = DigestAuthPlugin("test", nonce_manager=EasyNonceManager())
        environ = make_environ()
        params = get_challenge(plugin, environ)
        params = build_response(environ, params, "tester", "testing")
        headers = plugin.remember(environ, params)
        self.assertEquals(headers[0][0], "Authentication-Info")

    # Tests for various cases in the challenge() method.

    def test_challenge(self):
        plugin = DigestAuthPlugin("test")
        environ = make_environ()
        app = plugin.challenge(environ, "401 Unauthorized", [], [])
        self.assertNotEqual(app, None)
        response = get_response(app, environ)
        self.failUnless(response.startswith("401 Unauthorized"))
        self.failUnless("WWW-Authenticate: Digest" in response)

    def test_challenge_with_extra_headers(self):
        plugin = DigestAuthPlugin("test")
        environ = make_environ()
        app_headers = [("X-Test-One", "test1")]
        forget_headers = [("X-Test-Two", "test2")]
        app = plugin.challenge(environ, "401 Unauthorized",
                               app_headers, forget_headers)
        self.assertNotEqual(app, None)
        response = get_response(app, environ)
        self.failUnless(response.startswith("401 Unauthorized"))
        self.failUnless("WWW-Authenticate: Digest" in response)
        self.failUnless("X-Test-One" in response)
        self.failUnless("test1" in response)
        self.failUnless("X-Test-Two" in response)
        self.failUnless("test2" in response)

    def test_challenge_with_other_status(self):
        plugin = DigestAuthPlugin("test")
        environ = make_environ()
        app = plugin.challenge(environ, "200 OK", [], [])
        self.assertNotEqual(app, None)
        response = get_response(app, environ)
        self.failUnless(response.startswith("401 Unauthorized"))

    def test_challenge_with_stale_nonce(self):
        plugin = DigestAuthPlugin("test")
        environ = make_environ()
        # Identify with a bad nonce to mark it as stale.
        params = get_challenge(plugin, environ)
        params["nonce"] += "STALE"
        params = build_response(environ, params, "tester", "testing")
        self.assertEquals(plugin.identify(environ), None)
        # The challenge should then include stale=TRUE
        app = plugin.challenge(environ, "200 OK", [], [])
        self.assertNotEqual(app, None)
        response = get_response(app, environ)
        self.failUnless(response.startswith("401 Unauthorized"))
        self.failUnless('stale="TRUE"' in response)

    def test_challenge_with_extra_domains(self):
        plugin = DigestAuthPlugin("test", domain="http://example.com")
        environ = make_environ()
        app = plugin.challenge(environ, "200 OK", [], [])
        self.assertNotEqual(app, None)
        response = get_response(app, environ)
        self.failUnless(response.startswith("401 Unauthorized"))
        self.failUnless("http://example.com" in response)


class TestSignedNonceManager(unittest.TestCase):
    """Testcases for the SignedNonceManager class."""

    def test_nonce_validation(self):
        nm = SignedNonceManager(timeout=0.1)
        environ = make_environ(HTTP_USER_AGENT="good-user")
        # malformed nonces should be invalid
        self.failIf(nm.is_valid_nonce("", environ))
        self.failIf(nm.is_valid_nonce("IHACKYOU", environ))
        # immediately-generated nonces should be valid.
        nonce = nm.generate_nonce(environ)
        self.failUnless(nm.is_valid_nonce(nonce, environ))
        # tampered-with nonces should be invalid
        self.failIf(nm.is_valid_nonce(nonce + "IHACKYOU", environ))
        # nonces are only valid for specific user-agent
        environ2 = make_environ(HTTP_USER_AGENT="nasty-hacker")
        self.failIf(nm.is_valid_nonce(nonce, environ2))
        # expired nonces should be invalid
        self.failUnless(nm.is_valid_nonce(nonce, environ))
        time.sleep(0.1)
        self.failIf(nm.is_valid_nonce(nonce, environ))

    def test_next_nonce_generation(self):
        nm = SignedNonceManager(soft_timeout=0.1)
        environ = make_environ()
        nonce1 = nm.generate_nonce(environ)
        self.failUnless(nm.is_valid_nonce(nonce1, environ))

        # next-nonce is not generated until the soft timeout expires.
        self.assertEquals(nm.get_next_nonce(nonce1, environ), None)
        time.sleep(0.1)
        nonce2 = nm.get_next_nonce(nonce1, environ)
        self.assertNotEquals(nonce2, None)
        self.assertNotEquals(nonce2, nonce1)
        self.failUnless(nm.is_valid_nonce(nonce1, environ))
        self.failUnless(nm.is_valid_nonce(nonce2, environ))

    def test_nonce_count_management(self):
        nm = SignedNonceManager(timeout=0.1)
        environ = make_environ()
        nonce1 = nm.generate_nonce(environ)
        self.assertEquals(nm.get_nonce_count(nonce1), None)
        nm.set_nonce_count(nonce1, 1)
        self.assertEquals(nm.get_nonce_count(nonce1), 1)
        # purging won't remove it until it has expired.
        nm._purge_expired_nonces()
        self.assertEquals(nm.get_nonce_count(nonce1), 1)
        time.sleep(0.1)
        nm._purge_expired_nonces()
        self.assertEquals(nm.get_nonce_count(nonce1), None)

    def test_auto_purging_of_expired_nonces(self):
        nm = SignedNonceManager(timeout=0.2)
        environ = make_environ()
        nonce1 = nm.generate_nonce(environ)
        nm.set_nonce_count(nonce1, 1)
        time.sleep(0.1)
        # nonce1 hasn't expired, so adding a new one won't purge it
        nonce2 = nm.generate_nonce(environ)
        nm.set_nonce_count(nonce2, 1)
        self.assertEquals(nm.get_nonce_count(nonce1), 1)
        time.sleep(0.1)
        # nonce1 has expired, it should be purged when adding another.
        # nonce2 hasn't expired so it should remain in memory.
        nonce3 = nm.generate_nonce(environ)
        nm.set_nonce_count(nonce3, 1)
        self.assertEquals(nm.get_nonce_count(nonce1), None)
        self.assertEquals(nm.get_nonce_count(nonce2), 1)


class TestDigestAuthHelpers(unittest.TestCase):
    """Testcases for the various digest-auth helper functions."""

    def test_parse_auth_header(self):
        # Test parsing of a single unquoted parameter.
        params = parse_auth_header('Digest realm=hello')
        self.assertEquals(params['scheme'], 'Digest')
        self.assertEquals(params['realm'], 'hello')

        # Test parsing of multiple parameters with mixed quotes.
        params = parse_auth_header('Digest test=one, again="two"')
        self.assertEquals(params['scheme'], 'Digest')
        self.assertEquals(params['test'], 'one')
        self.assertEquals(params['again'], 'two')

        # Test parsing of an escaped quote and empty string.
        params = parse_auth_header('Digest test="\\"",again=""')
        self.assertEquals(params['scheme'], 'Digest')
        self.assertEquals(params['test'], '"')
        self.assertEquals(params['again'], '')

        # Test parsing of embedded commas, escaped and non-escaped.
        params = parse_auth_header('Digest one="1\\,2", two="3,4"')
        self.assertEquals(params['scheme'], 'Digest')
        self.assertEquals(params['one'], '1,2')
        self.assertEquals(params['two'], '3,4')

        # Test parsing on various malformed inputs
        self.assertRaises(ValueError, parse_auth_header, "")
        self.assertRaises(ValueError, parse_auth_header, " ")
        self.assertRaises(ValueError, parse_auth_header,
                          'Broken raw-token')
        self.assertRaises(ValueError, parse_auth_header,
                          'Broken realm="unclosed-quote')
        self.assertRaises(ValueError, parse_auth_header,
                          'Broken realm=unopened-quote"')
        self.assertRaises(ValueError, parse_auth_header,
                          'Broken realm="unescaped"quote"')
        self.assertRaises(ValueError, parse_auth_header,
                          'Broken realm="escaped-end-quote\\"')
        self.assertRaises(ValueError, parse_auth_header,
                          'Broken realm="duplicated",,what=comma')

    def test_validate_digest_parameters_qop(self):
        params = dict(scheme="Digest", realm="testrealm", username="tester",
                      nonce="abcdef", response="123456", qop="auth",
                      uri="/my/page", cnonce="98765")
        # Missing "nc"
        self.failIf(validate_digest_parameters(params))
        params["nc"] = "0001"
        self.failUnless(validate_digest_parameters(params))
        # Wrong realm
        self.failIf(validate_digest_parameters(params, realm="otherrealm"))
        self.failUnless(validate_digest_parameters(params, realm="testrealm"))
        # Unknown qop
        params["qop"] = "super-duper"
        self.failIf(validate_digest_parameters(params))
        params["qop"] = "auth-int"
        self.failUnless(validate_digest_parameters(params))
        params["qop"] = "auth"
        # Unknown algorithm
        params["algorithm"] = "sha1"
        self.failIf(validate_digest_parameters(params))
        params["algorithm"] = "md5"
        self.failUnless(validate_digest_parameters(params))

    def test_validate_digest_parameters_legacy(self):
        params = dict(scheme="Digest", realm="testrealm", username="tester",
                      nonce="abcdef", response="123456")
        # Missing "uri"
        self.failIf(validate_digest_parameters(params))
        params["uri"] = "/my/page"
        self.failUnless(validate_digest_parameters(params))
        # Wrong realm
        self.failIf(validate_digest_parameters(params, realm="otherrealm"))
        self.failUnless(validate_digest_parameters(params, realm="testrealm"))

    def test_validate_digest_uri(self):
        environ = make_environ(SCRIPT_NAME="/my", PATH_INFO="/page")
        params = dict(scheme="Digest", realm="testrealm", username="tester",
                      nonce="abcdef", response="123456", qop="auth",
                      uri="/my/page", cnonce="98765", nc="0001")
        self.failUnless(validate_digest_uri(environ, params))
        # Using full URI still works
        params["uri"] = "http://localhost/my/page"
        self.failUnless(validate_digest_uri(environ, params))
        # Check that query-string is taken into account.
        params["uri"] = "http://localhost/my/page?test=one"
        self.failIf(validate_digest_uri(environ, params))
        environ["QUERY_STRING"] = "test=one"
        self.failUnless(validate_digest_uri(environ, params))
        params["uri"] = "/my/page?test=one"
        self.failUnless(validate_digest_uri(environ, params))
        # Check that only MSIE is allow to fudge on the query-string.
        params["uri"] = "/my/page"
        environ["HTTP_USER_AGENT"] = "I AM FIREFOX I HAVE TO DO IT PROPERLY"
        self.failIf(validate_digest_uri(environ, params))
        environ["HTTP_USER_AGENT"] = "I AM ANCIENT MSIE PLZ HELP KTHXBYE"
        self.failUnless(validate_digest_uri(environ, params))
        self.failIf(validate_digest_uri(environ, params, msie_hack=False))
        params["uri"] = "/wrong/page"
        self.failIf(validate_digest_uri(environ, params))
