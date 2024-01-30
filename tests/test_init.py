# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from unittest import mock

from cornice import Service
from cornice.pyramidhook import apply_filters
from pyramid import testing
from webtest import TestApp

from .support import CatchErrors, TestCase


class TestCorniceSetup(TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def _get_app(self):
        self.config.include("cornice")

        failing_service = Service(name="failing", path="/fail")
        failing_service.add_view("GET", lambda r: 1 / 0)
        self.config.add_cornice_service(failing_service)

        return TestApp(CatchErrors(self.config.make_wsgi_app()))

    def test_exception_handling_is_included_by_default(self):
        app = self._get_app()
        with mock.patch("cornice.pyramidhook.apply_filters", wraps=apply_filters) as mocked:
            app.post("/foo", status=404)
            self.assertTrue(mocked.called)

    def test_exception_handling_can_be_disabled(self):
        self.config.add_settings(handle_exceptions=False)
        app = self._get_app()
        with mock.patch("cornice.pyramidhook.apply_filters", wraps=apply_filters) as mocked:
            app.post("/foo", status=404)
            self.assertFalse(mocked.called)

    def test_exception_handling_raises_uncaught_errors(self):
        app = self._get_app()
        self.assertRaises(ZeroDivisionError, app.get, "/fail")
