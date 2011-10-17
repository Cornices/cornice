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

repoze.who IIdentifier/IAuthenticator plugin based on hmac-signed cookies.

The SignedCookieAuthPlugin is broadly similar to the builtin repoze.who
AuthTktCookiePlugin.  It's designed to be simpler (because it records only
the username and doesn't try to do any datatype conversion) and more secure
(because it signs with a SHA1-HMAC rather than double-MD5).

"""

import os
import time
import hmac
import hashlib
import base64

from zope.interface import implements

from repoze.who.interfaces import IIdentifier, IAuthenticator

from paste.request import get_cookies


class SignedCookieAuthPlugin(object):
    """IIdentifier/IAuthenticatior plugin based on hmac-signed cookies.

    This is a repoze.who IIdentifier plugin that remembers user logins with
    a signed cookie.  Use it to reduce load on your authentication database
    by remembering good logins for a short period.

    The plugin should be given a secret key that is used to sign cookies.
    Servers sharing the same secret key will be able to validate each other's
    cookies.  If not specified, a new random secret will be generated at
    startup time.
    """

    implements(IIdentifier, IAuthenticator)

    def __init__(self, secret=None, cookie_name=None, timeout=None,
                 https_only=None, extra_headers=None):
        if secret is None:
            self.secret = os.urandom(16)
        else:
            self.secret = secret
        if cookie_name is None:
            self.cookie_name = "auth_token"
        else:
            self.cookie_name = cookie_name
        if timeout is None:
            self.timeout = 5 * 60
        else:
            self.timeout = timeout
        if https_only is None:
            self.https_only = True
        else:
            self.https_only = https_only
        if extra_headers is None:
            self.extra_headers = ()
        else:
            self.extra_headers = extra_headers

    def identify(self, environ):
        token = get_cookies(environ).get(self.cookie_name)
        # Don't identify if the cookie is missing.
        if token is None:
            return None
        # Don't identity if the token is invalid
        userid = self._verify_auth_token(token.value, environ)
        if userid is None:
            return None
        # Store the verified identity for retrieval during auth.
        identity = {}
        identity["services.whoauth.signedcookieauth.userid"] = userid
        return identity

    def remember(self, environ, identity):
        userid = identity.get("repoze.who.userid")
        # Don't set a cookie if there's nothing to remember.
        if userid is None:
            return None
        # Don't set a secure cookie if the connection is not encrypted.
        if self.https_only and environ["wsgi.url_scheme"] != "https":
            return None
        # Sign and set an auth token cookie.
        token = self._get_auth_token(userid, time.time(), environ)
        if self.https_only:
            cookie = "%s=%s; Path=/; Secure; HttpOnly"
        else:
            cookie = "%s=%s; Path=/; HttpOnly"
        return [("Set-Cookie", cookie % (self.cookie_name, token))]

    def forget(self, environ, identity):
        # Send an invalid, already-expired cookie.
        cookie = "%s=INVALID; Path=/; Expires=Sat, 01 Jan 2010 01:00:00 GMT"
        return [("Set-Cookie", cookie % (self.cookie_name,))]

    def authenticate(self, environ, identity):
        #  Identity extraction will already have verified the signature.
        #  Simply return the loaded userid.
        return identity.get("services.whoauth.signedcookieauth.userid")

    def _get_auth_token(self, userid, timestamp, environ):
        """Generate a signed auth token, embedding userid and timestamp."""
        # Don't leak subsecond timing info from the server.
        timestamp = int(timestamp)
        # Encode any special characters in the userid
        content = "%s:%s" % (userid, timestamp)
        # Sign it with a hmac, including any extra headers.
        sig = self._get_signature(content, environ)
        return "%s:%s" % (content, sig)

    def _verify_auth_token(self, token, environ):
        """Verify a signed auth token, returning extracted userid.

        This method verifies a signed auth token.  If the token is valid then
        the embedded userid string is returned; if not then None is returned.
        """
        # Extract the userid, timestamp and signature.
        try:
            (content, sig) = token.rsplit(":", 1)
            (userid, timestamp) = content.rsplit(":", 1)
            timestamp = int(timestamp)
        except ValueError:
            return None
        # Check whether the token has expired.
        if timestamp + self.timeout < time.time():
            return None
        # Check the signature while avoiding timing attacks.
        correct_sig = self._get_signature(content, environ)
        if len(sig) != len(correct_sig):
            return None
        differs = 0
        for i in xrange(len(sig)):
            differs |= ord(sig[i]) ^ ord(correct_sig[i])
        if differs:
            return None
        # The token is valid, return the userid.
        return userid

    def _get_signature(self, content, environ):
        """Generate signature for the given content."""
        sig = hmac.new(self.secret, content, hashlib.sha1)
        for header in self.extra_headers:
            sig.update(":")
            sig.update(environ.get(header, ""))
        return base64.b64encode(sig.digest())


def make_plugin(secret=None, cookie_name=None, timeout=None,
                https_only=None, extra_headers=None):
    """SignedCookieAuthPlugin helper for loading from ini files."""
    if timeout is not None:
        timeout = int(timeout)
    if https_only is not None:
        if isinstance(https_only, basestring):
            if https_only.lower() in ("yes", "on", "true", "1", ""):
                https_only = True
            elif https_only.lower() in ("no", "off", "false", "0"):
                https_only = False
            else:
                raise ValueError("invalid boolean value: %r" % (https_only,))
    if extra_headers is not None:
        extra_headers = [header.strip() for header in extra_headers.split()]
    plugin = SignedCookieAuthPlugin(secret, cookie_name, timeout, https_only,
                                    extra_headers)
    return plugin
