# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import json
import warnings
import functools

import venusian

from pyramid.exceptions import PredicateMismatch
from pyramid.httpexceptions import HTTPMethodNotAllowed, HTTPNotAcceptable

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

    response = func(request)

    # We can't apply filters at this level, since "response" may not have
    # been rendered into a proper Response object yet.  Instead, give the
    # request a reference to its api_kwargs so that a tween can apply them.
    request.cornice_api_kwargs = api_kwargs

    return response


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
        self.definitions = []

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
            config.add_view(view=self._fallback_view,
                            route_name=self.route_name)

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

    def options(self, **kw):
        return self.api(request_method='OPTIONS', **kw)

    def get_view_wrapper(self, kw):
        """
        Overload this method if you would like to wrap the API function
        function just before it is registered as a view callable. This will be
        called with the api() call kwargs, it should return a callable which
        accepts a single function and returns a single function. Right before
        view registration, this will be called w/ the function to register, and
        the return value will be registered in its stead. By default this
        simply returns the same function it was passed.
        """
        return lambda func: func

    # the actual decorator
    def api(self, **kw):
        """Decorates a function to make it a service.

        Options can be passed to the decorator. The methods get, post, put and
        delete are aliases to this one, specifying the "request_method"
        argument for convenience.

        :param request_method: the request method. Should be one of GET, POST,
                               PUT, DELETE, OPTIONS, HEAD, TRACE or CONNECT
        :param decorators: A sequence of decorators which should be applied
                           to the view callable before it's returned. Will be
                           applied in order received, i.e. the last decorator
                           in the sequence will be the outermost wrapper.

        All the constructor options, minus name and path, can be overwritten in
        here.
        """
        view_wrapper = self.get_view_wrapper(kw)
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
            self.definitions.append(_api_kw)

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
                    view = functools.partial(call_service, view, _api_kw)
                else:
                    view = functools.partial(call_service, ob, _api_kw)

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

            func = view_wrapper(func)
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

    def _fallback_view(self, request):
        """Fallback view for this service, called when nothing else matches.

        This method provides the view logic to be executed when the request
        does not match any explicitly-defined view.  Its main responsibility
        is to produce an accurate error response, such as HTTPMethodNotAllowed
        or HTTPNotAcceptable.
        """
        # Maybe we failed to match any definitions for the request method?
        if request.method not in self.defined_methods:
            response = HTTPMethodNotAllowed()
            response.allow = self.defined_methods
            return response
        # Maybe we failed to match an acceptable content-type?
        # First search all the definitions to find the acceptable types.
        # XXX: precalculate this like the defined_methods list?
        acceptable = []
        for api_kwargs in self.definitions:
            if api_kwargs['request_method'] != request.method:
                continue
            if 'accept' in api_kwargs:
                accept = to_list(api_kwargs.get('accept'))
                acceptable.extend(a for a in accept if not callable(a))
                if 'acceptable' in request.info:
                    for content_type in request.info['acceptable']:
                        if content_type not in acceptable:
                            acceptable.append(content_type)
        # Now check if that was actually the source of the problem.
        if not request.accept.best_match(acceptable):
            response = HTTPNotAcceptable()
            response.content_type = "application/json"
            response.body = json.dumps(acceptable)
            return response
        # In the absence of further information about what went wrong,
        # let upstream deal with the mismatch.
        raise PredicateMismatch(self.name)
