# -*- coding: utf-8 -*-
from cornice import Service


def resource(**kw):
    def wrapper(klass):
        services = {}

        if 'collection_path' in kw:
            prefixes = ('collection_', '')
        else:
            prefixes = ('',)

        for prefix in prefixes:

            # get clean view arguments
            service_args = {}
            for k in list(kw):
                if k.startswith('collection_'):
                    if prefix == 'collection_':
                        service_args[k[len(prefix):]] = kw[k]
                elif k not in service_args:
                    service_args[k] = kw[k]

            # create service
            service_name = prefix + klass.__name__.lower()
            service = services[service_name] = Service(name=service_name,
                                                       **service_args)

            # initialize views
            for verb in ('get', 'post', 'put', 'delete'):
                view_attr = prefix + verb
                meth = getattr(klass, view_attr, None)
                if meth is not None:
                    views = getattr(meth, '__views__', [])
                    verb_dec = getattr(service, verb)
                    if views:
                        for view_args in views:
                            view_args = dict(service_args, **view_args)
                            view_args['attr'] = view_attr
                            del view_args['path']
                            verb_dec(**view_args)(klass)
                    else:
                        verb_dec(attr=view_attr)(klass)

        setattr(klass, '_services', services)
        return klass
    return wrapper


def view(**kw):
    def wrapper(func):
        # store view argument to use them later in @resource
        views = getattr(func, '__views__', None)
        if views is None:
            views = []
            setattr(func, '__views__', views)
        views.append(kw)
        return func
    return wrapper
