# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.tests.support import TestCase

from pyramid import testing
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response
from pyramid.security import Allow
import colander

from webtest import TestApp

from cornice import Service
from cornice.tests.support import CatchErrors
from cornice.tests.support import dummy_factory

from cornice.pyramidhook import register_service_views

from mock import MagicMock

service = Service(name="service", path="/service")


@service.get()
def return_404(request):
    raise HTTPNotFound()


def my_acl(request):
    return [(Allow, 'bob', 'write')]


@service.delete(acl=my_acl)
def return_yay(request):
    return "yay"


class TemperatureCooler(object):
    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def get_fresh_air(self):
        resp = Response()
        resp.text = u'air with ' + repr(self.context)
        return resp

    def make_it_fresh(self, response):
        response.text = u'fresh ' + response.text
        return response

    def check_temperature(self, request):
        if not 'X-Temperature' in request.headers:
            request.errors.add('header', 'X-Temperature')

tc = Service(name="TemperatureCooler", path="/fresh-air",
             klass=TemperatureCooler, factory=dummy_factory)
tc.add_view("GET", "get_fresh_air", filters=('make_it_fresh',),
            validators=('check_temperature',))


class TestService(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_service")
        self.config.scan("cornice.tests.test_pyramidhook")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_404(self):
        # a get on a resource that explicitely return a 404 should return
        # 404
        self.app.get("/service", status=404)

    def test_405(self):
        # calling a unknown verb on an existing resource should return a 405
        self.app.post("/service", status=405)

    def test_acl_support(self):
        self.app.delete('/service')

    def test_class_support(self):
        self.app.get('/fresh-air', status=400)
        resp = self.app.get('/fresh-air', headers={'X-Temperature': '50'})
        self.assertEqual(resp.body, b'fresh air with context!')


class WrapperService(Service):
    def get_view_wrapper(self, kw):
        def upper_wrapper(func):
            def upperizer(*args, **kwargs):
                result = func(*args, **kwargs)
                return result.upper()
            return upperizer
        return upper_wrapper


wrapper_service = WrapperService(name='wrapperservice', path='/wrapperservice')


@wrapper_service.get()
def return_foo(request):
    return 'foo'


class TestServiceWithWrapper(TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_pyramidhook")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_wrapped(self):
        result = self.app.get('/wrapperservice')
        self.assertEqual(result.json, 'FOO')


test_service = Service(name="jardinet", path="/jardinet", traverse="/jardinet")
test_service.add_view('GET', lambda _:_)



class TestRouteWithTraverse(TestCase):

    def test_route_construction(self):
        config = MagicMock()
        config.add_route = MagicMock()

        register_service_views(config, test_service)
        self.assertTrue(
                ('traverse', '/jardinet'),
                config.add_route.called_args,
            )

class NonpickableSchema(colander.Schema):
    # Compiled regexs are, apparently, non-pickleable
    s = colander.SchemaNode(colander.String(), validator=colander.Regex('.'))

class TestServiceWithNonpickleableSchema(TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test(self):
        service = Service(name="test", path="/", schema=NonpickableSchema())
        service.add_view('GET', lambda _:_)
        register_service_views(self.config, service)
