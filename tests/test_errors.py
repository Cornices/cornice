from unittest import mock

from cornice.errors import Errors
from cornice.service import Service
from pyramid import testing
from pyramid.i18n import TranslationString
from webtest import TestApp

from .support import CatchErrors, TestCase


class TestErrorsHelper(TestCase):
    def setUp(self):
        self.errors = Errors()

    def test_add_to_supported_location(self):
        self.errors.add("")
        self.errors.add("body", description="!")
        self.errors.add("querystring", name="field")
        self.errors.add("url")
        self.errors.add("header")
        self.errors.add("path")
        self.errors.add("cookies")
        self.errors.add("method")
        self.assertEqual(len(self.errors), 8)

    def test_raises_an_exception_when_location_is_unsupported(self):
        with self.assertRaises(ValueError):
            self.errors.add("something")


service1 = Service(name="service1", path="/error-service1")


@service1.get()
def get1(request):
    return request.errors.add("body", "field", "Description")


service2 = Service(name="service2", path="/error-service2")


@service2.get()
def get2(request):
    return request.errors.add("body", "field", TranslationString("Description"))


class TestErrorsTranslation(TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.config.add_settings({"available_languages": "en fr"})
        self.config.include("cornice")
        self.config.scan("tests.test_errors")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    @property
    def _translate(self):
        return "pyramid.i18n.Localizer.translate"

    def test_error_description_translation_not_called_when_string(self):
        with mock.patch(self._translate) as mocked:
            self.app.get("/error-service1", status=400).json
            self.assertFalse(mocked.called)

    def test_error_description_translation_called_when_translationstring(self):
        with mock.patch(self._translate, return_value="Translated") as mocked:
            self.app.get("/error-service2", status=400).json
            self.assertTrue(mocked.called)
