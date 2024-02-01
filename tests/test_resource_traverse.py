# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from cornice.resource import resource, view
from pyramid import testing
from webtest import TestApp

from .support import CatchErrors, TestCase


FRUITS = {"1": {"name": "apple"}, "2": {"name": "orange"}}


class FruitFactory(object):
    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        return FRUITS[key]


@resource(
    collection_path="/fruits/",
    collection_factory=FruitFactory,
    collection_traverse="",
    path="/fruits/{fruit_id}/",
    factory=FruitFactory,
    name="fruit_service",
    traverse="/{fruit_id}",
)
class Fruit(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    def collection_get(self):
        return {"fruits": list(FRUITS.keys())}

    @view(renderer="json")
    def get(self):
        return self.context


class TestResourceTraverse(TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")

        self.config.scan("tests.test_resource_traverse")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_collection_traverse(self):
        resp = self.app.get("/fruits/").json
        self.assertEqual(sorted(resp["fruits"]), ["1", "2"])

    def test_traverse(self):
        resp = self.app.get("/fruits/1/")
        self.assertEqual(resp.json, {"name": "apple"})

        resp = self.app.get("/fruits/2/")
        self.assertEqual(resp.json, {"name": "orange"})

        self.app.get("/fruits/3/", status=404)
