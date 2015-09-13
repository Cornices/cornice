# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.errors import Errors
from cornice.tests.support import TestCase
from cornice import schemas
from cornice.util import extract_json_data
import json

try:
    from colander import (
        deferred,
        Mapping,
        MappingSchema,
        Sequence,
        SequenceSchema,
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

    class WrongSchema(SequenceSchema):
        pass

    class DropSchema(MappingSchema):
        foo = SchemaNode(String(), type='str', missing=drop)
        bar = SchemaNode(String(), type='str')

    class StrictMappingSchema(MappingSchema):
        @staticmethod
        def schema_type():
            return Mapping(unknown='raise')

    class StrictSchema(StrictMappingSchema):
        foo = SchemaNode(String(), type='str', location="body", missing=drop)
        bar = SchemaNode(String(), type='str', location="body")

    class NestedSchema(MappingSchema):
        egg = StrictSchema(location='querystring')
        ham = StrictSchema(location='body')

    class DefaultSchema(MappingSchema):
        foo = SchemaNode(String(), type='str', location="querystring",
                         missing='foo')
        bar = SchemaNode(String(), type='str', location="querystring",
                         missing='bar')

    class DefaultValueConvertSchema(MappingSchema):
        bar = SchemaNode(Int(), type="int", missing=10)

    class QsSchema(MappingSchema):
        foo = SchemaNode(String(), type='str', location="querystring",
                         missing=drop)

    class StrictQsSchema(StrictMappingSchema):
        foo = SchemaNode(String(), type='str', location="querystring",
                         missing=drop)

    class PreserveUnkownSchema(MappingSchema):
        bar = SchemaNode(String(), type='str')

        @staticmethod
        def schema_type():
            return Mapping(unknown='preserve')

    def get_mock_request(body, get=None):
        # Construct a mock request with the given request body
        class MockRegistry(object):
            def __init__(self):
                self.cornice_deserializers = {
                    'application/json': extract_json_data
                }

        class MockRequest(object):
            def __init__(self, body, get):
                self.headers = {}
                self.matchdict = {}
                self.body = body
                self.GET = get or {}
                self.POST = {}
                self.validated = {}
                self.registry = MockRegistry()
                self.content_type = 'application/json'

        dummy_request = MockRequest(body, get)
        setattr(dummy_request, 'errors', Errors(dummy_request))
        return dummy_request

    class TestSchemas(TestCase):

        def test_colander_schema_using_drop(self):
            """
            remove fields from validated data if they deserialize to colander's
            `drop` object.
            """
            schema = schemas.CorniceSchema.from_colander(DropSchema)

            dummy_request = get_mock_request('{"bar": "required_data"}')
            schemas.use(schema, dummy_request)

            self.assertNotIn('foo', dummy_request.validated)
            self.assertIn('bar', dummy_request.validated)
            self.assertEqual(len(dummy_request.errors), 0)

        def test_colander_strict_schema(self):
            schema = schemas.CorniceSchema.from_colander(StrictSchema)

            dummy_request = get_mock_request(
                '''
                {"bar": "required_data", "foo": "optional_data",
                "other": "not_wanted_data"}
                ''')
            schemas.use(schema, dummy_request)

            errors = dummy_request.errors
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0], {'description': 'Unrecognized key',
                                         'location': 'body',
                                         'name': 'other'})
            self.assertIn('foo', dummy_request.validated)
            self.assertIn('bar', dummy_request.validated)

        def test_colander_schema_using_dotted_names(self):
            """
            Schema could be passed as string in view
            """
            schema = 'cornice.tests.schema.AccountSchema'

            dummy_request = get_mock_request(
                '{"nickname": "john", "city": "Moscow"}')
            schemas.use(schema, dummy_request)

            self.assertIn('nickname', dummy_request.validated)
            self.assertNotIn('city', dummy_request.validated)

        def test_colander_nested_schema(self):
            schema = schemas.CorniceSchema.from_colander(NestedSchema)

            dummy_request = get_mock_request('{"ham": {"bar": "POST"}}',
                                             {'egg.bar': 'GET'})
            schemas.use(schema, dummy_request)

            errors = dummy_request.errors
            self.assertEqual(len(errors), 0, errors)

            expected = {'egg': {'bar': 'GET'},
                        'ham': {'bar': 'POST'},
                        }

            self.assertEqual(expected, dummy_request.validated)

        def test_colander_schema_using_defaults(self):
            """
            Schema could contains default values
            """
            schema = schemas.CorniceSchema.from_colander(DefaultSchema)

            dummy_request = get_mock_request('', {'bar': 'test'})
            schemas.use(schema, dummy_request)

            expected = {'foo': 'foo', 'bar': 'test'}
            self.assertEqual(expected, dummy_request.validated)

            dummy_request = get_mock_request('', {'bar': 'test',
                                                  'foo': 'test'})
            schemas.use(schema, dummy_request)

            expected = {'foo': 'test', 'bar': 'test'}
            self.assertEqual(expected, dummy_request.validated)

        def test_colander_schema_defaults_convert(self):
            """
            Test schema behaviour regarding conversion missing(default) values
            """
            # apply default value to field if the input for them is
            # missing
            schema = schemas.CorniceSchema.from_colander(
                DefaultValueConvertSchema)

            dummy_request = get_mock_request('')
            schemas.use(schema, dummy_request)
            self.assertEqual({'bar': 10}, dummy_request.validated)

            dummy_request = get_mock_request('{"foo": 5}')
            schemas.use(schema, dummy_request)
            self.assertEqual({'bar': 5}, dummy_request.validated)

        def test_only_mapping_is_accepted(self):
            schema = schemas.CorniceSchema.from_colander(WrongSchema)
            dummy_request = get_mock_request('', {'foo': 'test',
                                                  'bar': 'test'})
            self.assertRaises(schemas.InvalidSchemaError,
                              schemas.use, schema, dummy_request)

            # We shouldn't accept a MappingSchema if the `typ` has
            #  been set to something else:
            schema = CorniceSchema.from_colander(
                MappingSchema(
                    Sequence,
                    SchemaNode(String(), name='foo'),
                    SchemaNode(String(), name='bar'),
                    SchemaNode(String(), name='baz')
                )
            )
            self.assertRaises(InvalidSchemaError,
                              validate_colander_schema, schema, dummy_request)

        def test_extra_params_qs(self):
            schema = schemas.CorniceSchema.from_colander(QsSchema)
            dummy_request = get_mock_request('', {'foo': 'test',
                                                  'bar': 'test'})
            schemas.use(schema, dummy_request)

            errors = dummy_request.errors
            self.assertEqual(len(errors), 0)

            expected = {'foo': 'test'}
            self.assertEqual(expected, dummy_request.validated)

        def test_extra_params_qs_strict(self):
            schema = schemas.CorniceSchema.from_colander(StrictQsSchema)
            dummy_request = get_mock_request('', {'foo': 'test',
                                                  'bar': 'test'})
            schemas.use(schema, dummy_request)

            errors = dummy_request.errors
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0], {'description': 'Unrecognized key',
                                         'location': 'querystring',
                                         'name': 'bar'})

            expected = {'foo': 'test'}
            self.assertEqual(expected, dummy_request.validated)

        def test_validate_colander_schema_can_preserve_unknown_fields(self):
            schema = schemas.CorniceSchema.from_colander(PreserveUnkownSchema)

            data = json.dumps({"bar": "required_data", "optional": "true"})
            dummy_request = get_mock_request(data)
            schemas.use(schema, dummy_request)

            self.assertDictEqual(dummy_request.validated, {
                "bar": "required_data",
                "optional": "true"
            })
            self.assertEqual(len(dummy_request.errors), 0)
