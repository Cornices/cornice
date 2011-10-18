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
""" Cornice default views/.
"""
from pyramid.view import view_config
from webob.exc import HTTPNotFound
from cornice.util import get_config


def heartbeat(request):
    # checks the server's state -- if wrong, return a 503 here
    return 'OK'


def manage(request):
    ## if it's not a local call, this does not exist

    # XXX protect with new auth APIs
    #if not is_local(request):
    #    raise HTTPNotFound()

    # now let's see if the config allows the debug mode
    config = get_config(request)
    if (not config.has_option('global', 'debug') or
        not config.get('global', 'debug')):
        raise HTTPNotFound()

    # local + activated
    return {'config': config}


@view_config(route_name='apidocs', renderer='apidocs.mako')
def apidocs(request):
    routes = []
    for k, v in request.registry.settings['apidocs'].items():
        routes.append((k, v))
    return {'routes': routes}
