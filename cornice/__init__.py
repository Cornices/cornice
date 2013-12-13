# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
from functools import partial

from cornice import util
from cornice.errors import Errors  # NOQA
from cornice.service import Service   # NOQA
from cornice.pyramidhook import (
    wrap_request,
    register_service_views,
    handle_exceptions,
    add_deserializer,
    register_resource_views,
)
from cornice.util import ContentTypePredicate
from pyramid.i18n import get_localizer
from pyramid.httpexceptions import HTTPNotFound, HTTPForbidden
from pyramid.security import NO_PERMISSION_REQUIRED

logger = logging.getLogger('cornice')
__version__ = "0.18"


def add_renderer_globals(event):
    event['util'] = util


def add_apidoc(config, pattern, func, service, **kwargs):
    apidocs = config.registry.settings.setdefault('apidocs', {})
    info = apidocs.setdefault(pattern, kwargs)
    info['service'] = service
    info['func'] = func


def set_localizer_for_languages(event, available_languages,
                                default_locale_name):
    request = event.request
    if request.accept_language:
        accepted = request.accept_language
        locale = accepted.best_match(available_languages, default_locale_name)
        request._LOCALE_ = locale
    localizer = get_localizer(request)
    request.localizer = localizer


def includeme(config):
    """Include the Cornice definitions
    """
    from pyramid.events import BeforeRender, NewRequest

    # attributes required to maintain services
    config.registry.cornice_services = {}

    # config.add_directive('add_apidoc', add_apidoc)
    config.add_directive('add_cornice_service', register_service_views)
    config.add_directive('add_cornice_resource', register_resource_views)
    config.add_directive('add_cornice_deserializer', add_deserializer)
    config.add_subscriber(add_renderer_globals, BeforeRender)
    config.add_subscriber(wrap_request, NewRequest)
    config.add_renderer('simplejson', util.json_renderer)
    config.add_view_predicate('content_type', ContentTypePredicate)
    config.add_cornice_deserializer('application/x-www-form-urlencoded',
                                    util.extract_form_urlencoded_data)
    config.add_cornice_deserializer('application/json', util.extract_json_data)

    settings = config.get_settings()
    if settings.get('handle_exceptions', True):
        config.add_view(handle_exceptions, context=Exception,
                        permission=NO_PERMISSION_REQUIRED)
        config.add_view(handle_exceptions, context=HTTPNotFound,
                        permission=NO_PERMISSION_REQUIRED)
        config.add_view(handle_exceptions, context=HTTPForbidden,
                        permission=NO_PERMISSION_REQUIRED)

    if settings.get('available_languages'):
        available_languages = settings['available_languages'].split()
        default_locale_name = settings.get('pyramid.default_locale_name', 'en')
        set_localizer = partial(set_localizer_for_languages,
                                available_languages=available_languages,
                                default_locale_name=default_locale_name)
        config.add_subscriber(set_localizer, NewRequest)
        config.add_translation_dirs('colander:locale/')
