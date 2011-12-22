# -*- coding: utf-8 -*-
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
#   Gael Pasgrimaud (gael@gawel.org)
#   Alexis Métaireau (alexis@mozilla.com)
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
