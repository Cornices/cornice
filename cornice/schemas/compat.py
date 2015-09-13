# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, absolute_import

import colander
from pyramid import path

from cornice.schemas import generic
from cornice.schemas import colander as cornice_colander


class ColanderSchema(colander.MappingSchema):
    pass


class BackwardCompatibilityAdapter(cornice_colander.ColanderAdapter):
    def __init__(self, schema):
        if isinstance(schema, generic.CorniceSchema):
            bind_request = schema.bind_request
            schema = _python_path_resolver.maybe_resolve(schema.schema)
        elif isinstance(schema, ColanderSchema):
            bind_request = True
        else:
            raise generic.UnsuitableSchemaCtrl

        super(BackwardCompatibilityAdapter, self).__init__(
            schema, bind_request=bind_request, flattening=True)

    def _flattening_data(self, schema, data):
        if not self.need_flattening:
            return data
        try:
            flatted = schema.unflatten(data)
            flatted.update(data)
        except KeyError:
            flatted = data

        return flatted


_python_path_resolver = path.DottedNameResolver(__name__)


def init():
    return BackwardCompatibilityAdapter
