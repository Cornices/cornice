from cornice.tests.support import TestCase

from cornice.errors import Errors


class TestErrorsHelper(TestCase):
    def setUp(self):
        self.errors = Errors()

    def test_raises_an_exception_when_location_is_unsupported(self):
        with self.assertRaises(ValueError):
            self.errors.add('something')
