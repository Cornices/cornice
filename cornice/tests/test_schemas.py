# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.errors import Errors
from cornice.tests.support import TestCase
from cornice.schemas import (
    CorniceSchema, validate_colander_schema, StrictMappingSchema
)
from cornice.util import extract_json_data


try:
    import colander
except ImportError:
    pass
else:
    # colander is properly imported so we can proceed...

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

        def test_imperative_colander_schema(self):
            imperative_schema = CorniceSchema()
            imperative_schema['body'].add(
                colander.SchemaNode(
                    colander.String(),
                    name='foo',
                    default=colander.drop,
                )
            )
            imperative_schema['body'].add(
                colander.SchemaNode(
                    colander.String(),
                    name='bar'
                )
            )
            imperative_schema['querystring'].add(
                colander.SchemaNode(
                    colander.String(),
                    name='baz',
                    default=colander.drop
                )
            )

            dummy_request = get_mock_request('{"bar": "some data"}')
            validate_colander_schema(imperative_schema, dummy_request)

            self.assertEqual(len(dummy_request.errors), 0)
            self.assertEqual(dummy_request.validated['body'],
                             {'bar': 'some data'})

        def test_colander_schema_using_drop(self):
            """ remove fields from validated data if they deserialize to
            `colander.drop`.
            """
            from colander import SchemaNode, String

            class DropSchema(StrictMappingSchema):
                foo = SchemaNode(String(), missing=colander.drop)
                bar = SchemaNode(String())

            schema = CorniceSchema()
            schema['body'] = DropSchema()

            dummy_request = get_mock_request('{"bar": "required_data"}')
            validate_colander_schema(schema, dummy_request)

            self.assertNotIn('foo', dummy_request.validated['body'])
            self.assertIn('bar', dummy_request.validated['body'])
            self.assertEqual(len(dummy_request.errors), 0)

        def test_colander_strict_schema(self):
            from colander import SchemaNode, String

            class StrictSchema(StrictMappingSchema):
                foo = SchemaNode(String(), missing=colander.drop)
                bar = SchemaNode(String())

            schema = CorniceSchema()
            schema['body'] = StrictSchema()

            dummy_request = get_mock_request(
                '''{"bar": "required_data", "foo": "optional_data",
                "other": "not_wanted_data"}'''
            )
            validate_colander_schema(schema, dummy_request)

            errors = dummy_request.errors
            self.assertEqual(len(errors), 1)
            self.assertNotIn('body', dummy_request.validated)
