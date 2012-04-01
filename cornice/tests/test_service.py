# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import warnings
import unittest

from pyramid import testing
from pyramid.httpexceptions import HTTPNotFound
from webtest import TestApp

from cornice import Service
from cornice.tests import CatchErrors


service = Service(name="service", path="/service")


@service.get()
def return_404(request):
    raise HTTPNotFound()


class TestService(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_service")
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

    def test_warning(self):

        service = Service(name='blah', path='/blah')
        msg = "'validator' is deprecated, please use 'validators'"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # this should raise a warning, but work
            @service.post(validator=())
            def bah(req):
                pass

            self.assertEqual(msg, str(w[-1].message))


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


class TestServiceWithWrapper(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_service")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_wrapped(self):
        result = self.app.get('/wrapperservice')
        self.assertEqual(result.json, 'FOO')
