import json
import logging

log = logging.getLogger(__name__)


def filter_json_xsrf(response):
    """drops a warning if a service is returning a json array.

    See http://wiki.pylonshq.com/display/pylonsfaq/Warnings for more info
    on this
    """
    if response.content_type in ('application/json', 'text/json'):
        try:
            content = json.loads(response.body)
            if isinstance(content, (list, tuple)):
                log.warn("returning a json array is a potential security "
                         "hole, please ensure you really want to do this. See "
                         "http://wiki.pylonshq.com/display/pylonsfaq/Warnings "
                         "for more info")
        except:
            pass
    return response


def extract_data(request):
    """extract the different parts of the data from the request, and return
    them as a list of (querystring, headers, body)
    """
    # XXX In the body, we're only handling JSON for now.
    try:
        body = json.loads(request.body)
    except ValueError, e:
        request.errors.add('body', None, e.message)
        body = {}

    return request.GET, request.headers, body, request.matchdict


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
                        deserialized = attr.deserialize(data[attr.name])
                    except Invalid, e:
                        # the struct is invalid
                        request.errors.append(location, attr.name, e.message)
                    else:
                        request.validated[attr.name] = deserialized

        qs, headers, body, path = extract_data(request)

        _validate_fields('path', path)
        _validate_fields('header', headers)
        _validate_fields('body', body)
        _validate_fields('querystring', qs)

    return validator


DEFAULT_VALIDATORS = []
DEFAULT_FILTERS = [filter_json_xsrf, ]
