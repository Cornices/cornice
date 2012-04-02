# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging

from pyramid.events import BeforeRender, NewRequest

from cornice import util
from cornice.errors import Errors
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
                kwargs = getattr(request, "cornice_api_kwargs", {})
                for _filter in kwargs.get('filters', []):
                    response = _filter(response)
        return response
    return cornice_tween


def includeme(config):
    """Include the Cornice definitions
    """
    config.add_directive('add_apidoc', add_apidoc)
    config.add_subscriber(add_renderer_globals, BeforeRender)
    config.add_subscriber(wrap_request, NewRequest)
    config.add_tween('cornice.tween_factory')
    config.add_renderer('simplejson', util.json_renderer)
