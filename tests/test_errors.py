from cornice.errors import Errors

from .support import TestCase


class TestErrorsHelper(TestCase):
    def setUp(self):
        self.errors = Errors()

    def test_add_to_supported_location(self):
        self.errors.add('')
        self.errors.add('body', description='!')
        self.errors.add('querystring', name='field')
        self.errors.add('url')
        self.errors.add('header')
        self.errors.add('path')
        self.errors.add('cookies')
        self.errors.add('method')
        self.assertEqual(len(self.errors), 8)

    def test_raises_an_exception_when_location_is_unsupported(self):
        with self.assertRaises(ValueError):
            self.errors.add('something')
