# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Sync Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Ryan Kelly (ryan@rfk.id.au)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
"""

A repoze.who plugin for authentication via HTTP-Digest-Auth:

    http://tools.ietf.org/html/rfc2617

"""

from __future__ import with_statement

import os
import re
import time
import hmac
import base64
import heapq
import threading
import wsgiref.util
from urlparse import urlparse
from hashlib import md5

from zope.interface import implements

from repoze.who.interfaces import IIdentifier, IChallenger, IAuthenticator
from repoze.who.utils import resolveDotted


# WSGI environ key used to indicate a stale nonce.
_ENVKEY_STALE_NONCE = "cornice.auth.whoauth.digestauth.stale_nonce"

# Regular expression matching a single param in the HTTP_AUTHORIZATION header.
# This is basically <name>=<value> where <value> can be an unquoted token,
# an empty quoted string, or a quoted string where the ending quote is *not*
# preceded by a backslash.
_AUTH_PARAM_RE = r'([a-zA-Z0-9_\-]+)=(([a-zA-Z0-9_\-]+)|("")|(".*[^\\]"))'
_AUTH_PARAM_RE = re.compile(r"^\s*" + _AUTH_PARAM_RE + r"\s*$")

# Regular expression matching an unescaped quote character.
_UNESC_QUOTE_RE = r'(^")|([^\\]")'
_UNESC_QUOTE_RE = re.compile(_UNESC_QUOTE_RE)

# Regular expression matching a backslash-escaped characer.
_ESCAPED_CHAR = re.compile(r"\\.")


class DigestAuthPlugin(object):
    """A repoze.who plugin for authentication via HTTP-Digest-Auth.

    This plugin provides a repoze.who IIdentifier/IAuthenticator/IChallenger
    implementing the HTTP-Digest-Auth protocol:

        http://tools.ietf.org/html/rfc2617

    When used as an IIdentifier, it will extract digest-auth credentials
    from the HTTP Authorization header, check that they are well-formed
    and fresh, and return them for checking by an IAuthenticator.

    When used as an IAuthenticator, it will validate digest-auth credentials
    using a callback function to obtain the user's password or password hash.

    When used as an IChallenger, it will issue a HTTP WWW-Authenticate
    header with a fresh digest-auth challenge for each challenge issued.

    This plugin implements fairly complete support for the protocol as defined
    in RFC-2167.  Specifically:

        * both qop="auth" and qop="auth-int" modes
        * compatability mode for legacy clients
        * client nonce-count checking
        * next-nonce generation via the Authentication-Info header

    The following optional parts of the specification are not supported:

        * MD5-sess, or any hash algorithm other than MD5
        * mutual authentication via the Authentication-Info header

    Also, for qop="auth-int" mode, this plugin assumes that the request
    contains a Content-MD5 header and that this header is validated by some
    other component of the system (as it would be very rude for an auth
    plugin to consume the request body to calculate this header itself).

    To implement nonce generation, storage and expiration, this plugin
    uses a helper object called a "nonce manager".  This allows the details
    of nonce management to be modified to meet the security needs of your
    deployment.  The default implementation (SignedNonceManager) should be
    suitable for most purposes.
    """

    implements(IIdentifier, IChallenger, IAuthenticator)

    def __init__(self, realm, nonce_manager=None, domain=None, qop=None,
                 get_password=None, get_pwdhash=None):
        if nonce_manager is None:
            nonce_manager = SignedNonceManager()
        if qop is None:
            qop = "auth"
        self.realm = realm
        self.nonce_manager = nonce_manager
        self.domain = domain
        self.qop = qop
        self.get_password = get_password
        self.get_pwdhash = get_pwdhash

    def identify(self, environ):
        """Extract HTTP-Digest-Auth credentials from the request.

        This method extracts the digest-auth credentials from the request
        and checks that the provided nonce and other metadata is valid.
        If the nonce is found to be invalid (e.g. it is being re-used)
        then None is returned.

        If the credentials are fresh then the returned identity is a
        dictionary containing all the digest-auth parameters, e.g.:

            {'username': 'user', 'nonce': 'fc19cc22d1b5f84d', 'realm': 'Sync',
             'algorithm': 'MD5', 'qop': 'auth', 'cnonce': 'd61391b0baeb5131',
             'nc': '00000001', 'uri': '/some-protected-uri',
             'response': '75a8f0d4627eef8c73c3ac64a4b2acca'}

        It is the responsibility of an IAuthenticator plugin to check that
        the "response" value is a correct digest calculated according to the
        provided parameters.
        """
        # Grab the auth credentials, if any.
        authz = environ.get("HTTP_AUTHORIZATION")
        if authz is None:
            return None
        # Parse and sanity-check the auth credentials.
        try:
            params = parse_auth_header(authz)
        except ValueError:
            return None
        if params["scheme"].lower() != "digest":
            return None
        if not validate_digest_parameters(params):
            return None
        # Check that the digest is applied to the correct request URI.
        if not validate_digest_uri(environ, params):
            return None
        # Check that the provided nonce is valid.
        # If this looks like a stale request, mark it in the environment
        # so we can include that information in the challenge.
        if not validate_digest_nonce(environ, params, self.nonce_manager):
            environ[_ENVKEY_STALE_NONCE] = True
            return None
        # Looks good!
        return params

    def remember(self, environ, identity):
        """Remember the authenticated identity.

        This method can be used to pre-emptively send an updated nonce to
        the client as part of a successful response.  It is otherwise a
        no-op; the user-agent is supposed to remember the provided credentials
        and automatically send an authorization header with future requests.
        """
        nonce = identity.get("nonce", None)
        if nonce is None:
            return None
        next_nonce = self.nonce_manager.get_next_nonce(nonce, environ)
        if next_nonce is None:
            return None
        next_nonce = next_nonce.replace('"', '\\"')
        value = 'nextnonce="%s"' % (next_nonce,)
        return [("Authentication-Info", value)]

    def forget(self, environ, identity):
        """Forget the authenticated identity.

        For digest auth this is equivalent to sending a new challenge header,
        which should cause the user-agent to re-prompt for credentials.
        """
        return self._get_challenge_headers(environ, check_stale=False)

    def authenticate(self, environ, identity):
        """Authenticated the provided identity.

        If one of the "get_password" or "get_pwdhash" callbacks were provided
        then this class is capable of authenticating the identity for itself.
        """
        # Grab the username.
        # If there isn't one, we can't use this identity.
        username = identity.get("username")
        if username is None:
            return None
        # Grab the realm.
        # If there isn't one or it doesn't match, we can't use this identity.
        realm = identity.get("realm")
        if realm is None or realm != self.realm:
            return None
        # Obtain the pwdhash via one of the callbacks.
        if self.get_pwdhash is not None:
            pwdhash = self.get_pwdhash(username, realm)
        elif self.get_password is not None:
            password = self.get_password(username)
            pwdhash = calculate_pwdhash(username, password, realm)
        else:
            return None
        # Validate the digest response.
        if not check_digest_response(environ, identity, pwdhash=pwdhash):
            return None
        # Looks good!
        return username

    def challenge(self, environ, status, app_headers, forget_headers):
        """Challenge for digest-auth credentials.

        For digest-auth the challenge is a "401 Unauthorized" response with
        a fresh nonce in the WWW-Authenticate header.
        """
        headers = self._get_challenge_headers(environ)
        headers.extend(app_headers)
        headers.extend(forget_headers)
        if not status.startswith("401 "):
            status = "401 Unauthorized"

        def challenge_app(environ, start_response):
            start_response(status, headers)
            return ["Unauthorized"]

        return challenge_app

    def _get_challenge_headers(self, environ, check_stale=True):
        """Get headers necessary for a fresh digest-auth challenge.

        This method generates a new digest-auth challenge for the given
        request environ, including a fresh nonce.  If the environment
        is marked as having a stale nonce then this is indicated in the
        challenge.
        """
        params = {}
        params["realm"] = self.realm
        params["qop"] = self.qop
        params["nonce"] = self.nonce_manager.generate_nonce(environ)
        if self.domain is not None:
            params["domain"] = self.domain
        # Escape any special characters in those values, so we can send
        # them as quoted-strings.  The extra values added below are under
        # our control so we know they don't contain quotes.
        for key, value in params.iteritems():
            params[key] = value.replace('"', '\\"')
        # Mark the nonce as stale if told so by the environment.
        # NOTE:  The RFC says the server "should only set stale to TRUE if
        # it receives a request for which the nonce is invalid but with a
        # valid digest for that nonce".  But we can't necessarily check the
        # password at this stage, and it's only a "should", so don't bother.
        if check_stale and environ.get(_ENVKEY_STALE_NONCE):
            params["stale"] = "TRUE"
        params["algorithm"] = "MD5"
        # Construct the final header as quoted-string k/v pairs.
        value = ", ".join('%s="%s"' % itm for itm in params.iteritems())
        value = "Digest " + value
        return [("WWW-Authenticate", value)]


class NonceManager(object):
    """Interface definition for management of digest-auth nonces.

    This class defines the necessary methods for managing nonces as
    part of the digest-auth protocol:

        * generate_nonce:    create a new unique nonce
        * is_valid_nonce:    check for validity of a nonce
        * get_next_nonce:    get next nonce to be used by client
        * set_nonce_count:   record nonce counter sent by client
        * get_nonce_count:   retrieve nonce counter sent by client

    Nonce management is split out into a separate class to make it easy
    to adjust the various time-vs-memory-security tradeoffs involved -
    for example, you might provide a custom NonceManager that stores its
    state in memcache so it can be shared by several servers.
    """

    def generate_nonce(self, environ):
        """Generate a new nonce value.

        This method generates a new nonce value for the given request
        environment.  It will be a unique and non-forgable token containing
        only characters from the base64 alphabet.
        """
        raise NotImplementedError  # pragma: no cover

    def is_valid_nonce(self, nonce, environ):
        """Check whether the given nonce is valid.

        This method returns True only if the given nonce was previously
        issued to the client sending the given request, and it if it has
        not become stale.
        """
        raise NotImplementedError  # pragma: no cover

    def get_next_nonce(self, nonce, environ):
        """Get a new nonce to be used by the client for future requests.

        This method returns a new nonce that should be used by the client for
        future requests.  It may also return None if the given nonce is still
        valid and should be re-used.
        """
        raise NotImplementedError  # pragma: no cover

    def get_nonce_count(self, nonce):
        """Get the current client nonce-count.

        This method returns the most-recently-set client nonce-count, or
        None if not nonce-count has been set.
        """
        raise NotImplementedError  # pragma: no cover

    def set_nonce_count(self, nonce, nc):
        """Set the current client nonce-count.

        This method records the given value as the current nonce-count for
        that nonce.  Subsequent calls to get_nonce_count() will return it.
        The given nonce-count value should be an integer.
        """
        raise NotImplementedError  # pragma: no cover


class SignedNonceManager(object):
    """Class managing signed digest-auth nonces.

    This class provides a NonceManager implementation based on signed
    timestamped nonces.  It should provide a good balance between speed,
    memory-usage and security for most applications.

    The following options customize the use of this class:

       * secret:  string key used for signing the nonces;
                  if not specified then a random bytestring is used.

       * timeout: the time after which a nonce will expire.

       * soft_timeout:  the time after which an updated nonce will
                        be sent to the client.

       * sign_headers:  a list of environment keys to include in the
                        nonce signature; if not specified then it
                        defaults to just the user-agent string.
    """

    def __init__(self, secret=None, timeout=None, soft_timeout=None,
                 sign_headers=None):
        # Default secret is a random bytestring.
        if secret is None:
            secret = os.urandom(16)
        # Default timeout is five minutes.
        if timeout is None:
            timeout = 5 * 60
        # Default soft_timeout is 80% of the hard timeout.
        if soft_timeout is None:
            soft_timeout = int(timeout * 0.8) or None
        # Default signing headers are just the user-agent string.
        if sign_headers is None:
            sign_headers = ("HTTP_USER_AGENT",)
        self.secret = secret
        self.timeout = timeout
        self.soft_timeout = soft_timeout
        self.sign_headers = sign_headers
        # We need to keep a mapping from nonces to their most recent count.
        self._nonce_counts = {}
        # But we don't want to store nonces in memory forever!
        # We keep a queue of nonces and aggresively purge them when expired.
        # Unfortunately this requires a lock, but we go to some lengths
        # to avoid having to acquire it in the default case.  See the
        # set_nonce_count() method for the details.
        self._nonce_purge_lock = threading.Lock()
        self._nonce_purge_queue = []

    def generate_nonce(self, environ):
        """Generate a new nonce value.

        In this implementation the nonce consists of an encoded timestamp
        and a HMAC signature to prevent forgery.  The signature can embed
        additional headers from the client request, to tie it to a particular
        user-agent.
        """
        # The nonce is the current time, hmac-signed along with the
        # request headers to tie it to a particular client or user-agent.
        timestamp = hex(int(time.time() * 10))
        # Remove hex-formatting guff e.g. "0x31220ead8L" => "31220ead8"
        timestamp = timestamp[2:]
        if timestamp.endswith("L"):
            timestamp = timestamp[:-1]
        sig = self._get_signature(timestamp, environ)
        return "%s:%s" % (timestamp, sig)

    def is_valid_nonce(self, nonce, environ):
        """Check whether the given nonce is valid.

        In this implementation the nonce is valid is if has a valid
        signature, and if the embedded timestamp is not too far in
        the past.
        """
        if self._nonce_has_expired(nonce):
            return False
        timestamp, sig = nonce.split(":", 1)
        expected_sig = self._get_signature(timestamp, environ)
        # This is a deliberately slow string-compare to avoid timing attacks.
        # Read the docstring of strings_differ for more details.
        return not strings_differ(sig, expected_sig)

    def get_next_nonce(self, nonce, environ):
        """Get a new nonce to be used by the client for future requests.

        In this implementation a new nonce is issued whenever the current
        nonce is older than the soft timeout.
        """
        if not self._nonce_has_expired(nonce, self.soft_timeout):
            return None
        return self.generate_nonce(environ)

    def get_nonce_count(self, nonce):
        """Get the current client nonce-count."""
        # No need to lock here.  If the client is generating lots of
        # parallel requests with the same nonce then we *might* read
        # a stale nonce count, but this will just trigger a re-submit
        # from the client and not produce any errors.
        return self._nonce_counts.get(nonce, None)

    def set_nonce_count(self, nonce, nc):
        """Set the current client nonce-count."""
        # If this is the first count registered for that nonce,
        # add it into the heap for expiry tracking.  Also take the
        # opportunity to remove a few expired nonces from memory.
        # In this way, we only spend time purging if we're about to
        # increase memory usage by registering a new nonce.
        if nonce not in self._nonce_counts:
            with self._nonce_purge_lock:
                self._purge_expired_nonces(limit=10)
                heapq.heappush(self._nonce_purge_queue, nonce)
        # Update the dict outside of the lock.  This is intentionally
        # a little sloppy, and may produce lost updates if the client
        # is sending parallel requests with the same nonce.  That's
        # not very likely and not very serious, and it's outweighed
        # by not having to take the lock in the common case.
        self._nonce_counts[nonce] = nc

    def _purge_expired_nonces(self, limit=None):
        """Purge any expired nonces from the in-memory store."""
        if limit is None:
            limit = len(self._nonce_purge_queue)
        # Pop nonces off the heap until we find one that's not expired.
        # Remove each expired nonce from the count map as we go.
        for i in xrange(min(limit, len(self._nonce_purge_queue))):
            nonce = self._nonce_purge_queue[0]
            if not self._nonce_has_expired(nonce):
                break
            self._nonce_counts.pop(nonce, None)
            heapq.heappop(self._nonce_purge_queue)

    def _nonce_has_expired(self, nonce, timeout=None):
        """Check whether the given nonce has expired."""
        if timeout is None:
            timeout = self.timeout
        try:
            timestamp, sig = nonce.split(":", 1)
            expiry_time = (int(timestamp, 16) * 0.1) + timeout
        except ValueError:
            # Eh? Malformed Nonce? Treat it as expired.
            return True
        else:
            return expiry_time <= time.time()

    def _get_signature(self, value, environ):
        """Calculate the HMAC signature for the given value.

        This method will calculate the HMAC signature for an arbitrary
        string value, mixing in some headers from the request environment
        so that the signature is tied to a particular user-agent.
        """
        # We're using md5 for the digest; using something stronger
        # for the HMAC probably won't win us much.
        sig = hmac.new(self.secret, value, md5)
        for header in self.sign_headers:
            sig.update("\x00")
            sig.update(environ.get(header, ""))
        return base64.b64encode(sig.digest())


def parse_auth_header(value):
    """Parse an authorization header string into an identity dict.

    This function can be used to parse the value from an Authorization
    header into a dict of its constituent parameters.  The auth scheme
    name will be included under the key "scheme", and any other auth
    params will appear as keys in the dictionary.

    For example, given the following auth header value:

        'Digest realm="Sync" userame=user1 response="123456"'

    This function will return the following dict:

        {"scheme": "Digest", realm: "Sync",
         "username": "user1", "response": "123456"}

    """
    scheme, kvpairs_str = value.split(None, 1)
    # Split the parameters string into individual key=value pairs.
    # In the simple case we can just split by commas to get each pair.
    # Unfortunately this will break if one of the values contains a comma.
    # So if we find a component that isn't a well-formed key=value pair,
    # then we stitch bits back onto the end of it until it is.
    kvpairs = []
    if kvpairs_str:
        for kvpair in kvpairs_str.split(","):
            if not kvpairs or _AUTH_PARAM_RE.match(kvpairs[-1]):
                kvpairs.append(kvpair)
            else:
                kvpairs[-1] = kvpairs[-1] + "," + kvpair
        if not _AUTH_PARAM_RE.match(kvpairs[-1]):
            raise ValueError('Malformed auth parameters')
    # Now we can just split by the equal-sign to get each key and value.
    params = {"scheme": scheme}
    for kvpair in kvpairs:
        (key, value) = kvpair.strip().split("=", 1)
        # For quoted strings, remove quotes and backslash-escapes.
        if value.startswith('"'):
            value = value[1:-1]
            if _UNESC_QUOTE_RE.search(value):
                raise ValueError("Unescaped quote in quoted-string")
            value = _ESCAPED_CHAR.sub(lambda m: m.group(0)[1], value)
        params[key] = value
    return params


def validate_digest_parameters(params, realm=None):
    """Validate the given dict of digest-auth parameters.

    This function allows you to sanity-check digest-auth parameters, to
    make sure that all required information has been provided.  It returns
    True if the parameters are a well-formed digest-auth response, False
    otherwise.
    """
    # Check for required information.
    for key in ("username", "realm", "nonce", "uri", "response"):
        if key not in params:
            return False
    if realm is not None and params["realm"] != realm:
        return False
    # Check for extra information required when "qop" is present.
    if "qop" in params:
        for key in ("cnonce", "nc"):
            if key not in params:
                return False
        if params["qop"] not in ("auth", "auth-int"):
            return False
    # Check that the algorithm, if present, is explcitly set to MD5.
    if "algorithm" in params and params["algorithm"].lower() != "md5":
        return False
    # Looks good!
    return True


def validate_digest_uri(environ, params, msie_hack=True):
    """Validate that the digest URI matches the request environment.

    This is a helper function to check that digest-auth is being applied
    to the correct URI.  It matches the given request environment against
    the URI specified in the digest auth parameters, returning True if
    they are equiavlent and False otherwise.

    Older versions of MSIE are known to handle certain URIs incorrectly,
    and this function includes a hack to work around this problem.  To
    disable it and sligtly increase security, pass msie_hack=False.
    """
    uri = params["uri"]
    req_uri = wsgiref.util.request_uri(environ)
    if uri != req_uri:
        p_req_uri = urlparse(req_uri)
        if not p_req_uri.query:
            if uri != p_req_uri.path:
                return False
        else:
            if uri != "%s?%s" % (p_req_uri.path, p_req_uri.query):
                # MSIE < 7 doesn't include the GET vars in the signed URI.
                # Let them in, but don't give other user-agents a free ride.
                if not msie_hack:
                    return False
                if "MSIE" not in environ.get("HTTP_USER_AGENT", ""):
                    return False
                if uri != p_req_uri.path:
                    return False
    return True


def validate_digest_nonce(environ, params, nonce_manager):
    """Validate that the digest parameters contain a fresh nonce.

    This is a helper function to check that the provided digest-auth
    credentials contain a valid, up-to-date nonce.  It calls various
    methods on the provided NonceManager object in order to query and
    update the state of the nonce database.

    Returns True if the nonce is valid, False otherwise.
    """
    # Check that the nonce itself is valid.
    nonce = params["nonce"]
    if not nonce_manager.is_valid_nonce(nonce, environ):
        return False
    # Check that the nonce-count is valid.
    # RFC-2617 says the nonce-count must be an 8-char-long hex number.
    # We convert to an integer since they take less memory than strings.
    # We enforce the length limit strictly since flooding the server with
    # many large nonce-counts could cause a DOS via memory exhaustion.
    nc_new = params.get("nc", None)
    if nc_new is not None:
        try:
            nc_new = int(nc_new[:8], 16)
        except ValueError:
            return False
    # Check that the the nonce-count is strictly increasing.
    nc_old = nonce_manager.get_nonce_count(nonce)
    if nc_old is not None:
        if nc_new is None or nc_new <= nc_old:
            return False
    if nc_new is not None:
        nonce_manager.set_nonce_count(nonce, nc_new)
    # Looks good!
    return True


def calculate_pwdhash(username, password, realm):
    """Calculate the password hash used for digest auth.

    This function takes the username, password and realm and calculates
    the password hash (aka "HA1") used in the digest-auth protocol.
    It assumes that the hash algorithm is MD5.
    """
    data = "%s:%s:%s" % (username, realm, password)
    return md5(data).hexdigest()


def calculate_reqhash(environ, params):
    """Calculate the request hash used for digest auth.

    This function takes the request environment and digest parameters,
    and calculates the request hash (aka "HA2") used in the digest-auth
    protocol.  It assumes that the hash algorithm is MD5.
    """
    method = environ["REQUEST_METHOD"]
    uri = params["uri"]
    qop = params.get("qop")
    # For qop="auth" or unspecified, we just has the method and uri.
    if qop in (None, "auth"):
        data = "%s:%s" % (method, uri)
    # For qop="auth-int" we also include the md5 of the entity body.
    # We assume that a Content-MD5 header has been sent and is being
    # checked by some other layer in the stack.
    elif qop == "auth-int":
        content_md5 = environ["HTTP_CONTENT_MD5"]
        content_md5 = base64.b64decode(content_md5)
        data = "%s:%s:%s" % (method, uri, content_md5)
    # No other qop values are recognised.
    else:
        raise ValueError("unrecognised qop value: %r" % (qop,))
    return md5(data).hexdigest()


def calculate_digest_response(environ, params, pwdhash=None, password=None):
    """Calculate the expected response to a digest challenge.

    Given the digest challenge parameters, request environ, and password or
    password hash, this function calculates the expected digest responds
    according to RFC-2617.  It assumes that the hash algorithm is MD5.
    """
    username = params["username"]
    realm = params["realm"]
    if pwdhash is None:
        if password is None:
            raise ValueError("must provide either 'pwdhash' or 'password'")
        pwdhash = calculate_pwdhash(username, password, realm)
    reqhash = calculate_reqhash(environ, params)
    qop = params.get("qop")
    if qop is None:
        data = "%s:%s:%s" % (pwdhash, params["nonce"], reqhash)
    else:
        data = ":".join([pwdhash, params["nonce"], params["nc"],
                         params["cnonce"], qop, reqhash])
    return md5(data).hexdigest()


def check_digest_response(environ, params, pwdhash=None, password=None):
    """Check if the given digest response is valid.

    This function checks whether a dict of digest response parameters
    has been correctly authenticated using the specified password or
    password hash.
    """
    expected = calculate_digest_response(environ, params, pwdhash)
    # Use a timing-invarient comparison to prevent guessing the correct
    # digest one character at a time.  Ideally we would reject repeated
    # attempts to use the same nonce, but that may not be possible using
    # e.g. time-based nonces.  This is a nice extra safeguard.
    return not strings_differ(expected, params["response"])


def strings_differ(string1, string2):
    """Check whether two strings differ while avoiding timing attacks.

    This function returns True if the given strings differ and False
    if they are equal.  It's careful not to leak information about *where*
    they differ as a result of its running time, which can be very important
    to avoid certain timing-related crypto attacks:

        http://seb.dbzteam.org/crypto/python-oauth-timing-hmac.pdf

    """
    if len(string1) != len(string2):
        return True
    invalid_bits = 0
    for a, b in zip(string1, string2):
        invalid_bits += a != b
    return invalid_bits != 0


def make_plugin(realm='', nonce_manager=None, domain=None, qop=None,
                get_password=None, get_pwdhash=None):
    """Make a DigestAuthPlugin using values from a .ini config file.

    This is a helper function for loading a DigestAuthPlugin via the
    repoze.who .ini config file system.  It converts its arguments from
    strings to the appropriate type then passes them on to the plugin.
    """
    if isinstance(nonce_manager, basestring):
        nonce_manager = resolveDotted(nonce_manager)
        if callable(nonce_manager):
            nonce_manager = nonce_manager()
    if isinstance(get_password, basestring):
        get_password = resolveDotted(get_password)
        if get_password is not None:
            assert callable(get_password)
    if isinstance(get_pwdhash, basestring):
        get_pwdhash = resolveDotted(get_pwdhash)
        if get_pwdhash is not None:
            assert callable(get_pwdhash)
    plugin = DigestAuthPlugin(realm, nonce_manager, domain, qop,
                              get_password, get_pwdhash)
    return plugin
