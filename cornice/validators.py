# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import re

from cornice.util import extract_request_data


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


def validate_colander_schema(schema):
    """Returns a validator for colander schemas"""
    def validator(request):
        from colander import Invalid

        def _validate_fields(location, data):
            for attr in schema.get_attributes(location=location):
                if attr.required and not attr.name in data:
                    # missing
                    request.errors.add(location, attr.name,
                                       "%s is missing" % attr.name)
                else:
                    try:
                        if not attr.name in data:
                            deserialized = attr.deserialize(None)
                        else:
                            deserialized = attr.deserialize(data[attr.name])
                    except Invalid, e:
                        # the struct is invalid
                        request.errors.add(location, attr.name, e.asdict()[attr.name])
                    else:
                        request.validated[attr.name] = deserialized

        qs, headers, body, path = extract_request_data(request)

        _validate_fields('path', path)
        _validate_fields('header', headers)
        _validate_fields('body', body)
        _validate_fields('querystring', qs)

    return validator


DEFAULT_VALIDATORS = []
DEFAULT_FILTERS = [filter_json_xsrf, ]
