# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

import inspect

import colander
from webob import multidict

from cornice.schemas import generic
from cornice import util


class ColanderAdapter(generic.GenericAdapter):
    UNKNOWN_DROP = 0
    UNKNOWN_KEEP = 1
    UNKNOWN_ERROR = 2

    def __init__(self, schema, bind_request=True,
                 unknown=None):
        if inspect.isclass(schema) and issubclass(schema, colander.Schema):
            schema = schema()
        super(ColanderAdapter, self).__init__(schema)

        if not isinstance(self.schema, colander.Schema):
            raise generic.UnsuitableSchemaCtrl
        if not self._is_mapping_field(self.schema):
            raise generic.UnsuitableSchemaCtrl

        self.bind_request = bind_request

        if unknown is None:
            for attr in (self.schema.typ, self.schema):
                try:
                    unknown = getattr(attr, 'unknown')
                    break
                except AttributeError:
                    pass
            else:
                unknown = self.UNKNOWN_DROP
        self.unknown = unknown

    def __call__(self, request):
        schema = self.schema.clone()
        if self.bind_request:
            schema = schema.bind(self.request)

        data, missing_fields = self._assemble_request_data(schema)
        schema = self._patch_schema(schema, missing_fields)

        try:
            validated = schema.deserialize(data)
        except colander.Invalid as e:
            for error in e.children:
                self.request.errors.add(
                    self._get_field_location(error.node),
                    error.node.name,
                    error.asdict())
        else:
            self.request.validated.update(validated)

    def _assemble_request_data(self, schema):
        sources = {
            'path': self.request.matchdict,
            'header': self.request.headers,
            'body': util.extract_request_body(self.request),
            'querystring': self.request.GET}

        data = dict()
        invalid_locations = list()

        for field in schema:
            source_name = self._get_field_location(field)
            try:
                location = sources[source_name]
            except KeyError:
                invalid_locations.append(field)
                continue

            is_multi = isinstance(location, multidict.MultiDict)

            try:
                value = location[field.name]
                if is_multi and self._is_sequence_field(field):
                    value = location.getall(field.name)
            except KeyError:
                continue

            data[field.name] = value

        if invalid_locations:
            raise generic.InvalidSchemaError(
                'Schema contain fields with unsupported "location" markers',
                invalid_locations)

        missing_fields = list()
        known_fields = set(data)

        if self.unknown != self.UNKNOWN_DROP:
            for location in 'querystring', 'body':
                for name in sources[location]:
                    try:
                        known_fields.remove(name)
                    except KeyError:
                        continue
                    data[name] = location[name]
                    missing_fields.append((location, name))

        return data, missing_fields

    def _patch_schema(self, schema, missing_fields):
        if self.unknown == self.UNKNOWN_DROP:
            return schema
        elif self.unknown == self.UNKNOWN_KEEP:
            field_factory = functools.partial(
                colander.SchemaNode, _RawType())
        elif self.unknown == self.UNKNOWN_ERROR:
            field_factory = functools.partial(
                colander.SchemaNode, _RawType(),
                validator=_ForceFailValidator('Unexpected field'))
        else:
            raise generic.InvalidSchemaError(
                'Unsupported "unknown" value.', self.unknown)

        for field in missing_fields:
            schema.add(field_factory(name=field))

    @staticmethod
    def _is_mapping_field(field):
        return isinstance(field.typ, colander.Mapping)

    @staticmethod
    def _is_sequence_field(field):
        return isinstance(
            field.typ, (colander.Positional, colander.List, colander.Set))

    @staticmethod
    def _get_field_location(field):
        return getattr(field, 'location', 'body')


class _RawType(colander.SchemaType):
    def serialize(self, node, appstruct):
        return appstruct

    def deserialize(self, node, cstruct):
        return cstruct


class _ForceFailValidator(object):
    def __init__(self, message='Forced error'):
        self.message = message

    def __call__(self, node, value):
        raise colander.Invalid(node, self.message, value)


def init():
    return generic.AdapterDescriptor('colander', ColanderAdapter)
