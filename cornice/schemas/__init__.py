# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

import importlib

from pyramid import path

from cornice.schemas import generic


def use(schema, request):
    schema = _python_path_resolver.maybe_resolve(schema)
    schema = _apply_compat_if_required(schema)

    for bind in _adapters:
        try:
            adapter = bind(schema)
        except generic.UnsuitableSchemaCtrl:
            continue

        break
    else:
        raise generic.InvalidSchemaError(
            'No schema adapter found for: {!r}'.format(schema))

    payload, errors = adapter(request)

    for err in errors:
        request.errors.add(err.location, err.field, err.desc)
    request.validated.update(payload)


def _apply_compat_if_required(schema):
    if isinstance(schema, CorniceSchema):
        pass
    elif isinstance(schema, generic.GenericAdapter):
        pass
    else:
        schema = CorniceSchema.from_colander(schema)
    return schema


class _PredefinedAdapter(generic.GenericAdapter):
    def __init__(self, schema):
        super(_PredefinedAdapter, self).__init__(schema)
        if not isinstance(self.schema, generic.GenericAdapter):
            raise generic.UnsuitableSchemaCtrl

    def __call__(self, request):
        return self.schema(request)


_python_path_resolver = path.DottedNameResolver(__name__)


_adapters = [
    _PredefinedAdapter]
for name in ('.compat', '.colander', '.generic'):
    try:
        # TODO: rewrite using stevedore
        mod = importlib.import_module(name, __name__)
    except ImportError:
        continue

    payload = mod.init()
    if isinstance(payload, generic.AdapterDescriptor):
        _adapters.append(payload.adapter)
    else:
        try:
            _adapters.extend(payload)
        except TypeError:
            _adapters.append(payload)

adapters = {}
for idx, a in enumerate(_adapters):
    if not isinstance(a, generic.AdapterDescriptor):
        continue
    adapters[a.name] = a.adapter
    _adapters[idx] = a.adapter


InvalidSchemaError = generic.InvalidSchemaError
CorniceSchema = generic.CorniceSchema
