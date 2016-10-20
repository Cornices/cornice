# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import json

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
        def test_body_contains_fields(self):
            body = {'bar': '1',
                    'baz': 2,
                    'foo': 'yeah'}
            headers = {'x-foo': 'version_a'}

            dummy_request = get_mock_request(body, headers=headers)
            validator(dummy_request, schema=RequestSchema)
