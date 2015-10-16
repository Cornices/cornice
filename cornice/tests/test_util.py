import unittest

from cornice.util import get_class_that_defined_method


class Mau(object):
    def bau(self):
        pass


class TestUtil(unittest.TestCase):

    def test_get_class(self):
        self.assertEqual(get_class_that_defined_method(Mau.bau).__name__,
                         Mau.__name__)
        # instance
        self.assertEqual(get_class_that_defined_method(Mau().bau).__name__,
                         Mau.__name__)
