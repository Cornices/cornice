# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

from pyramid import path
from cornice import util


class InvalidSchemaError(Exception):
    pass


class UnsuitableSchemaCtrl(Exception):
    pass


class GenericAdapter(object):
    _python_path_resolver = path.DottedNameResolver(__name__)

    def __init__(self, schema):
        self.schema = self._python_path_resolver.maybe_resolve(schema)

    def __call__(self, request):
        payload = util.extract_request_body(request)
        return self.schema(payload), tuple()


def init():
    return GenericAdapter
