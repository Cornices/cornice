# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import json

from pyramid import testing
from webtest import TestApp

from cornice.resource import resource
from cornice.resource import view
from cornice.schemas import CorniceSchema
from cornice.tests import validationapp
from cornice.tests.support import TestCase, CatchErrors
from cornice.tests.support import dummy_factory


USERS = {1: {'name': 'gawel'}, 2: {'name': 'tarek'}}


@resource(collection_path='/users', path='/users/{id}',
          name='user_service', factory=dummy_factory)
class User(object):

    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def collection_get(self):
        return {'users': list(USERS.keys())}

    @view(renderer='jsonp')
    @view(renderer='json')
    def get(self):
        return USERS.get(int(self.request.matchdict['id']))

    @view(renderer='json', accept='text/json')
    #@view(renderer='jsonp', accept='application/json')
    def collection_post(self):
        return {'test': 'yeah'}

    def patch(self):
        return {'test': 'yeah'}

    def collection_patch(self):
        return {'test': 'yeah'}

    def put(self):
        return dict(type=repr(self.context))


class TestResource(TestCase):

    def setUp(self):
        from pyramid.renderers import JSONP
        self.config = testing.setUp()
        self.config.add_renderer('jsonp', JSONP(param_name='callback'))
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_resource")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_basic_resource(self):

        self.assertEqual(self.app.get("/users").json, {'users': [1, 2]})

        self.assertEqual(self.app.get("/users/1").json, {'name': 'gawel'})

        resp = self.app.get("/users/1?callback=test")
        self.assertEqual(resp.body, b'test({"name": "gawel"})', resp.body)

    def test_accept_headers(self):
        # the accept headers should work even in case they're specified in a
        # resource method
        self.assertEqual(
            self.app.post("/users", headers={'Accept': 'text/json'},
                          params=json.dumps({'test': 'yeah'})).json,
            {'test': 'yeah'})

    def patch(self, *args, **kwargs):
        return self.app._gen_request('PATCH', *args, **kwargs)

    def test_head_and_patch(self):
        self.app.head("/users")
        self.app.head("/users/1")

        self.assertEqual(
            self.patch("/users").json,
            {'test': 'yeah'})

        self.assertEqual(
            self.patch("/users/1").json,
            {'test': 'yeah'})

    def test_context_factory(self):
        self.assertEqual(self.app.put('/users/1').json, {'type': 'context!'})

    def test_explicit_collection_service_name(self):
        route_url = testing.DummyRequest().route_url
        self.assert_(route_url('collection_user_service'))  # service must exist

    def test_explicit_service_name(self):
        route_url = testing.DummyRequest().route_url
        self.assert_(route_url('user_service', id=42))  # service must exist

    if validationapp.COLANDER:
        def test_schema_on_resource(self):
            User.schema = CorniceSchema.from_colander(
                    validationapp.FooBarSchema)
            result = self.patch("/users/1", status=400).json
            self.assertEquals(
                [(e['name'], e['description']) for e in result['errors']], [
                    ('foo', 'foo is missing'),
                    ('bar', 'bar is missing'),
                    ('yeah', 'yeah is missing'),
                ])


class NonAutocommittingConfigurationTestResource(TestCase):
    """
    Test that we don't fail Pyramid's conflict detection when using a manually-
    committing :class:`pyramid.config.Configurator` instance.
    """

    def setUp(self):
        from pyramid.renderers import JSONP
        self.config = testing.setUp(autocommit=False)
        self.config.add_renderer('jsonp', JSONP(param_name='callback'))
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_resource")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_get(self):
        self.app.get('/users/1')
