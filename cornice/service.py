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


_SERVICES = {}


def get_service(pattern):
    return _SERVICES.get(pattern)


class Service(object):
    def __init__(self, **kw):
        self.route_pattern = kw.pop('path')
        if self.route_pattern in _SERVICES:
            raise ValueError('%r already defined' % self.route_pattern)
        self.defined_methods = []
        self.route_name = self.route_pattern
        self.renderer = kw.pop('renderer', 'json')
        self.kw = kw
        _SERVICES[self.route_pattern] = self
        self._defined = False

    def _define(self, config, method):
        # registring the method
        if method not in self.defined_methods:
            self.defined_methods.append(method)

        if not self._defined:
            # defining the route
            config.add_route(self.route_name, self.route_pattern)
            self._defined = True

    def api(self, **kw):
        method = kw.get('request_method', 'GET')
        api_kw = {}
        api_kw.update(kw)

        if 'renderer' not in api_kw:
            api_kw['renderer'] = self.renderer

        def _api(func):
            _api_kw = api_kw.copy()
            docstring = func.__doc__

            def callback(context, name, ob):
                config = context.config.with_package(info.module)
                self._define(config, method)
                config.add_apidoc((self.route_pattern, method),
                                   docstring, self.renderer)
                config.add_view(view=ob, route_name=self.route_name,
                                **_api_kw)

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
