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

import unittest

from pyramid import testing
from webtest import TestApp

from cornice import Service
from cornice.tests import CatchErrors


service1 = Service(name="service1", path="/service1")
service2 = Service(name="service2", path="/service2")


@service1.get()
def get1(request):
    return {"test": "succeeded"}


@service1.post()
def post1(request):
    return {"body": request.body}


@service2.get(accept="text/html")
@service2.post(accept="audio/ogg")
def get2_or_post2(request):
    return {"test": "succeeded"}


class TestServiceDefinition(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_service_definition")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_basic_service_operation(self):

        self.app.get("/unknown", status=404)
        self.assertEquals(
                self.app.get("/service1").json,
                {'test': "succeeded"})

        self.assertEquals(
                self.app.post("/service1", params="BODY").json,
                {'body': 'BODY'})

    def test_loading_into_multiple_configurators(self):
        # When initializing a second configurator, it shouldn't interfere
        # with the one already in place.
        config2 = testing.setUp()
        config2.include("cornice")
        config2.scan("cornice.tests.test_service_definition")

        # Calling the new configurator works as expected.
        app = TestApp(CatchErrors(config2.make_wsgi_app()))
        self.assertEqual(app.get("/service1").json,
                {'test': 'succeeded'})

        # Calling the old configurator works as expected.
        self.assertEqual(self.app.get("/service1").json,
                {'test': 'succeeded'})

    def test_stacking_api_decorators(self):
        # Stacking multiple @api calls on a single function should
        # register it multiple times, just like @view_config does.
        resp = self.app.get("/service2", headers={'Accept': 'text/html'})
        self.assertEquals(resp.json, {'test': 'succeeded'})

        resp = self.app.post("/service2", headers={'Accept': 'audio/ogg'})
        self.assertEquals(resp.json, {'test': 'succeeded'})
