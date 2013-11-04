# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.errors import Errors
from cornice.tests.support import TestCase
from cornice.schemas import CorniceSchema, validate_colander_schema
from cornice.util import extract_json_data

try:
    from colander import (
        deferred,
        Mapping,
        MappingSchema,
        SchemaNode,
        String,
        Int,
        OneOf,
        drop
    )
    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:

    @deferred
    def deferred_validator(node, kw):
        """
        This is a deferred validator that changes its own behavior based on
        request object being passed, thus allowing for validation of fields
        depending on other field values.

        This example shows how to validate a body field based on a dummy
        header value, using OneOf validator with different choices
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

    class DropSchema(MappingSchema):
        foo = SchemaNode(String(), type='str', missing=drop)
        bar = SchemaNode(String(), type='str')

    imperative_schema = SchemaNode(Mapping())
    imperative_schema.add(SchemaNode(String(), name='foo', type='str'))
    imperative_schema.add(SchemaNode(String(), name='bar', type='str',
                          location="body"))
    imperative_schema.add(SchemaNode(String(), name='baz', type='str',
                          location="querystring"))

    class TestingSchemaWithHeader(MappingSchema):
        foo = SchemaNode(String(), type='str')
        bar = SchemaNode(String(), type='str', location="body")
        baz = SchemaNode(String(), type='str', location="querystring")
        qux = SchemaNode(String(), type='str', location="header")

    class TestSchemas(TestCase):

        def test_colander_integration(self):
            # not specifying body should act the same way as specifying it
            schema = CorniceSchema.from_colander(TestingSchema)
            body_fields = schema.get_attributes(location="body")
            qs_fields = schema.get_attributes(location="querystring")

            self.assertEqual(len(body_fields), 2)
            self.assertEqual(len(qs_fields), 1)

        def test_colander_integration_with_header(self):
            schema = CorniceSchema.from_colander(TestingSchemaWithHeader)
            all_fields = schema.get_attributes()
            body_fields = schema.get_attributes(location="body")
            qs_fields = schema.get_attributes(location="querystring")
            header_fields = schema.get_attributes(location="header")

            self.assertEqual(len(all_fields), 4)
            self.assertEqual(len(body_fields), 2)
            self.assertEqual(len(qs_fields), 1)
            self.assertEqual(len(header_fields), 1)

        def test_colander_inheritance(self):
            """
            support inheritance of colander.Schema
            introduced in colander 0.9.9

            attributes of base-classes with the same name than
            subclass-attributes get overwritten.
            """
            base_schema = CorniceSchema.from_colander(TestingSchema)
            inherited_schema = CorniceSchema.from_colander(InheritedSchema)

            self.assertEqual(len(base_schema.get_attributes()),
                              len(inherited_schema.get_attributes()))

            foo_filter = lambda x: x.name == "foo"
            base_foo = list(filter(foo_filter,
                                   base_schema.get_attributes()))[0]
            inherited_foo = list(filter(foo_filter,
                                        inherited_schema.get_attributes()))[0]
            self.assertTrue(base_foo.required)
            self.assertFalse(inherited_foo.required)

        def test_colander_bound_schemas(self):
            dummy_request = {'x-foo': 'version_a'}
            a_schema = CorniceSchema.from_colander(ToBoundSchema)
            field = a_schema.get_attributes(request=dummy_request)[3]
            self.assertEqual(field.validator.choices, ['a', 'b'])

            other_dummy_request = {'x-foo': 'bazinga!'}
            b_schema = CorniceSchema.from_colander(ToBoundSchema)
            field = b_schema.get_attributes(request=other_dummy_request)[3]
            self.assertEqual(field.validator.choices, ['c', 'd'])

        def test_colander_bound_schema_rebinds_to_new_request(self):
            dummy_request = {'x-foo': 'version_a'}
            the_schema = CorniceSchema.from_colander(ToBoundSchema)
            field = the_schema.get_attributes(request=dummy_request)[3]
            self.assertEqual(field.validator.choices, ['a', 'b'])

            other_dummy_request = {'x-foo': 'bazinga!'}
            field = the_schema.get_attributes(request=other_dummy_request)[3]
            self.assertEqual(field.validator.choices, ['c', 'd'])

        def test_imperative_colander_schema(self):
            # not specifying body should act the same way as specifying it
            schema = CorniceSchema.from_colander(imperative_schema)
            body_fields = schema.get_attributes(location="body")
            qs_fields = schema.get_attributes(location="querystring")

            self.assertEqual(len(body_fields), 2)
            self.assertEqual(len(qs_fields), 1)

        def test_colander_schema_using_drop(self):
            """
            remove fields from validated data if they deserialize to colander's
            `drop` object.
            """
            schema = CorniceSchema.from_colander(DropSchema)

            class MockRequest(object):
                def __init__(self, body):
                    self.headers = {}
                    self.matchdict = {}
                    self.body = body
                    self.GET = {}
                    self.POST = {}
                    self.validated = {}
                    self.registry = {
                        'cornice_deserializers': {
                            'application/json': extract_json_data
                        }
                    }

            dummy_request = MockRequest('{"bar": "required_data"}')
            setattr(dummy_request, 'errors', Errors(dummy_request))
            validate_colander_schema(schema, dummy_request)

            self.assertNotIn('foo', dummy_request.validated)
