# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from cornice.resource import resource, view
from pyramid import testing
from webtest import TestApp

from .support import CatchErrors, TestCase


FRUITS = {1: {"name": "apple"}, 2: {"name": "orange"}}


def _accept(request):
    return ("text/plain", "application/json")


def _content_type(request):
    return ("text/plain", "application/json")


@resource(collection_path="/fruits", path="/fruits/{id}", name="fruit_service", accept=_accept)
class Fruit(object):
    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def collection_get(self):
        return {"fruits": list(FRUITS.keys())}

    @view(renderer="json", accept=_accept)
    def get(self):
        return FRUITS.get(int(self.request.matchdict["id"]))

    @view(renderer="json", accept=_accept, content_type=_content_type)
    def collection_post(self):
        return {"test": "yeah"}


class TestResource(TestCase):
    def setUp(self):
        from pyramid.renderers import JSONP

        self.config = testing.setUp()
        self.config.add_renderer("jsonp", JSONP(param_name="callback"))
        self.config.include("cornice")

        self.config.scan("tests.test_resource_callable")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_accept_headers_get(self):
        self.assertEqual(
            self.app.get("/fruits", headers={"Accept": "text/plain"}).body, b'{"fruits": [1, 2]}'
        )

        self.assertEqual(
            self.app.get("/fruits", headers={"Accept": "application/json"}).json,
            {"fruits": [1, 2]},
        )

        self.assertEqual(
            self.app.get("/fruits/1", headers={"Accept": "text/plain"}).json, {"name": "apple"}
        )

        self.assertEqual(
            self.app.get("/fruits/1", headers={"Accept": "application/json"}).json,
            {"name": "apple"},
        )

    def test_accept_headers_post(self):
        self.assertEqual(
            self.app.post(
                "/fruits",
                headers={"Accept": "text/plain", "Content-Type": "application/json"},
                params=json.dumps({"test": "yeah"}),
            ).json,
            {"test": "yeah"},
        )

        self.assertEqual(
            self.app.post(
                "/fruits",
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                params=json.dumps({"test": "yeah"}),
            ).json,
            {"test": "yeah"},
        )

    def test_406(self):
        self.app.get("/fruits", headers={"Accept": "text/xml"}, status=406)

        self.app.post(
            "/fruits",
            headers={"Accept": "text/html"},
            params=json.dumps({"test": "yeah"}),
            status=406,
        )

    def test_415(self):
        self.app.post(
            "/fruits",
            headers={"Accept": "application/json", "Content-Type": "text/html"},
            status=415,
        )
