# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.tests.support import TestCase
from cornice.schemas import CorniceSchema

try:
    from colander import (
        deferred,
        MappingSchema,
        SchemaNode,
        String,
        Int,
        OneOf
    )
    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:

    @deferred
    def deferred_validator(node, kw):
        """ This is a deferred validator that changes its own behavior based on 
            request object being passed, thus allowing for validation of fields 
            depending on other field values.

            This example shows how to validate a body field based on a 
            dummy header value, using OneOf validator with different choices
        """
        request = kw['request']
        if request['x-foo'] == 'version_a':
            return OneOf(['a', 'b'])
        else:
            return OneOf(['c', 'd'])


    class TestingSchema(MappingSchema):
        foo = SchemaNode(String(), type='str')
        bar = SchemaNode(String(), type='str', location="body")
        baz = SchemaNode(String(), type='str', location="querystring")

    class InheritedSchema(TestingSchema):
        foo = SchemaNode(Int(), missing=1)

    class ToBoundSchema(TestingSchema):
        foo = SchemaNode(Int(), missing=1)
        bazinga = SchemaNode(String(), type='str', location="body",
                             validator=deferred_validator)

    class TestSchemas(TestCase):

        def test_colander_integration(self):
            # not specifying body should act the same way as specifying it
            schema = CorniceSchema.from_colander(TestingSchema)
            body_fields = schema.get_attributes(location="body")
            qs_fields = schema.get_attributes(location="querystring")

            self.assertEquals(len(body_fields), 2)
            self.assertEquals(len(qs_fields), 1)

        def test_colander_inheritance(self):
            """
            support inheritance of colander.Schema
            introduced in colander 0.9.9

            attributes of base-classes with the same name than
            subclass-attributes get overwritten.
            """
            base_schema = CorniceSchema.from_colander(TestingSchema)
            inherited_schema = CorniceSchema.from_colander(InheritedSchema)

            self.assertEquals(len(base_schema.get_attributes()),
                              len(inherited_schema.get_attributes()))

            foo_filter = lambda x: x.name == "foo"
            base_foo = list(filter(foo_filter, base_schema.get_attributes()))[0]
            inherited_foo = list(filter(foo_filter,
                                        inherited_schema.get_attributes()))[0]
            self.assertTrue(base_foo.required)
            self.assertFalse(inherited_foo.required)

        def test_colander_bound_schemas(self):
            dummy_request = {'x-foo': 'version_a'}
            a_schema = CorniceSchema.from_colander(ToBoundSchema)
            field = a_schema.get_attributes(request=dummy_request)[3]
            self.assertEqual(field.validator.choices, ['a','b'])

            other_dummy_request = {'x-foo': 'bazinga!'}
            b_schema = CorniceSchema.from_colander(ToBoundSchema)
            field = b_schema.get_attributes(request=other_dummy_request)[3]
            self.assertEqual(field.validator.choices, ['c','d'])
                       