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
# The Original Code is Cornice (Sagrada)
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
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
""" Exceptions
"""
from ConfigParser import Error


class BackendError(Exception):
    """Raised when the backend is down or fails"""
    def __init__(self, msg='', server='', retry_after=None,
                 backend=None, request=None):
        """
        - msg, server will be dumped in str() if provided
        - retry_after, if set to a positive integer, will be used to send
          back a Retry-After header value. If not set, a default value is
          returned. If set to 0, the header is explicitely skipped.
        - backend: if provided, the backend from where originated the error.
          it will be used to render more details, It can be any kind of object
          as __str__() will be called on it.

        """
        self.msg = msg
        self.server = server
        self.retry_after = retry_after
        self.backend = backend
        self.request = request

    def __str__(self):
        res = self.__class__.__name__
        if self.server != '':
            res += ' on %s' % self.server
        if self.backend is not None:
            res += '\n%s' % str(self.backend)
        if self.msg != '':
            res += '\n\n%s' % self.msg
        if self.request:
            res = '%s %s\n%s' % (self.request.method,
                                 self.request.path_info,
                                 res)
        return res


class BackendTimeoutError(BackendError):
    """Raised when the backend times out."""
    pass


class MaxConnectionReachedError(Exception):
    """Raised by ldappool"""
    pass


class NoEmailError(Exception):
    """Raised when we need the user's email address and it doesn't exist."""
    pass


class NoUserIDError(Exception):
    """Raised when there's no userID fails."""
    pass


class NodeAttributionError(Exception):
    """Raised when the node attribution fails."""
    pass


class InvalidCodeError(Exception):
    """Raised when we need the user's reset code is incorrect."""
    pass


class EnvironmentNotFoundError(Error):
    """Raised when an environment variable is not found"""

    def __init__(self, varname):
        Error.__init__(self, 'Variable not found %r' % varname)
        self.varname = varname


""" 400 error codes

Warning

  If you add a constant here, please update
  https://hg.mozilla.org/services/docs/file/tip/source/respcodes.rst
  which is used to generate http://docs.services.mozilla.com/respcodes.html
"""

ERROR_ILLEGAL_METHOD = 1            # Illegal method/protocol
ERROR_INVALID_CAPTCHA = 2           # Incorrect/missing captcha
ERROR_INVALID_USER = 3              # Invalid/missing username
ERROR_INVALID_WRITE = 4             # Attempt to overwrite data that can't be
ERROR_WRONG_USERID = 5              # Userid does not match account in path
ERROR_MALFORMED_JSON = 6            # Json parse failure
ERROR_MISSING_PASSWORD = 7          # Missing password field
ERROR_INVALID_WBO = 8               # Invalid Basic Object
ERROR_WEAK_PASSWORD = 9             # Requested password not strong enough
ERROR_INVALID_RESET_CODE = 10       # Invalid/missing password reset code
ERROR_UNSUPPORTED_FUNCTION = 11     # Unsupported function
ERROR_NO_EMAIL_ADDRESS = 12         # No email address on file
ERROR_INVALID_COLLECTION = 13       # Invalid collection
ERROR_OVER_QUOTA = 14               # User over quota
ERROR_USERNAME_EMAIL_MISMATCH = 15  # The e-mail does not match the username
