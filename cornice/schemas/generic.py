# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid import path
from cornice import util


class InvalidSchemaError(Exception):
    pass


class GenericAdapter(object):
    def __init__(self, request, schema):
        self.request = request
        self.schema = schema

    def __call__(self):
        payload = util.extract_request_body(self.request)
        return self.schema(payload), tuple()


class SchemaWrapper(object):
    _python_path_resolver = path.DottedNameResolver(__name__)

    def __init__(self, schema, adapter_factory=GenericAdapter):
        self.schema = schema
        self.adapter_factory = adapter_factory

    def __call__(self, request):
        self.schema = self._python_path_resolver.maybe_resolve(self.schema)

        adapter = self.adapter_factory(request, self.schema)
        validated, errors = adapter

        request.errors.extend(errors)
        request.validated.update(validated)
