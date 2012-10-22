# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import simplejson as json

from pyramid import httpexceptions as exc
from pyramid.response import Response


__all__ = ['json_renderer', 'to_list', 'json_error', 'match_accept_header',
           'extract_request_data']


def json_renderer(helper):
    return _JsonRenderer()


class _JsonRenderer(object):
    def __call__(self, data, context):
        response = context['request'].response
        response.content_type = 'application/json'
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
    acceptable = func(request)
    # attach the accepted content types to the request
    request.info['acceptable'] = acceptable
    return request.accept.best_match(acceptable) is not None


def extract_request_data(request):
    """extract the different parts of the data from the request, and return
    them as a list of (querystring, headers, body, path)
    """
    # XXX In the body, we're only handling JSON for now.
    if request.body:
        try:
            body = json.loads(request.body)
        except ValueError, e:
            request.errors.add('body', None, e.message)
            body = {}
    else:
        body = {}

    return request.GET, request.headers, body, request.matchdict
