from pyramid import testing
from webtest import TestApp
import mock

from cornice.tests.support import TestCase, CatchErrors


class TestCorniceSetup(TestCase):

    def setUp(self):
        self._apply_called = False

        def _apply(request, response):
            self._apply_called = True
            return response

        self._apply = _apply
        self.config = testing.setUp()

    def _get_app(self):
        self.config.include('cornice')
        self.config.scan("cornice.tests.test_init")
        return TestApp(CatchErrors(self.config.make_wsgi_app()))

    def test_exception_handling_is_included_by_default(self):
        app = self._get_app()
        with mock.patch('cornice.pyramidhook.apply_filters', self._apply):
            app.post('/foo', status=404)
            self.assertTrue(self._apply_called)

    def test_exception_handling_can_be_disabled(self):
        self.config.add_settings(handle_exceptions=False)
        app = self._get_app()
        with mock.patch('cornice.pyramidhook.apply_filters', self._apply):
            app.post('/foo', status=404)
            self.assertFalse(self._apply_called)
