# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice import Service
try:
    import venusian
    VENUSIAN = True
except ImportError:
    VENUSIAN = False
import functools


def resource(depth=1, **kw):
    """Class decorator to declare resources.

    All the methods of this class named by the name of HTTP resources
    will be used as such. You can also prefix them by "collection_" and they
    will be treated as HTTP methods for the given collection path
    (collection_path), if any.
    
    Here is an example::

        @resource(collection_path='/users', path='/users/{id}')
        
    You can also add any other prefixed path like e.g. "activate_path".
    This may be useful when defining sub-resources.

    Here is an example::

        @resource(collection_path='/users', path='/users/{id}', 
                  activate_path='/users/{id}/activate')
    """
    def wrapper(klass):
        services = {}

        path_keys = [x[:len(x)-len('path')] for x in list(kw) if x.endswith('_path')]
        if len(path_keys) > 0:
            prefixes = tuple(path_keys + [''])
        else:
            prefixes = ('',)
        
        def filter_prefixes(prefix, x):
            """Filters out keys for prefixes other than specified prefix.
            """
            other = set(prefixes) - set(['', prefix])
            return len([y for y in other if x.startswith(y)]) == 0
        
        for prefix in prefixes:

            # get clean view arguments
            service_args = {}
            
            filter_other = filter(functools.partial(filter_prefixes, prefix), list(kw))
            
            for k in filter_other:
                if k.startswith(prefix):
                    service_args[k[len(prefix):]] = kw[k]
                elif k not in service_args:
                    service_args[k] = kw[k]

            if prefix != '':
                prefix_acl = prefix + '_acl'
                if service_args.get(prefix_acl):
                    service_args['acl'] = service_args[prefix_acl]

            # create service
            service_name = (service_args.pop('name', None) or
                            klass.__name__.lower())
            service_name = prefix + service_name
            service = services[service_name] = Service(name=service_name,
                                                       depth=2, **service_args)

            # initialize views
            for verb in ('get', 'post', 'put', 'delete', 'options', 'patch'):

                view_attr = prefix + verb
                meth = getattr(klass, view_attr, None)

                if meth is not None:
                    # if the method has a __views__ arguments, then it had
                    # been decorated by a @view decorator. get back the name of
                    # the decorated method so we can register it properly
                    views = getattr(meth, '__views__', [])
                    if views:
                        for view_args in views:
                            service.add_view(verb, view_attr, klass=klass,
                                             **view_args)
                    else:
                        service.add_view(verb, view_attr, klass=klass)

        setattr(klass, '_services', services)

        if VENUSIAN:
            def callback(context, name, ob):
                # get the callbacks registred by the inner services
                # and call them from here when the @resource classes are being
                # scanned by venusian.
                for service in services.values():
                    config = context.config.with_package(info.module)
                    config.add_cornice_service(service)

            info = venusian.attach(klass, callback, category='pyramid',
                                   depth=depth)
        return klass
    return wrapper


def view(**kw):
    """Method decorator to store view arguments when defining a resource with
    the @resource class decorator
    """
    def wrapper(func):
        # store view argument to use them later in @resource
        views = getattr(func, '__views__', None)
        if views is None:
            views = []
            setattr(func, '__views__', views)
        views.append(kw)
        return func
    return wrapper
