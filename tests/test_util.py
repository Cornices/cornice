# -*- encoding: utf-8 -*-
import json

import mock

from pyramid import testing
from pyramid.interfaces import IRendererFactory
from webtest import TestApp

from cornice import util, Service
from cornice.util import default_bytes_adapter
from .support import TestCase, CatchErrors, skip_if_no_simplejson, skip_if_simplejson


class TestDeprecatedUtils(TestCase):

    def test_extract_json_data_is_deprecated(self):
        with mock.patch('cornice.util.warnings') as mocked:
            util.extract_json_data(mock.MagicMock())
            self.assertTrue(mocked.warn.called)

    def test_extract_form_urlencoded_data_is_deprecated(self):
        with mock.patch('cornice.util.warnings') as mocked:
            util.extract_form_urlencoded_data(mock.MagicMock())
            self.assertTrue(mocked.warn.called)


class CurrentServiceTest(TestCase):

    def test_current_service_returns_the_service_for_existing_patterns(self):
        request = mock.MagicMock()
        request.matched_route.pattern = '/buckets'
        request.registry.cornice_services = {'/buckets': mock.sentinel.service}

        self.assertEqual(util.current_service(request), mock.sentinel.service)

    def test_current_service_returns_none_for_unexisting_patterns(self):
        request = mock.MagicMock()
        request.matched_route.pattern = '/unexisting'
        request.registry.cornice_services = {}

        self.assertEqual(util.current_service(request), None)


@skip_if_no_simplejson
class JSONRendererTest(TestCase):
    def setUp(self):
        self.config = testing.setUp()
        json_renderer_factory = self._get_json_renderer_factory()
        json_renderer_factory.serializer = json.dumps
        json_renderer_factory.kw = {}

    def tearDown(self):
        testing.tearDown()

    def _get_json_renderer_factory(self):
        return self.config.registry.queryUtility(
            IRendererFactory, name='json'
        )

    def _get_app(self):
        self.config.include('cornice')

        test_service = Service(name='testing', path='/test')
        test_service.add_view('GET', lambda r: {"result": 1})
        self.config.add_cornice_service(test_service)

        return TestApp(CatchErrors(self.config.make_wsgi_app()))

    @skip_if_no_simplejson
    def test_default_renderer_gets_patched(self):
        import simplejson

        app = self._get_app()
        response = app.get('/test')
        self.assertEqual(response.text, '{"result": 1}')
        json_renderer_factory = self._get_json_renderer_factory()

        # serializer should have been patched
        self.assertNotEqual(json_renderer_factory.serializer, json.dumps)
        self.assertEqual(json_renderer_factory.serializer, simplejson.dumps)
        self.assertIn("use_decimal", json_renderer_factory.kw)
        self.assertTrue(json_renderer_factory.kw["use_decimal"])

    @skip_if_simplejson
    def test_configured_renderer_does_not_get_patched(self):
        app = self._get_app()
        response = app.get('/test')
        self.assertEqual(response.text, '{"result": 1}')
        json_renderer_factory = self._get_json_renderer_factory()

        # serializer should not have been patched
        self.assertEqual(json_renderer_factory.serializer, json.dumps)
        self.assertNotIn("use_decimal", json_renderer_factory.kw)

    def test_default_bytes_adapter(self):
        string = "test_string"
        bytestring = b"test_string"
        self.assertEqual(
            default_bytes_adapter(string),
            default_bytes_adapter(bytestring)
        )
        unsupported = object()
        self.assertEqual(unsupported, default_bytes_adapter(unsupported))
