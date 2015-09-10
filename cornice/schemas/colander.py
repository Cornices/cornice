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
    def __init__(self, schema, bind_request=True, flattening=False):
        if inspect.isclass(schema) and issubclass(schema, colander.Schema):
            schema = schema()
        super(ColanderAdapter, self).__init__(schema)

        if not isinstance(self.schema, colander.Schema):
            raise generic.UnsuitableSchemaCtrl
        if not self._is_mapping_field(self.schema):
            raise generic.UnsuitableSchemaCtrl

        self.bind_request = bind_request
        self.need_flattening = flattening

    def __call__(self, request):
        schema = self.schema.clone()
        if self.bind_request:
            schema = schema.bind(request=request)

        data, fields_to_location = self._assemble_request_data(schema, request)
        data = self._flattening_data(schema, data)
        try:
            validated = schema.deserialize(data)
        except colander.Invalid as e:
            for error in e.children:
                self.request.errors.add(
                    self._get_field_location(error.node),
                    error.node.name,
                    error.asdict())
        return validated, errors

    @classmethod
    def _assemble_request_data(cls, schema, request):
        sources = {
            'path': request.matchdict,
            'header': request.headers,
            'body': util.extract_request_body(request),
            'querystring': request.GET}

        data = dict()
        fields_to_location = dict()
        invalid_locations = list()

        for field in schema:
            source_name = cls._get_field_location(field)
            try:
                location = sources[source_name]
            except KeyError:
                invalid_locations.append(field)
                continue
            fields_to_location[field.name] = source_name

            is_multi = isinstance(location, multidict.MultiDict)

            try:
                value = location[field.name]
                if is_multi and cls._is_sequence_field(field):
                    value = location.getall(field.name)
            except KeyError:
                continue

            data[field.name] = value

        if invalid_locations:
            raise generic.InvalidSchemaError(
                'Schema contain fields with unsupported "location" markers',
                invalid_locations)

        # copy unknown fields
        for location in ('body', 'querystring'):
            for name, value in sources[location].iteritems():
                data.setdefault(name, value)
                fields_to_location.setdefault(name, location)

        return data, fields_to_location

    def _flattening_data(self, schema, data):
        if not self.need_flattening:
            return data
        return schema.unflatten(data)


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


def init():
    return generic.AdapterDescriptor('colander', ColanderAdapter)
