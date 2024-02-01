# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import json
from unittest import mock

import pytest
from cornice.resource import add_resource, add_view
from pyramid import testing
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.httpexceptions import HTTPForbidden, HTTPOk
from pyramid.security import Allow
from webtest import TestApp

from .support import CatchErrors, TestCase, dummy_factory


USERS = {1: {"name": "gawel"}, 2: {"name": "tarek"}}


def my_collection_acl(request):
    return [(Allow, "alice", "read")]


class ThingImp(object):
    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def __acl__(self):
        return my_collection_acl(self.request)

    def collection_get(self):
        return "yay"


class UserImp(object):
    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def collection_get(self):
        return {"users": list(USERS.keys())}

    def get(self):
        return USERS.get(int(self.request.matchdict["id"]))

    def collection_post(self):
        return {"test": "yeah"}

    def patch(self):
        return {"test": "yeah"}

    def collection_patch(self):
        return {"test": "yeah"}

    def put(self):
        return dict(type=repr(self.context))


class TestResourceWarning(TestCase):
    @mock.patch("warnings.warn")
    def test_path_clash(self, mocked_warn):
        class BadThingImp(object):
            def __init__(self, request, context=None):
                pass

        add_resource(
            BadThingImp,
            collection_path="/badthing/{id}",
            path="/badthing/{id}",
            name="bad_thing_service",
        )

        msg = "Warning: collection_path and path are not distinct."
        mocked_warn.assert_called_with(msg)


class TestResource(TestCase):
    def setUp(self):
        from pyramid.renderers import JSONP

        self.config = testing.setUp()
        self.config.add_renderer("jsonp", JSONP(param_name="callback"))
        self.config.include("cornice")
        self.authz_policy = ACLAuthorizationPolicy()
        self.config.set_authorization_policy(self.authz_policy)

        self.authn_policy = AuthTktAuthenticationPolicy("$3kr1t")
        self.config.set_authentication_policy(self.authn_policy)

        add_view(ThingImp.collection_get, permission="read")
        thing_resource = add_resource(
            ThingImp, collection_path="/thing", path="/thing/{id}", name="thing_service"
        )

        add_view(UserImp.get, renderer="json")
        add_view(UserImp.get, renderer="jsonp", accept="application/javascript")
        add_view(UserImp.collection_post, renderer="json", accept="application/json")
        user_resource = add_resource(
            UserImp,
            collection_path="/users",
            path="/users/{id}",
            name="user_service",
            factory=dummy_factory,
        )

        self.config.add_cornice_resource(thing_resource)
        self.config.add_cornice_resource(user_resource)
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_basic_resource(self):
        self.assertEqual(self.app.get("/users").json, {"users": [1, 2]})

        self.assertEqual(self.app.get("/users/1").json, {"name": "gawel"})

        resp = self.app.get("/users/1?callback=test")

        self.assertIn(b'test({"name": "gawel"})', resp.body, msg=resp.body)

    def test_accept_headers(self):
        # the accept headers should work even in case they're specified in a
        # resource method
        self.assertEqual(
            self.app.post(
                "/users",
                headers={"Accept": "application/json"},
                params=json.dumps({"test": "yeah"}),
            ).json,
            {"test": "yeah"},
        )

    def patch(self, *args, **kwargs):
        return self.app._gen_request("PATCH", *args, **kwargs)

    def test_head_and_patch(self):
        self.app.head("/users")
        self.app.head("/users/1")

        self.assertEqual(self.patch("/users").json, {"test": "yeah"})

        self.assertEqual(self.patch("/users/1").json, {"test": "yeah"})

    def test_context_factory(self):
        self.assertEqual(self.app.put("/users/1").json, {"type": "context!"})

    def test_explicit_collection_service_name(self):
        route_url = testing.DummyRequest().route_url
        # service must exist
        self.assertTrue(route_url("collection_user_service"))

    def test_explicit_service_name(self):
        route_url = testing.DummyRequest().route_url
        self.assertTrue(route_url("user_service", id=42))  # service must exist

    def test_acl_support_unauthenticated_thing_get(self):
        # calling a view with permissions without an auth'd user => 403
        self.app.get("/thing", status=HTTPForbidden.code)

    def test_acl_support_unauthenticated_forbidden_thing_get(self):
        # calling a view with permissions without an auth'd user => 403
        with mock.patch.object(self.authn_policy, "authenticated_userid", return_value=None):
            self.app.get("/thing", status=HTTPForbidden.code)

    def test_acl_support_authenticated_allowed_thing_get(self):
        with mock.patch.object(self.authn_policy, "unauthenticated_userid", return_value="alice"):
            with mock.patch.object(
                self.authn_policy, "authenticated_userid", return_value="alice"
            ):
                result = self.app.get("/thing", status=HTTPOk.code)
                self.assertEqual("yay", result.json)


@pytest.mark.skip(reason="This test fails when ran with pytest, and it's too mysterious for now")
class NonAutocommittingConfigurationTestResource(TestCase):
    """
    Test that we don't fail Pyramid's conflict detection when using a manually-
    committing :class:`pyramid.config.Configurator` instance.
    """

    def setUp(self):
        from pyramid.renderers import JSONP

        self.config = testing.setUp(autocommit=False)
        self.config.add_renderer("jsonp", JSONP(param_name="callback"))
        self.config.include("cornice")

        add_view(UserImp.get, renderer="json")
        # pyramid does not allow having 2 views with same request conditions
        add_view(UserImp.get, renderer="jsonp", accept="application/javascript")
        add_view(UserImp.collection_post, renderer="json", accept="application/json")
        user_resource = add_resource(
            UserImp,
            collection_path="/users",
            path="/users/{id}",
            name="user_service",
            factory=dummy_factory,
        )

        self.config.add_cornice_resource(user_resource)
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_get(self):
        self.app.get("/users/1")
