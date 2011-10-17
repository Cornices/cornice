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
"""
Various utilities
"""
from hashlib import md5
import traceback
import random
import string
import simplejson as json
import re
import os
import logging
from ConfigParser import NoOptionError


random.seed()
_RE_CODE = re.compile('[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}')


def randchar(chars=string.digits + string.letters):
    """Generates a random char using urandom.

    If the system does not support it, the function fallbacks on random.choice

    See Haypo's explanation on the used formula to pick a char:
    http://bitbucket.org/haypo/hasard/src/tip/doc/common_errors.rst
    """
    try:
        pos = int(float(ord(os.urandom(1))) * 256. / 255.)
        return chars[pos % len(chars)]
    except NotImplementedError:
        return random.choice(chars)


def _resolve_name(name):
    """Resolves the name and returns the corresponding object."""
    ret = None
    parts = name.split('.')
    cursor = len(parts)
    module_name = parts[:cursor]
    last_exc = None

    while cursor > 0:
        try:
            ret = __import__('.'.join(module_name))
            break
        except ImportError, exc:
            last_exc = exc
            if cursor == 0:
                raise
            cursor -= 1
            module_name = parts[:cursor]

    for part in parts[1:]:
        try:
            ret = getattr(ret, part)
        except AttributeError:
            if last_exc is not None:
                raise last_exc
            raise ImportError(name)

    if ret is None:
        if last_exc is not None:
            raise last_exc
        raise ImportError(name)

    return ret


class CatchErrorMiddleware(object):
    """Middleware that catches error, log them and return a 500"""
    def __init__(self, app, config):
        self.app = app
        try:
            logger_name = config.get('global', 'logger_name')
        except NoOptionError:
            logger_name = 'root'

        self.logger = logging.getLogger(logger_name)
        try:
            hook = config.get('global', 'logger_hook')
            self.hook = _resolve_name(hook)
        except NoOptionError:
            self.hook = None

        try:
            self.ctype = config.get('global', 'logger_type')
        except NoOptionError:
            self.ctype = 'application/json'

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        except:
            err = traceback.format_exc()
            hash = create_hash(err)
            self.logger.error(hash)
            self.logger.error(err)
            start_response('500 Internal Server Error',
                           [('content-type', self.ctype)])

            response = json.dumps("application error: crash id %s" % hash)
            if self.hook:
                try:
                    response = self.hook()
                except Exception:
                    pass

            return [response]


def make_err_mdw(app, global_conf, **conf):
    config = app.registry.settings['config']
    return CatchErrorMiddleware(app, config)


def create_hash(data):
    """Creates a unique hash using the data provided
    and a bit of randomness
    """
    rand = ''.join([randchar() for x in range(10)])
    data += rand
    return md5(data + rand).hexdigest()
