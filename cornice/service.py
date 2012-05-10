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


class Service(object):
    """Contains a service definition (in the definition attribute).

    A service is composed of one path and many potential methods, associated
    with context.

    All the class attributes defined in this class or in childs are considered
    default values.

    :param name: the name of the service. Should be unique among all the
                 services.

    :param path: the path the service is available at. Should also be unique.

    :param renderer: the renderer that should be used by this service. Default
                     value is 'simplejson'.

    :param description: the description of what the webservice does. This is
                        primarily intended for documentation purposes.

    :param validators: a list of callables to pass the request into before
                       passing it to the associated view.

    :param filters: a list of callables to pass the response into before
                    returning it to the client.

    :param accept: a list of headers accepted for this service (or method if
                   overwritten when defining a method). It can also be a
                   callable, in which case the content-type will be discovered
                   at runtime. If a callable is passed, it should be able to
                   take the request as a first argument.

    :param factory: A factory returning callables which return boolean values.
                    The callables take the request as their first argument and
                    return boolean values.
                    This param is exclusive with the 'acl' one.

    :param acl: a callable defininng the ACL (returns true or false, function
                of the given request). Exclusive with the 'factory' option.

    :param klass: the class to use when resolving views (if they are not
                  callables)
    See
    http://readthedocs.org/docs/pyramid/en/1.0-branch/glossary.html#term-acl
    for more information about ACLs.
    """
    renderer = 'simplejson'
    mandatory_arguments = ('renderer',)
    list_arguments = ('validators', 'filters')
    default_validators = DEFAULT_VALIDATORS
    default_filters = DEFAULT_FILTERS

    def __repr__(self):
        return u'<Service %s at %s>' % (self.name, self.path)

    def __init__(self, name, path, description=None, depth=1, **kw):
        self.name = name
        self.path = path
        self.description = description
        self._schemas = {}

        self.arguments = self.get_arguments(kw)
        for key, value in self.arguments.items():
            setattr(self, key, value)

        if hasattr(self, 'factory') and hasattr(self, 'acl_factory'):
            raise KeyError("Cannot specify both 'acl_factory' and 'factory'")

        # instanciate some variables we use to keep track of what's defined for
        # this service.
        self.defined_methods = []
        self.definitions = []

        # add this service to the list of available services
        global SERVICES
        SERVICES.append(self)

        # register aliases for the decorators
        for verb in ('GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'):
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
            arguments['schema'] = CorniceSchema.from_colander(
                                    conf.pop('schema'))

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

    def hook_view(self, method, view, **kwargs):
        """Hooks a view to a method and arguments.

        :param method: the HTTP method to hook the view to
        :param view: the view to hook to
        :param **kwargs: additional configuration for this view
        """
        if 'schema' in kwargs:
            # this is deprecated and unusable because multiple schema
            # definitions for the same method will overwrite each other.
            self._schemas[method] = kwargs['schema']

        args = self.get_arguments(kwargs)
        if hasattr(self, 'get_view_wrapper'):
            view = self.get_view_wrapper(kwargs)(view)
        self.definitions.append((method.upper(), view, args))

        # keep track of the defined methods for the service
        if method not in self.defined_methods:
            self.defined_methods.append(method)

    def decorator(self, method, **args):
        """Add the ability to define methods using python's decorators
        syntax.

        For instance, it is possible to do this with this method::

            service = Service("blah", "/blah")
            @service.decorator("get", accept="application/json")
            def my_view(request):
                pass
        """
        def wrapper(view):
            self.hook_view(method, view, **args)
            return view
        return wrapper

    def get_acceptable(self, method, filter_callables=False):
        """return a list of acceptable content-type headers that were defined
        for this service.

        :param method: the method to get the acceptable content-types for
        :param filter_callables: it is possiible to give acceptable
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


def decorate_view(view, args, method):
    """Decorate a given view with cornice niceties.

    This function returns a function with the same signature than the one
    you give as :param view:

    :param view: the view to decorate
    :param args: the args to use for the decoration
    :param method: the HTTP method
    """
    def wrapper(request):
        validators = args.get('validators', ())

        # do schema validation
        if 'schema' in args:
            validate_colander_schema(args['schema'], request)

        for validator in validators:
            validator(request)

        if len(request.errors) > 0:
            return json_error(request.errors)

        response = view(request)

        # We can't apply filters at this level, since "response" may not have
        # been rendered into a proper Response object yet.  Instead, give the
        # request a reference to its api_kwargs so that a tween can apply them.
        request.cornice_args = args
        return response

    # return the wrapper, not the function
    return wrapper
