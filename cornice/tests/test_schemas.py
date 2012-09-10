# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.tests.support import TestCase
from cornice.schemas import CorniceSchema

try:
    from colander import (
        MappingSchema,
        SchemaNode,
        String,
    )
    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:

    class TestingSchema(MappingSchema):
        foo = SchemaNode(String(), type='str')
        bar = SchemaNode(String(), type='str', location="body")
        baz = SchemaNode(String(), type='str', location="querystring")

    class TestSchemas(TestCase):

        def test_colander_integration(self):
            # not specifying body should act the same way as specifying it
            schema = CorniceSchema.from_colander(TestingSchema)
            body_fields = schema.get_attributes(location="body")
            qs_fields = schema.get_attributes(location="querystring")

            self.assertEquals(len(body_fields), 2)
            self.assertEquals(len(qs_fields), 1)
