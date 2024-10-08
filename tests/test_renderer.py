from unittest import mock

from pyramid.interfaces import IJSONAdapter
from pyramid.renderers import JSON
from zope.interface import providedBy

from cornice import CorniceRenderer
from cornice.renderer import JSONError, bytes_adapter

from .support import TestCase


class TestBytesAdapter(TestCase):
    def test_with_bytes_object(self):
        self.assertEqual(bytes_adapter(b"hello", None), "hello")

    def test_with_string_object(self):
        self.assertEqual(bytes_adapter("hello", None), "hello")

    def test_with_incompatible_object(self):
        incompatible = object()
        self.assertEqual(bytes_adapter(incompatible, None), incompatible)


class TestRenderer(TestCase):
    def test_renderer_is_pyramid_renderer_subclass(self):
        self.assertIsInstance(CorniceRenderer(), JSON)

    def test_renderer_has_bytes_adapter_by_default(self):
        renderer = CorniceRenderer()
        self.assertEqual(
            renderer.components.adapters.lookup((providedBy(bytes()),), IJSONAdapter),
            bytes_adapter,
        )

    def test_renderer_calls_render_method(self):
        renderer = CorniceRenderer()
        self.assertEqual(renderer(info=None), renderer.render)

    def test_renderer_render_errors(self):
        renderer = CorniceRenderer()
        request = mock.MagicMock()

        class FakeErrors(object):
            status = 418

            def __json__(self, request):
                return ["error_1", "error_2"]

        request.errors = FakeErrors()

        result = renderer.render_errors(request)
        self.assertIsInstance(result, JSONError)
        self.assertEqual(result.status_int, 418)
        self.assertEqual(result.json_body, {"status": "error", "errors": ["error_1", "error_2"]})
