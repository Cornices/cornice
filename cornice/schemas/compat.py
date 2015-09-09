# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, absolute_import

from cornice.schemas import generic
from cornice.schemas import colander as cornice_colander


class BackwardCompatibilityAdapter(cornice_colander.ColanderAdapter):
    def __init__(self, schema):
        if isinstance(schema, generic.CorniceSchema):
            bind_request = schema.bind_request
            schema = schema.schema
        else:
            raise generic.UnsuitableSchemaCtrl

        super(BackwardCompatibilityAdapter, self).__init__(
            schema, bind_request=bind_request)


def init():
    return BackwardCompatibilityAdapter
