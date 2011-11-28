
import unittest
import json
from StringIO import StringIO

from pyramid import testing
from pyramid.exceptions import HTTPNotFound

from cornice import Service


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
        app = self.config.make_wsgi_app()

        # An unknown URL raises HTTPNotFound
        def start_response(status, headers, exc_info=None):
            pass
        req = make_request(PATH_INFO="/unknown")
        self.assertRaises(HTTPNotFound, app, req.environ, start_response)

        # A request to the service calls the apppriate view function.
        req = make_request(PATH_INFO="/service1")
        result = json.loads("".join(app(req.environ, start_response)))
        self.assertEquals(result["test"], "succeeded")

        req = make_request(PATH_INFO="/service1", REQUEST_METHOD="POST")
        req.environ["wsgi.input"] = StringIO("BODY")
        result = json.loads("".join(app(req.environ, start_response)))
        self.assertEquals(result["body"], "BODY")

    def test_loading_into_multiple_configurators(self):
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
