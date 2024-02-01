# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import functools
import json
from unittest import mock

from cornice.resource import resource, view
from pyramid import testing
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import HTTPForbidden, HTTPOk
from pyramid.security import Allow
from webtest import TestApp

from .support import CatchErrors, TestCase, dummy_factory


USERS = {1: {"name": "gawel"}, 2: {"name": "tarek"}}


def my_collection_acl(request):
    return [(Allow, "alice", "read")]


@resource(collection_path="/thing", path="/thing/{id}", name="thing_service")
class Thing(object):
    """This is a thing."""

    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def __acl__(self):
        return my_collection_acl(self.request)

    @view(permission="read")
    def collection_get(self):
        return "yay"


@resource(collection_path="/users", path="/users/{id}", name="user_service", factory=dummy_factory)
class User(object):
    """My user resource."""

    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def collection_get(self):
        return {"users": list(USERS.keys())}

    @view(renderer="jsonp", accept="application/javascript")
    @view(renderer="json")
    def get(self):
        return USERS.get(int(self.request.matchdict["id"]))

    @view(renderer="json", accept="application/json")
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
        @resource(
            collection_path="/badthing/{id}", path="/badthing/{id}", name="bad_thing_service"
        )
        class BadThing(object):
            def __init__(self, request, context=None):
                pass

        msg = "Warning: collection_path and path are not distinct."
        mocked_warn.assert_called_with(msg)

    @mock.patch("warnings.warn")
    def test_routes_clash(self, mocked_warn):
        @resource(
            collection_pyramid_route="some_route",
            pyramid_route="some_route",
            name="bad_thing_service",
        )
        class BadThing(object):
            def __init__(self, request, context=None):
                pass

        msg = "Warning: collection_pyramid_route and " "pyramid_route are not distinct."
        mocked_warn.assert_called_with(msg)

    def test_routes_with_paths(self):
        with self.assertRaises(ValueError):

            @resource(
                collection_path="/some_route", pyramid_route="some_route", name="bad_thing_service"
            )
            class BadThing(object):
                def __init__(self, request, context=None):
                    pass

    def test_routes_with_paths_reversed(self):
        with self.assertRaises(ValueError):

            @resource(
                collection_pyramid_route="some_route", path="/some_route", name="bad_thing_service"
            )
            class BadThing(object):
                def __init__(self, request, context=None):
                    pass


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
        self.config.scan("tests.test_resource")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_basic_resource(self):
        self.assertEqual(self.app.get("/users").json, {"users": [1, 2]})

        self.assertEqual(self.app.get("/users/1").json, {"name": "gawel"})

        resp = self.app.get("/users/1?callback=test", headers={"Accept": "application/javascript"})

        self.assertIn(b'test({"name": "gawel"})', resp.body, msg=resp.body)

    @mock.patch("cornice.resource.Service")
    def test_without_collection_path_has_one_service(self, mocked_service):
        @resource(path="/nocollection/{id}", name="nocollection")
        class NoCollection(object):
            def __init__(self, request, context=None):
                pass

        self.assertEqual(mocked_service.call_count, 1)

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

    @mock.patch("cornice.resource.Service")
    def test_factory_is_autowired(self, mocked_service):
        @resource(collection_path="/list", path="/list/{id}", name="list")
        class List(object):
            pass

        factory_args = [kw.get("factory") for _, kw in mocked_service.call_args_list]
        self.assertEqual([List, List], factory_args)

    def test_acl_is_deprecated(self):
        def custom_acl(request):
            return []

        with self.assertRaises(ConfigurationError):

            @resource(
                collection_path="/list",
                path="/list/{id}",
                name="list",
                collection_acl=custom_acl,
                acl=custom_acl,
            )
            class List(object):
                pass

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

    def test_service_wrapped_resource(self):
        resources = {
            "thing_service": Thing,
            "user_service": User,
        }

        for name, service in (
            (x.name, x)
            for x in self.config.registry.cornice_services.values()
            if x.name in resources
        ):
            for attr in functools.WRAPPER_ASSIGNMENTS:
                with self.subTest(service=name, attribute=attr):
                    self.assertEqual(
                        getattr(resources[name], attr, None), getattr(service, attr, None)
                    )


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
        self.config.scan("tests.test_resource")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_get(self):
        self.app.get("/users/1")
