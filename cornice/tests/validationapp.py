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
#   Alexis Metaireau (alexis@mozilla.com)
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
from pyramid.config import Configurator

from cornice import Service
from cornice.schemas import *  # NOQA
from cornice.tests import CatchErrors


service = Service(name="service", path="/service")


def has_payed(request):
    if not 'paid' in request.GET:
        request.errors.add('body', 'paid', 'You must pay!')


def foo_int(request):
    if 'foo' not in request.GET:
        return
    try:
        request.validated['foo'] = int(request.GET['foo'])
    except ValueError:
        request.errors.add('url', 'foo', 'Not an int')


@service.get(validators=(has_payed, foo_int))
def get1(request):
    res = {"test": "succeeded"}
    try:
        res['foo'] = request.validated['foo']
    except KeyError:
        pass

    return res


def _json(request):
    """The request body should be a JSON object."""
    try:
        request.validated['json'] = json.loads(request.body)
    except ValueError:
        request.errors.add('body', 'json', 'Not a json body')


@service.post(validators=_json)
def post1(request):
    return {"body": request.body}


service2 = Service(name="service2", path="/service2")


@service2.get(accept=("application/json", "text/json"))
def get2(request):
    return {"body": "yay!"}


service3 = Service(name="service3", path="/service3")


def _accept(request):
    return ('text/json', 'application/json')


@service3.get(accept=_accept)
def get3(request):
    return {"body": "yay!"}


def _filter(response):
    response.body = "filtered response"
    return response

# test filtered services
filtered_service = Service(name="filtered", path="/filtered", filters=_filter)


@filtered_service.get()
@filtered_service.post(exclude=_filter)
def get4(request):
    return "unfiltered"  # should be overwritten on GET


def includeme(config):
    config.include("cornice")
    config.scan("cornice.tests.validationapp")


def main(global_config, **settings):
    config = Configurator(settings={})
    config.include(includeme)
    return CatchErrors(config.make_wsgi_app())
