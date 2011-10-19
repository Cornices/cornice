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
import os

from webob.exc import HTTPNotFound, HTTPMethodNotAllowed

from pyramid.config import Configurator
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.events import BeforeRender

from cornice.resources import Root
from cornice.config import Config
from cornice import util
from cornice.service import Service     # NOQA


def add_renderer_globals(event):
    event['util'] = util


def add_apidoc(config, pattern, docstring, renderer):
    apidocs = config.registry.settings.setdefault('apidocs', {})
    info = apidocs.setdefault(pattern, {})
    info['docstring'] = docstring
    info['renderer'] = renderer


def _notfound(request):
    match = request.matchdict
    # the route exists, raising a 405
    if match is not None:
        pattern = request.matched_route.pattern
        service = request.registry['cornice_services'].get(pattern)
        if service is not None:
            res = HTTPMethodNotAllowed()
            res.allow = service.defined_methods
            return res

    # 404
    return HTTPNotFound()


def main(package=None):
    def _main(global_config, **settings):
        config_file = global_config['__file__']
        config_file = os.path.abspath(
                        os.path.normpath(
                        os.path.expandvars(
                            os.path.expanduser(
                            config_file))))

        settings['config'] = config = Config(config_file)
        conf_dir, _ = os.path.split(config_file)

        authz_policy = ACLAuthorizationPolicy()
        config = Configurator(root_factory=Root, settings=settings,
                              authorization_policy=authz_policy)

        # add auth via repoze.who
        # eventually the app will have to do this explicitly
        config.include("cornice.auth.whoauth")

        # adding default views: __heartbeat__, __apis__
        config.add_route('heartbeat', '/__heartbeat__',
                        renderer='string',
                        view='cornice.views.heartbeat')

        config.add_route('manage', '/__config__',
                        renderer='config.mako',
                        view='cornice.views.manage')

        config.add_static_view('static', 'cornice:static', cache_max_age=3600)
        config.add_directive('add_apidoc', add_apidoc)
        config.add_route('apidocs', '/__apidocs__')
        config.add_view(_notfound, context=HTTPNotFound)
        config.add_subscriber(add_renderer_globals, BeforeRender)
        config.scan()
        config.scan(package=package)
        return config.make_wsgi_app()
    return _main


def make_main(package=None):
    """Factory to build apps."""
    return main(package)
