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
#   Alexis Metaireau (alexis@mozilla.com)
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
import json
import logging

from pyramid.events import BeforeRender, NewRequest
from pyramid.httpexceptions import HTTPNotFound, HTTPMethodNotAllowed
from pyramid.exceptions import PredicateMismatch

from cornice import util
from cornice.schemas import Errors
from cornice.service import Service   # NOQA


logger = logging.getLogger('cornice')


def add_renderer_globals(event):
    event['util'] = util


def wrap_request(event):
    """Adds a "validated" dict, a custom "errors" object and an "info" dict to
    the request object if they don't already exists
    """
    request = event.request
    if not hasattr(request, 'validated'):
        setattr(request, 'validated', {})

    if not hasattr(request, 'errors'):
        setattr(request, 'errors', Errors(request))

    if not hasattr(request, 'info'):
        setattr(request, 'info', {})


def add_apidoc(config, pattern, func, service, **kwargs):
    apidocs = config.registry.settings.setdefault('apidocs', {})
    info = apidocs.setdefault(pattern, kwargs)
    info['service'] = service
    info['func'] = func


def tween_factory(handler, registry):
    """Wraps the default WSGI workflow to provide cornice utilities"""
    def cornice_tween(request):
        response = handler(request)
        if request.matched_route is not None:
            # do some sanity checking on the response using filters
            pattern = request.matched_route.pattern
            service = request.registry['cornice_services'].get(pattern)
            if service is not None:
                if request.method not in service.defined_methods:
                    response = HTTPMethodNotAllowed()
                    response.allow = service.defined_methods
                else:
                    # get the filters for this call
                    kwargs = service.definitions[request.method]
                    for _filter in kwargs.get('filters', []):
                        response = _filter(response)
        return response
    return cornice_tween


def _notfound(request):
    match = request.matchdict
    if match is not None:
        pattern = request.matched_route.pattern
        service = request.registry['cornice_services'].get(pattern)
        if (service is not None
                and isinstance(request.exception, PredicateMismatch)
                and request.method in service.defined_methods):
            # maybe was it the accept predicate that was not matched
            # in this case, returns a HTTP 406 NOT ACCEPTABLE with the
            # list of available choices
            api_kwargs = service.definitions[request.method]
            if 'accept' in api_kwargs:
                accept = api_kwargs.get('accept')
                acceptable = [a for a in util.to_list(accept) if
                              not callable(a)]

                if 'acceptable' in request.info:
                    for content_type in request.info['acceptable']:
                        if content_type not in acceptable:
                            acceptable.append(content_type)

                if not request.accept.best_match(acceptable):
                    # if not, return the list of accepted headers
                    resp = request.response
                    resp.status = 406
                    resp.content_type = "application/json"
                    resp.body = json.dumps(acceptable)
                    return resp
    # 404
    return request.exception


def includeme(config):
    """Include the Cornice definitions
    """
    config.add_directive('add_apidoc', add_apidoc)
    config.add_view(_notfound, context=HTTPNotFound)
    config.add_subscriber(add_renderer_globals, BeforeRender)
    config.add_subscriber(wrap_request, NewRequest)
    config.add_tween('cornice.tween_factory')
    config.add_renderer('simplejson', util.json_renderer)
