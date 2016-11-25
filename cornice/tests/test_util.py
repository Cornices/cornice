# -*- encoding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from cornice import util
from cornice.tests.support import TestCase

class StubRequestWithBody(object):
    def __init__(self, body):
        self.body = body

class TestExtractedJSONValueTypes(TestCase):
    """Make sure that all JSON string values extracted from the request
      are unicode when running using PY2.
    """

    def test_extracted_json_values(self):
        """Extracted JSON values are unicode in PY2."""

        if not util.PY2:
            return

        valid_json_str = '{"foo": "bar", "currency": "\xe2\x82\xac"}'
        request = StubRequestWithBody(valid_json_str)
        data = util.extract_json_data(request)
        self.assertEqual(type(data['foo']), unicode)
        self.assertEqual(type(data['currency']), unicode)
        self.assertEqual(data['currency'], u'€')
