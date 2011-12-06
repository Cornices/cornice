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
import json
from StringIO import StringIO

from pyramid import testing

from cornice import Service
from cornice.tests import CatchErrors


service1 = Service(name="service1", path="/service1")


@service1.get()
def get1(request):
    return {"test": "succeeded"}


@service1.post()
def post1(request):
    return {"body": request.body}


def make_request(**kwds):
    environ = {}
    environ["wsgi.version"] = (1, 0)
    environ["wsgi.url_scheme"] = "http"
    environ["SERVER_NAME"] = "localhost"
    environ["SERVER_PORT"] = "80"
    environ["REQUEST_METHOD"] = "GET"
    environ["SCRIPT_NAME"] = ""
    environ["PATH_INFO"] = "/"
    environ.update(kwds)
    return testing.DummyRequest(environ=environ)


class TestServiceDefinition(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_service_definition")

    def tearDown(self):
        testing.tearDown()

    def test_basic_service_operation(self):
        app = CatchErrors(self.config.make_wsgi_app())

        # An unknown URL raises HTTPNotFound
        def start_response(status, headers, exc_info=None):
            pass
        req = make_request(PATH_INFO="/unknown")
        res = app(req.environ, start_response)
        self.assertTrue(res[0].startswith('404'))

        # A request to the service calls the apppriate view function.
        req = make_request(PATH_INFO="/service1")
        result = json.loads("".join(app(req.environ, start_response)))
        self.assertEquals(result["test"], "succeeded")

        req = make_request(PATH_INFO="/service1", REQUEST_METHOD="POST")
        req.environ["wsgi.input"] = StringIO("BODY")
        result = json.loads("".join(app(req.environ, start_response)))
        self.assertEquals(result["body"], "BODY")

    def test_loading_into_multiple_configurators(self):
        # When initializing a second configurator, it shouldn't interfere
        # with the one already in place.
        config2 = testing.setUp()
        config2.include("cornice")
        config2.scan("cornice.tests.test_service_definition")

        # Calling the new configurator works as expected.
        def start_response(status, headers, exc_info=None):
            pass
        app = config2.make_wsgi_app()
        req = make_request(PATH_INFO="/service1")
        result = json.loads("".join(app(req.environ, start_response)))
        self.assertEquals(result["test"], "succeeded")

        # Calling the old configurator works as expected.
        app = self.config.make_wsgi_app()
        req = make_request(PATH_INFO="/service1")
        result = json.loads("".join(app(req.environ, start_response)))
        self.assertEquals(result["test"], "succeeded")
