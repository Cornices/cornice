# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import sys

import simplejson as json

from pyramid import httpexceptions as exc
from pyramid.response import Response


__all__ = ['json_renderer', 'to_list', 'json_error', 'match_accept_header',
           'extract_request_data']


PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
else:
    string_types = basestring,


def is_string(s):
    return isinstance(s, string_types)


def json_renderer(helper):
    return _JsonRenderer()


class _JsonRenderer(object):
    def __call__(self, data, context):
        acceptable = ('application/json', 'text/json', 'text/plain')
        response = context['request'].response
        content_type = (context['request'].accept.best_match(acceptable)
                        or acceptable[0])
        response.content_type = content_type
        return json.dumps(data, use_decimal=True)


def to_list(obj):
    """Convert an object to a list if it is not already one"""
    if not isinstance(obj, (list, tuple)):
        obj = [obj, ]
    return obj


class _JSONError(exc.HTTPError):
    def __init__(self, errors, status=400):
        body = {'status': 'error', 'errors': errors}
        Response.__init__(self, json.dumps(body, use_decimal=True))
        self.status = status
        self.content_type = 'application/json'


def json_error(errors):
    """Returns an HTTPError with the given status and message.

    The HTTP error content type is "application/json"
    """
    return _JSONError(errors, errors.status)


def match_accept_header(func, context, request):
    """
    Return True if the request matches the values returned by the given :param:
    func callable.

    :param func:
        The callable returning the list of acceptable content-types,
        given a request. It should accept a "request" argument.
    """
    acceptable = func(request)
    # attach the accepted egress content types to the request
    request.info['acceptable'] = acceptable
    return request.accept.best_match(acceptable) is not None


def match_content_type_header(func, context, request):
    supported_contenttypes = func(request)
    # attach the accepted ingress content types to the request
    request.info['supported_contenttypes'] = supported_contenttypes
    return content_type_matches(request, supported_contenttypes)


def extract_json_data(request):
    if request.body:
        try:
            body = json.loads(request.body)
        except ValueError as e:
            request.errors.add(
                'body', None,
                "Invalid JSON request body: %s" % (e.message))
        return body
    else:
        return {}


def extract_form_urlencoded_data(request):
    return request.POST


def extract_request_data(request):
    """extract the different parts of the data from the request, and return
    them as a tuple of (querystring, headers, body, path)
    """
    body = {}
    content_type = getattr(request, 'content_type', None)
    registry = request.registry
    if hasattr(request, 'deserializer'):
        body = request.deserializer(request)
    elif (hasattr(registry, 'cornice_deserializers')
          and content_type in registry.cornice_deserializers):
        deserializer = registry.cornice_deserializers[content_type]
        body = deserializer(request)
    # otherwise, don't block but it will be an empty body, decode
    # on your own

    return request.GET, request.headers, body, request.matchdict


def content_type_matches(request, content_types):
    """
    Check whether ``request.content_type``
    matches given list of content types.
    """
    return request.content_type in content_types


class ContentTypePredicate(object):
    """
    Pyramid predicate for matching against ``Content-Type`` request header.
    Should live in ``pyramid.config.predicates``.

    .. seealso::

        http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/hooks.html#view-and-route-predicates
    """
    def __init__(self, val, config):
        self.val = val

    def text(self):
        return 'content_type = %s' % (self.val,)

    phash = text

    def __call__(self, context, request):
        return request.content_type == self.val
