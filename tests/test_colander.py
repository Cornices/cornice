# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import json
import warnings

from cornice.errors import Errors
from cornice.validators._colander import validator

from .support import TestCase

try:
    from colander import (
        MappingSchema,
        SchemaNode,
        String,
        Int
    )
    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:

    class BodySchema(MappingSchema):
        foo = SchemaNode(String())
        bar = SchemaNode(String())
        baz = SchemaNode(Int())

    class RequestSchema(MappingSchema):
        body = BodySchema()

    def get_mock_request(body, get=None, headers=None):
        if get is None:
            get = {}

        if headers is None:
            headers = {}

        body = json.dumps(body)
        json_body = json.loads(body)

        # Construct a mock request with the given request body
        class MockTranslator(object):
            def translate(self, something):
                return something

        class MockRequest(object):
            def __init__(self, body, json_body, get, method='GET'):
                self.headers = {}
                self.method = method
                self.url = 'http://example.com/path?ok=1'
                self.path = '/path'
                self.matchdict = {}
                self.body = body
                self.json_body = json_body
                self.GET = get or {}
                self.POST = {}
                self.validated = {}
                self.cookies = {}
                self.registry = object()
                self.content_type = 'application/json'
                self.localizer = MockTranslator()

        dummy_request = MockRequest(body, json_body, get)
        setattr(dummy_request, 'errors', Errors(dummy_request))
        return dummy_request

    class TestSchemas(TestCase):
        def test_validation(self):
            body = {'bar': '1',
                    'baz': '2',
                    'foo': 'yeah'}
            request = get_mock_request(body)
            validator(request, schema=RequestSchema())
            self.assertEqual(len(request.errors), 0)
            self.assertEqual(request.validated['body'], {
                'foo': 'yeah',
                'bar': '1',
                'baz': 2,
                })

        def test_validation_failure(self):
            body = {'bar': '1',
                    'baz': 'two',
                    'foo': 'yeah'}
            request = get_mock_request(body)
            validator(request, schema=RequestSchema())
            self.assertEqual(len(request.errors), 1)
            self.assertEqual(request.validated, {})
            error = request.errors[0]
            self.assertEqual(error['location'], 'body')
            self.assertEqual(error['name'], 'baz')

        def test_schema_class_deprecated(self):
            body = {}
            request = get_mock_request(body)
            with warnings.catch_warnings(record=True) as w:
                warnings.resetwarnings()
                validator(request, schema=RequestSchema)
            self.assertEqual(len(w), 1)
            self.assertIs(w[0].category, DeprecationWarning)
