# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import re

# Strings and arrays are potentially exploitable
safe_json_re = re.compile(r'\s*[\{tfn\-0-9]'.encode('ascii'), re.MULTILINE)


def filter_json_xsrf(response):
    """drops a warning if a service returns potentially exploitable json
    """
    if hasattr(response, 'content_type') and response.content_type in ('application/json', 'text/json'):
        if safe_json_re.match(response.body) is None:
            from cornice import logger
            logger.warn("returning a json string or array is a potential "
                "security hole, please ensure you really want to do this.")
    return response


DEFAULT_VALIDATORS = []
DEFAULT_FILTERS = [filter_json_xsrf, ]
