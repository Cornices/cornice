# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

from pyramid import path

from cornice.schemas import generic


def use(schema, request):
    schema = _python_path_resolver.maybe_resolve(schema)

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

    request.errors.extend(errors)
    request.validated.update(payload)


class _PredefinedAdapter(generic.GenericAdapter):
    def __init__(self, schema):
        super(_PredefinedAdapter, self).__init__(schema)
        if not isinstance(self.schema, generic.GenericAdapter):
            raise generic.UnsuitableSchemaCtrl

    def __call__(self, request):
        return self.schema(request)


_python_path_resolver = path.DottedNameResolver(__name__)


# TODO: rewrite using stevedore
_adapters = [
    _PredefinedAdapter]
for name in (
        'cornice.schemas.generic',
        'cornice.schemas.colander'):
    try:
        mod = __import__(name)
    except ImportError:
        continue

    factories = mod.init()
    try:
        _adapters.extend(factories)
    except TypeError:
        _adapters.append(factories)
