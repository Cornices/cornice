# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid import testing
from pyramid.interfaces import IRendererFactory
from webtest import TestApp
import mock

from cornice import Service
from cornice.pyramidhook import apply_filters
from .support import TestCase, CatchErrors, skip_if_no_simplejson, skip_if_simplejson


class TestCorniceSetup(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _get_app(self):
        self.config.include('cornice')

        failing_service = Service(name='failing', path='/fail')
        failing_service.add_view('GET', lambda r: 1 / 0)
        self.config.add_cornice_service(failing_service)

        return TestApp(CatchErrors(self.config.make_wsgi_app()))

    @skip_if_no_simplejson
    def test_default_renderer_is_simplejson(self):
        import simplejson

        self._get_app()
        self.assertEqual(Service.renderer, 'simplejson')
        renderer_factory = self.config.registry.queryUtility(
            IRendererFactory, name='simplejson'
        )
        renderer = renderer_factory(None)
        self.assertEqual(
            renderer._serializer_patch,
            simplejson.dumps
        )

    @skip_if_simplejson
    def test_default_renderer_without_simplejson(self):
        self._get_app()
        self.assertEqual(Service.renderer, 'cornicejson')
        renderer_factory = self.config.registry.queryUtility(
            IRendererFactory, name='cornicejson'
        )
        renderer = renderer_factory(None)
        self.assertIsNone(renderer._serializer_patch)

    def test_exception_handling_is_included_by_default(self):
        app = self._get_app()
        with mock.patch('cornice.pyramidhook.apply_filters',
                        wraps=apply_filters) as mocked:
            app.post('/foo', status=404)
            self.assertTrue(mocked.called)

    def test_exception_handling_can_be_disabled(self):
        self.config.add_settings(handle_exceptions=False)
        app = self._get_app()
        with mock.patch('cornice.pyramidhook.apply_filters',
                        wraps=apply_filters) as mocked:
            app.post('/foo', status=404)
            self.assertFalse(mocked.called)

    def test_exception_handling_raises_uncaught_errors(self):
        app = self._get_app()
        self.assertRaises(ZeroDivisionError, app.get, '/fail')
