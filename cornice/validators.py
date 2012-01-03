import logging
import re

log = logging.getLogger('cornice')


def filter_json_xsrf(response):
    """drops a warning if a service is returning a json array.

    See http://wiki.pylonshq.com/display/pylonsfaq/Warnings for more info
    on this
    """
    if response.content_type in ('application/json', 'text/json'):
        if re.match(r'[\(\[).*[\)\]]', response.body):
            log.warn("returning a json array is a potential security whole, "
                     "please ensure you really want to do this. See "
                     "http://wiki.pylonshq.com/display/pylonsfaq/Warnings "
                     "for more info")
    return response


DEFAULT_VALIDATORS = []
DEFAULT_FILTERS = [filter_json_xsrf, ]
