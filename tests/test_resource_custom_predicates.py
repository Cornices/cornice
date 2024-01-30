# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.resource import resource, view
from pyramid import testing
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from webtest import TestApp

from .support import CatchErrors, TestCase


class employeeType(object):
    def __init__(self, val, config):
        self.val = val

    def text(self):
        return "position = %s" % (self.val,)

    phash = text

    def __call__(self, context, request):
        if request.params.get("position") is not None:
            position = request.params.get("position")
            return position == self.val
        return False


@resource(
    collection_path="/company/employees",
    path="/company/employees/{id}",
    name="Topmanagers",
    position="topmanager",
)
class EManager(object):
    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    @view(renderer="json", accept="application/json")
    def collection_get(self):
        return ["Topmanagers list get"]

    @view(renderer="json", accept="application/json")
    def get(self):
        return {"get": "Topmanagers"}

    @view(renderer="json", accept="application/json")
    def collection_post(self):
        return ["Topmanagers list post"]

    @view(renderer="json", accept="application/json")
    def patch(self):
        return {"patch": "Topmanagers"}

    @view(renderer="json", accept="application/json")
    def put(self):
        return {"put": "Topmanagers"}


@resource(
    collection_path="/company/employees",
    path="/company/employees/{id}",
    name="Supervisors",
    position="supervisor",
)
class ESupervisor(object):
    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    @view(renderer="json", accept="application/json")
    def collection_get(self):
        return ["Supervisors list get"]

    @view(renderer="json", accept="application/json")
    def get(self):
        return {"get": "Supervisors"}

    @view(renderer="json", accept="application/json")
    def collection_post(self):
        return ["Supervisors list post"]

    @view(renderer="json", accept="application/json")
    def patch(self):
        return {"patch": "Supervisors"}

    @view(renderer="json", accept="application/json")
    def put(self):
        return {"put": "Supervisors"}


class TestCustomPredicates(TestCase):
    def setUp(self):
        from pyramid.renderers import JSONP

        self.config = testing.setUp()
        self.config.add_renderer("jsonp", JSONP(param_name="callback"))
        self.config.include("cornice")
        self.authz_policy = ACLAuthorizationPolicy()
        self.config.set_authorization_policy(self.authz_policy)

        self.authn_policy = AuthTktAuthenticationPolicy("$3kr1t")
        self.config.set_authentication_policy(self.authn_policy)
        self.config.add_route_predicate("position", employeeType)
        self.config.scan("tests.test_resource_custom_predicates")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_get_resource_predicates(self):
        # Tests for resource with name 'Supervisors'
        res = self.app.get("/company/employees?position=supervisor").json
        self.assertEqual(res[0], "Supervisors list get")
        res = self.app.get("/company/employees/2?position=supervisor").json
        self.assertEqual(res["get"], "Supervisors")

        # Tests for resource with name 'Topmanagers'
        res = self.app.get("/company/employees?position=topmanager").json
        self.assertEqual(res[0], "Topmanagers list get")
        res = self.app.get("/company/employees/1?position=topmanager").json
        self.assertEqual(res["get"], "Topmanagers")

    def test_post_resource_predicates(self):
        # Tests for resource with name 'Supervisors'
        supervisor_data = {"name": "Jimmy Arrow", "position": "supervisor", "salary": 50000}
        res = self.app.post("/company/employees", supervisor_data).json
        self.assertEqual(res[0], "Supervisors list post")

        # Tests for resource with name 'Topmanagers'
        topmanager_data = {"name": "Jimmy Arrow", "position": "topmanager", "salary": 30000}
        res = self.app.post("/company/employees", topmanager_data).json
        self.assertEqual(res[0], "Topmanagers list post")

    def test_patch_resource_predicates(self):
        # Tests for resource with name 'Supervisors'
        res = self.app.patch("/company/employees/2?position=supervisor", {"salary": 1001}).json
        self.assertEqual(res["patch"], "Supervisors")

        # Tests for resource with name 'Topmanagers'
        res = self.app.patch("/company/employees/1?position=topmanager", {"salary": 2002}).json
        self.assertEqual(res["patch"], "Topmanagers")

    def test_put_resource_predicates(self):
        # Tests for resource with name 'Supervisors'
        supervisor_data = {"position": "supervisor", "salary": 53000}
        res = self.app.put("/company/employees/2", supervisor_data).json
        self.assertEqual(res["put"], "Supervisors")

        # Tests for resource with name 'Topmanagers'
        topmanager_data = {"position": "topmanager", "salary": 33000}
        res = self.app.put("/company/employees/1", topmanager_data).json
        self.assertEqual(res["put"], "Topmanagers")
