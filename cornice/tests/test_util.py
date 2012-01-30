# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import unittest2
from cornice.util import rst2html


class TestUtil(unittest2.TestCase):

    def test_rendering(self):
        text = '**simple render**'
        res = rst2html(text)
        self.assertEquals(res, '<p><strong>simple render</strong></p>')
        self.assertEquals(rst2html(''), '')
