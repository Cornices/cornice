# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import warnings
import functools

import venusian

from cornice.util import to_list, json_error, match_accept_header
from cornice.validators import (
        DEFAULT_VALIDATORS,
        DEFAULT_FILTERS,
        validate_colander_schema
)
from cornice.schemas import CorniceSchema


_CORNICE_ARGS = ('validators', 'filters', 'schema')


def call_service(func, api_kwargs, context, request):
    """Wraps the request and the response, once a route does match."""

    # apply validators
    for validator in api_kwargs.get('validators', []):
        validator(request)
        if len(request.errors) > 0:
            return json_error(request.errors)

    return func(request)


class Service(object):
    """Represents a service.

    A service is composed of one path and several possible methods, associated
    to python callables.

    Options can be passed to a service.

    :param name: the name of the service. Should be unique.

    :param path: the path the service is available at. Should also be unique.

    :param renderer: the renderer that should be used by this service. Default
                     value is 'simplejson'.

    :param description: the description of what the webservice does. This is
                        primarily intended for documentation purposes.

    :param validators: a list of validators (callables) to pass the request
                       into before passing it to the callable.

    :param filters: a list of filters (callables) to pass the response into
                    before returning it to the client.

    :param accept: a list of headers accepted for this service (or method if
                   overwritten when defining a method)

    :param factory: A factory returning callables that return true or false,
                    function of the given request. Exclusive with the 'acl'
                    option.

    :param acl: a callable that define the ACL (returns true or false, function
                of the given request. Exclusive with the 'factory' option.

    See
    http://readthedocs.org/docs/pyramid/en/1.0-branch/glossary.html#term-acl
    for more information about ACLs.
    """

    def __init__(self, **kw):
        self.defined_methods = []
        self.name = kw.pop('name')
        self.route_pattern = kw.pop('path')
        self.route_name = self.route_pattern
        self.renderer = kw.pop('renderer', 'simplejson')
        self.description = kw.pop('description', None)
        self.factory = kw.pop('factory', None)
        self.acl_factory = kw.pop('acl', None)
        self.schemas = {}
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

    # Aliases for the most common verbs
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
        """Decorates a function to make it a service.

        Options can be passed to the decorator. The methods get, post, put and
        delete are aliases to this one, specifying the "request_method"
        argument for convenience.

        ;param request_method: the request method. Should be one of GET, POST,
                               PUT, DELETE, OPTIONS, HEAD, TRACE or CONNECT

        All the constructor options, minus name and path, can be overwritten in
        here.
        """

        method = kw.get('request_method', 'GET')  # default is GET
        api_kw = self.kw.copy()
        api_kw.update(kw)

        # sanitize the keyword arguments
        if 'renderer' not in api_kw:
            api_kw['renderer'] = self.renderer

        if 'validator' in api_kw:
            msg = "'validator' is deprecated, please use 'validators'"
            warnings.warn(msg, DeprecationWarning)
            api_kw['validators'] = api_kw.pop('validator')

        validators = []
        validators.extend(to_list(api_kw.get('validators', [])))
        validators.extend(DEFAULT_VALIDATORS)

        filters = []
        filters.extend(to_list(api_kw.get('filters', [])))
        filters.extend(DEFAULT_FILTERS)

        # excluded validators/filters
        for item in to_list(api_kw.pop('exclude', [])):
            for items in validators, filters:
                if item in items:
                    items.remove(item)

        if 'schema' in api_kw:
            schema = CorniceSchema.from_colander(api_kw.pop('schema'))
            validators.append(validate_colander_schema(schema))
            self.schemas[method] = schema

        api_kw['filters'] = filters
        api_kw['validators'] = validators

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
                                        **_view_kw)
                else:
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
