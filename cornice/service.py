# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import functools
import warnings

from cornice.validators import (
    DEFAULT_VALIDATORS,
    DEFAULT_FILTERS,
)
from cornice.schemas import CorniceSchema, validate_colander_schema
from cornice.util import to_list, json_error

try:
    import venusian
    VENUSIAN = True
except ImportError:
    VENUSIAN = False

SERVICES = []


def clear_services():
    SERVICES[:] = []


def get_services(names=None, exclude=None):

    def _keep(service):
        if exclude is not None and service.name in exclude:
            # excluded !
            return False

        # in white list or no white list provided
        return names is None or service.name in names

    return [service for service in SERVICES if _keep(service)]


class Service(object):
    """Contains a service definition (in the definition attribute).

    A service is composed of a path and many potential methods, associated
    with context.

    All the class attributes defined in this class or in childs are considered
    default values.

    :param name:
        The name of the service. Should be unique among all the services.

    :param path:
        The path the service is available at. Should also be unique.

    :param renderer:
        The renderer that should be used by this service. Default value is
        'simplejson'.

    :param description:
        The description of what the webservice does. This is primarily intended
        for documentation purposes.

    :param validators:
        A list of callables to pass the request into before passing it to the
        associated view.

    :param filters:
        A list of callables to pass the response into before returning it to
        the client.

    :param accept:
        A list of headers accepted for this service (or method if overwritten
        when defining a method). It can also be a callable, in which case the
        content-type will be discovered at runtime. If a callable is passed, it
        should be able to take the request as a first argument.

    :param factory:
        A factory returning callables which return boolean values.  The
        callables take the request as their first argument and return boolean
        values.  This param is exclusive with the 'acl' one.

    :param acl:
        A callable defininng the ACL (returns true or false, function of the
        given request). Exclusive with the 'factory' option.

    :param klass:
        The class to use when resolving views (if they are not callables)

    :param error_handler:
        A callable which is used to render responses following validation
        failures.  Defaults to 'json_renderer'.

    There is also a number of parameters that are related to the support of
    CORS (Cross Origin Resource Sharing). You can read the CORS specification
    at http://www.w3.org/TR/cors/

    :param cors_enabled:
        To use if you especially want to disable CORS support for a particular
        service / method.

    :param cors_origins:
        The list of origins for CORS. You can use wildcards here if needed,
        e.g. ('list', 'of', '*.domain').

    :param cors_headers:
        The list of headers supported for the services.

    :param cors_credentials:
        Should the client send credential information (False by default).

    :param cors_max_age:
         Indicates how long the results of a preflight request can be cached in
         a preflight result cache.

    :param cors_expose_all_headers:
        If set to True, all the headers will be exposed and considered valid
        ones (Default: True). If set to False, all the headers need be
        explicitely mentionned with the cors_headers parameter.

    :param cors_policy:
        It may be easier to have an external object containing all the policy
        information related to CORS, e.g::

            >>> cors_policy = {'origins': ('*',), 'max_age': 42,
            ...                'credentials': True}

        You can pass a dict here and all the values will be
        unpacked and considered rather than the parameters starting by `cors_`
        here.

    See
    http://readthedocs.org/docs/pyramid/en/1.0-branch/glossary.html#term-acl
    for more information about ACLs.

    Service cornice instances also have methods :meth:`~get`, :meth:`~post`,
    :meth:`~put`, :meth:`~options` and :meth:`~delete` are decorators that can
    be used to decorate views.
    """
    renderer = 'simplejson'
    default_validators = DEFAULT_VALIDATORS
    default_filters = DEFAULT_FILTERS

    mandatory_arguments = ('renderer',)
    list_arguments = ('validators', 'filters', 'cors_headers', 'cors_origins')

    def __repr__(self):
        return u'<Service %s at %s>' % (self.name, self.path)

    def __init__(self, name, path, description=None, cors_policy=None, depth=1,
                 **kw):
        self.name = name
        self.path = path
        self.description = description
        self.cors_expose_all_headers = True
        self._schemas = {}
        self._cors_enabled = None

        if cors_policy:
            for key, value in cors_policy.items():
                kw.setdefault('cors_' + key, value)

        for key in self.list_arguments:
            # default_{validators,filters} and {filters,validators} doesn't
            # have to be mutables, so we need to create a new list from them
            extra = to_list(kw.get(key, []))
            kw[key] = []
            kw[key].extend(getattr(self, 'default_%s' % key, []))
            kw[key].extend(extra)

        self.arguments = self.get_arguments(kw)
        for key, value in self.arguments.items():
            setattr(self, key, value)

        if hasattr(self, 'factory') and hasattr(self, 'acl'):
            raise KeyError("Cannot specify both 'acl' and 'factory'")

        # instanciate some variables we use to keep track of what's defined for
        # this service.
        self.defined_methods = []
        self.definitions = []

        # add this service to the list of available services
        SERVICES.append(self)

        # register aliases for the decorators
        for verb in ('GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'):
            setattr(self, verb.lower(),
                    functools.partial(self.decorator, verb))

        if VENUSIAN:
            # this callback will be called when config.scan (from pyramid) will
            # be triggered.
            def callback(context, name, ob):
                config = context.config.with_package(info.module)
                config.add_cornice_service(self)

            info = venusian.attach(self, callback, category='pyramid',
                                   depth=depth)

    def get_arguments(self, conf=None):
        """Return a dictionnary of arguments. Takes arguments from the :param
        conf: param and merges it with the arguments passed in the constructor.

        :param conf: the dictionnary to use.
        """
        if conf is None:
            conf = {}

        arguments = {}
        for arg in self.mandatory_arguments:
            # get the value from the passed conf, then from the instance, then
            # from the default class settings.
            arguments[arg] = conf.pop(arg, getattr(self, arg, None))

        for arg in self.list_arguments:
            # rather than overwriting, extend the defined lists if any.
            # take care of re-creating the lists before appening items to them,
            # to avoid modifications to the already existing ones
            value = list(getattr(self, arg, []))
            if arg in conf:
                value.extend(to_list(conf.pop(arg)))
            arguments[arg] = value

        # schema validation handling
        if 'schema' in conf:
            arguments['schema'] = (
                CorniceSchema.from_colander(conf.pop('schema')))

        # Allow custom error handler
        arguments['error_handler'] = conf.pop('error_handler', json_error)

        # exclude some validators or filters
        if 'exclude' in conf:
            for item in to_list(conf.pop('exclude')):
                for container in arguments['validators'], arguments['filters']:
                    if item in container:
                        container.remove(item)

        # also include the other key,value pair we don't know anything about
        arguments.update(conf)

        # if some keys have been defined service-wide, then we need to add
        # them to the returned dict.
        if hasattr(self, 'arguments'):
            for key, value in self.arguments.items():
                if key not in arguments:
                    arguments[key] = value

        return arguments

    def add_view(self, method, view, **kwargs):
        """Add a view to a method and arguments.

        All the :class:`Service` keyword params except `name` and `path`
        can be overwritten here. Additionally,
        :meth:`~cornice.service.Service.api` has following keyword params:

        :param method: The request method. Should be one of GET, POST, PUT,
                       DELETE, OPTIONS, TRACE or CONNECT.
        :param view: the view to hook to
        :param **kwargs: additional configuration for this view
        """
        method = method.upper()
        if 'schema' in kwargs:
            # this is deprecated and unusable because multiple schema
            # definitions for the same method will overwrite each other.
            # still here for legacy reasons: you'll get a warning if you try to
            # use it.
            self._schemas[method] = kwargs['schema']

        args = self.get_arguments(kwargs)
        if hasattr(self, 'get_view_wrapper'):
            view = self.get_view_wrapper(kwargs)(view)
        self.definitions.append((method, view, args))

        # keep track of the defined methods for the service
        if method not in self.defined_methods:
            self.defined_methods.append(method)

        # auto-define a HEAD method if we have a definition for GET.
        if method == 'GET':
            self.definitions.append(('HEAD', view, args))
            if 'HEAD' not in self.defined_methods:
                self.defined_methods.append('HEAD')

    def decorator(self, method, **kwargs):
        """Add the ability to define methods using python's decorators
        syntax.

        For instance, it is possible to do this with this method::

            service = Service("blah", "/blah")
            @service.decorator("get", accept="application/json")
            def my_view(request):
                pass
        """
        def wrapper(view):
            self.add_view(method, view, **kwargs)
            return view
        return wrapper

    def get_acceptable(self, method, filter_callables=False):
        """return a list of acceptable content-type headers that were defined
        for this service.

        :param method: the method to get the acceptable content-types for
        :param filter_callables: it is possible to give acceptable
                                 content-types dinamycally, with callables.
                                 This filter or not the callables (default:
                                 False)
        """
        acceptable = []
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper():
                acc = to_list(args.get('accept'))
                if filter_callables:
                    acc = [a for a in acc if not callable(a)]
                acceptable.extend(acc)
        return acceptable

    def get_validators(self, method):
        """return a list of validators for the given method.

        :param method: the method to get the validators for.
        """
        validators = []
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper() and 'validators' in args:
                for validator in args['validators']:
                    if validator not in validators:
                        validators.append(validator)
        return validators

    def schemas_for(self, method):
        """Returns a list of schemas defined for a given HTTP method.

        A tuple is returned, containing the schema and the arguments relative
        to it.
        """
        schemas = []
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper() and 'schema' in args:
                schemas.append((args['schema'], args))
        return schemas

    @property
    def schemas(self):
        """Here for backward compatibility with the old API."""
        msg = "'Service.schemas' is deprecated. Use 'Service.definitions' "\
              "instead."
        warnings.warn(msg, DeprecationWarning)
        return self._schemas

    @property
    def cors_enabled(self):
        if self._cors_enabled is False:
            return False

        return bool(self.cors_origins or self._cors_enabled)

    @cors_enabled.setter
    def cors_enabled(self, value):
        self._cors_enabled = value

    @property
    def cors_supported_headers(self):
        """Return an iterable of supported headers for this service.

        The supported headers are defined by the :param headers: argument
        that is passed to services or methods, at definition time.
        """
        headers = set()
        for _, _, args in self.definitions:
            if args.get('cors_enabled', True):
                headers |= set(args.get('cors_headers', ()))
        return headers

    @property
    def cors_supported_methods(self):
        """Return an iterable of methods supported by CORS"""
        methods = []
        for meth, _, args in self.definitions:
            if args.get('cors_enabled', True) and meth not in methods:
                methods.append(meth)
        return methods

    @property
    def cors_supported_origins(self):
        origins = set(getattr(self, 'cors_origins', ()))
        for _, _, args in self.definitions:
            origins |= set(args.get('cors_origins', ()))
        return origins

    def cors_origins_for(self, method):
        """Return the list of origins supported for a given HTTP method"""
        origins = set()
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper():
                origins |= set(args.get('cors_origins', ()))

        if not origins:
            origins = self.cors_origins
        return origins

    def cors_support_credentials(self, method=None):
        """Returns if the given method support credentials.

        :param method:
            The method to check the credentials support for
        """
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper():
                return args.get('cors_credentials', False)

        if getattr(self, 'cors_credentials', False):
            return self.cors_credentials
        return False

    def cors_max_age_for(self, method=None):
        for meth, view, args in self.definitions:
            if meth.upper() == method.upper():
                return args.get('cors_max_age', False)

        return getattr(self, 'cors_max_age', None)


def decorate_view(view, args, method):
    """Decorate a given view with cornice niceties.

    This function returns a function with the same signature than the one
    you give as :param view:

    :param view: the view to decorate
    :param args: the args to use for the decoration
    :param method: the HTTP method
    """
    def wrapper(request):
        # if the args contain a klass argument then use it to resolve the view
        # location (if the view argument isn't a callable)
        ob = None
        view_ = view
        if 'klass' in args:
            ob = args['klass'](request)
            if isinstance(view, basestring):
                view_ = getattr(ob, view.lower())

        # do schema validation
        if 'schema' in args:
            validate_colander_schema(args['schema'], request)

        # the validators can either be a list of callables or contain some
        # non-callable values. In which case we want to resolve them using the
        # object if any
        validators = args.get('validators', ())
        for validator in validators:
            if isinstance(validator, basestring) and ob is not None:
                validator = getattr(ob, validator)
            validator(request)

        # only call the view if we don't have validation errors
        if len(request.errors) == 0:
            # if we have an object, the request had already been passed to it
            if ob:
                response = view_()
            else:
                response = view_(request)

        # check for errors and return them if any
        if len(request.errors) > 0:
            return args['error_handler'](request.errors)

        # We can't apply filters at this level, since "response" may not have
        # been rendered into a proper Response object yet.  Instead, give the
        # request a reference to its api_kwargs so that a tween can apply them.
        # We also pass the object we created (if any) so we can use it to find
        # the filters that are in fact methods.
        request.cornice_args = (args, ob)
        return response

    # return the wrapper, not the function, keep the same signature
    functools.wraps(wrapper)
    return wrapper
