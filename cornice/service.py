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
# The Original Code is Sync Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
#   Alexis Metaireau (alexis@mozilla.com)
#   Gael Pasgrimaud (gael@gawel.org)
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
import venusian
import functools

from cornice.util import to_list, json_error, match_accept_header


_CORNICE_ARGS = ('validator',)


def call_service(func, api_kwargs, context, request):

    for validator in to_list(api_kwargs.get('validator', [])):
        validator(request)
        if len(request.errors) > 0:
            return json_error(request.errors)

    return func(request)


class Service(object):
    def __init__(self, **kw):
        self.defined_methods = []
        self.name = kw.pop('name')
        self.route_pattern = kw.pop('path')
        self.route_name = self.route_pattern
        self.renderer = kw.pop('renderer', 'simplejson')
        self.description = kw.pop('description', None)
        self.factory = kw.pop('factory', None)
        self.acl_factory = kw.pop('acl', None)
        if self.factory and self.acl_factory:
            raise ValueError("Cannot specify both 'acl' and 'factory'")
        self.kw = kw
        # to keep the order in which the services have been defined
        self.index = -1
        self.definitions = {}

    def __repr__(self):
        return "<%s Service at %s>" % (self.renderer.capitalize(),
                                       self.route_name)

    def _define(self, config, method):
        # setup the services hash if it isn't already
        services = config.registry.setdefault('cornice_services', {})
        if self.index == -1:
            self.index = len(services)

        # define the route if it isn't already
        if self.route_pattern not in services:
            services[self.route_pattern] = self
            route_kw = {}
            if self.factory is not None:
                route_kw["factory"] = self.factory
            elif self.acl_factory is not None:
                route_kw["factory"] = self._make_route_factory()

            config.add_route(self.route_name, self.route_pattern, **route_kw)

        # registers the method
        if method not in self.defined_methods:
            self.defined_methods.append(method)

    def _make_route_factory(self):
        acl_factory = self.acl_factory

        class ACLResource(object):
            def __init__(self, request):
                self.request = request
                self.__acl__ = acl_factory(request)

        return ACLResource

    # Aliases for the three most common verbs
    def post(self, **kw):
        return self.api(request_method='POST', **kw)

    def get(self, **kw):
        return self.api(request_method='GET', **kw)

    def put(self, **kw):
        return self.api(request_method='PUT', **kw)

    def delete(self, **kw):
        return self.api(request_method='DELETE', **kw)

    # the actual decorator
    def api(self, **kw):
        method = kw.get('request_method', 'GET')  # default is GET
        api_kw = self.kw.copy()
        api_kw.update(kw)

        if 'renderer' not in api_kw:
            api_kw['renderer'] = self.renderer

        def _api(func):
            _api_kw = api_kw.copy()
            self.definitions[method] = _api_kw.copy()

            def callback(context, name, ob):
                config = context.config.with_package(info.module)
                self._define(config, method)
                config.add_apidoc((self.route_pattern, method), func, self,
                                  **_api_kw)

                view_kw = _api_kw.copy()

                for arg in _CORNICE_ARGS:
                    view_kw.pop(arg, None)

                # method decorators
                if 'attr' in view_kw:
                    @functools.wraps(getattr(ob, kw['attr']))
                    def view(request):
                        meth = getattr(ob(request), kw['attr'])
                        return meth()
                    del view_kw['attr']
                    view = functools.partial(call_service, view,
                                       self.definitions[method])
                else:
                    view = functools.partial(call_service, ob,
                                       self.definitions[method])

                # set the module of the partial function
                setattr(view, '__module__', getattr(ob, '__module__'))

                # handle accept headers as custom predicates if needed
                if 'accept' in view_kw:
                    for accept in to_list(view_kw.pop('accept', ())):
                        _view_kw = view_kw.copy()

                        predicates = view_kw.get('custom_predicates', [])
                        if callable(accept):
                            predicates.append(
                                    functools.partial(match_accept_header,
                                                      accept))
                            _view_kw['custom_predicates'] = predicates
                        else:
                            _view_kw['accept'] = accept

                config.add_view(view=view, route_name=self.route_name,
                                    **view_kw)

            info = venusian.attach(func, callback, category='pyramid')

            if info.scope == 'class':
                # if the decorator was attached to a method in a class, or
                # otherwise executed at class scope, we need to set an
                # 'attr' into the settings if one isn't already in there
                if 'attr' not in kw:
                    kw['attr'] = func.__name__

            kw['_info'] = info.codeinfo   # fbo "action_method"

            return func
        return _api
