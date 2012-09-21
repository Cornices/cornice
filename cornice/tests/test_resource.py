# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import json

from pyramid import testing
from pyramid.httpexceptions import HTTPOk, HTTPNotFound
from webtest import TestApp

from cornice.resource import resource
from cornice.resource import view
from cornice.tests import CatchErrors
from cornice.tests.support import TestCase


USERS = {1: {'name': 'gawel'}, 2: {'name': 'tarek'}}


@resource(collection_path='/users', path='/users/{id}')
class User(object):

    def __init__(self, request):
        self.request = request

    def collection_get(self):
        return {'users': USERS.keys()}

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

        self.assertEquals(
                self.app.get("/users").json,
                {'users': [1, 2]})

        self.assertEquals(
                self.app.get("/users/1").json,
                {'name': 'gawel'})
        resp = self.app.get("/users/1?callback=test")
        self.assertEquals(resp.body,
                'test({"name": "gawel"})', resp.body)

    def test_accept_headers(self):
        # the accept headers should work even in case they're specified in a
        # resource method
        self.assertEquals(
                self.app.post("/users",
                    headers={'Accept': 'text/json'},
                    params=json.dumps({'test': 'yeah'})).json,
                {'test': 'yeah'})

    def patch(self, *args, **kwargs):
        return self.app._gen_request('PATCH', *args, **kwargs)
    
    def test_head_and_patch(self):
        self.app.head("/users", status=200)
        self.app.head("/users/1", status=200)
        
        self.assertEquals(
                self.patch("/users", status=200).json,
                {'test': 'yeah'})
        self.assertEquals(
                self.patch("/users/1", status=200).json,
                {'test': 'yeah'})

