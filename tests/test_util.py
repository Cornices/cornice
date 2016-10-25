import mock
import unittest

from cornice import util


class TestDeprecatedUtils(unittest.TestCase):

    def test_extract_json_data_is_deprecated(self):
        with mock.patch('cornice.util.warnings') as mocked:
            util.extract_json_data(mock.MagicMock())
            self.assertTrue(mocked.warn.called)

    def test_extract_form_urlencoded_data_is_deprecated(self):
        with mock.patch('cornice.util.warnings') as mocked:
            util.extract_form_urlencoded_data(mock.MagicMock())
            self.assertTrue(mocked.warn.called)
