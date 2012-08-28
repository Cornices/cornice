# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging

from cornice import util
from cornice.errors import Errors  # NOQA
from cornice.service import Service   # NOQA
from cornice.pyramidhook import (
    wrap_request,
    register_service_views
)

logger = logging.getLogger('cornice')


def add_renderer_globals(event):
    event['util'] = util


def add_apidoc(config, pattern, func, service, **kwargs):
    apidocs = config.registry.settings.setdefault('apidocs', {})
    info = apidocs.setdefault(pattern, kwargs)
    info['service'] = service
    info['func'] = func


def includeme(config):
    """Include the Cornice definitions
    """
    from pyramid.events import BeforeRender, NewRequest

    #config.add_directive('add_apidoc', add_apidoc)
    config.add_directive('add_cornice_service', register_service_views)
    config.add_subscriber(add_renderer_globals, BeforeRender)
    config.add_subscriber(wrap_request, NewRequest)
    config.add_tween('cornice.pyramidhook.tween_factory')
    config.add_renderer('simplejson', util.json_renderer)
