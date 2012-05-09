# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import re


def filter_json_xsrf(response):
    """drops a warning if a service is returning a json array.

    See http://wiki.pylonshq.com/display/pylonsfaq/Warnings for more info
    on this
    """
    if response.content_type in ('application/json', 'text/json'):
        if re.match(r'\s?[\(\[).*[\)\]]\s?', response.body):
            from cornice import logger
            logger.warn("returning a json array is a potential security "
                     "hole, please ensure you really want to do this. See "
                     "http://wiki.pylonshq.com/display/pylonsfaq/Warnings "
                     "for more info")
    return response


DEFAULT_VALIDATORS = []
DEFAULT_FILTERS = [filter_json_xsrf, ]
