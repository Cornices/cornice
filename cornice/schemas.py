# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import webob.multidict

from pyramid.path import DottedNameResolver
from cornice.util import to_list, extract_request_data


class SchemaError(Exception):
    pass


class CorniceSchema(object):
    """Defines a cornice schema"""

    def __init__(self, _colander_schema, bind_request=True):
        self._colander_schema = _colander_schema
        self._colander_schema_runtime = None
        self._bind_request = bind_request

    @property
    def colander_schema(self):
        if not self._colander_schema_runtime:
            schema = self._colander_schema
            schema = DottedNameResolver(__name__).maybe_resolve(schema)
            if callable(schema):
                schema = schema()
            self._colander_schema_runtime = schema
        return self._colander_schema_runtime

    def bind_attributes(self, request=None):
        schema = self.colander_schema
        if request and self._bind_request:
            schema = schema.bind(request=request)
        return schema.children

    def get_attributes(self, location=("body", "header", "querystring"),
                       required=(True, False),
                       request=None):
        """Return a list of attributes that match the given criteria.

        By default, if nothing is specified, it will return all the attributes,
        without filtering anything.
        """
        attributes = self.bind_attributes(request)

        def _filter(attr):
            if not hasattr(attr, "location"):
                valid_location = 'body' in location
            else:
                valid_location = attr.location in to_list(location)
            return valid_location and attr.required in to_list(required)

        return list(filter(_filter, attributes))

    def as_dict(self):
        """returns a dict containing keys for the different attributes, and
        for each of them, a dict containing information about them::

            >>> schema.as_dict()  # NOQA
            {'foo': {'type': 'string',
                     'location': 'body',
                     'description': 'yeah',
                     'required': True},
             'bar': {'type': 'string',
                     'location': 'body',
                     'description': 'yeah',
                     'required': True}
             # ...
             }
        """
        attributes = self.bind_attributes()
        schema = {}
        for attr in attributes:
            schema[attr.name] = {
                'type': getattr(attr, 'type', attr.typ),
                'name': attr.name,
                'description': getattr(attr, 'description', ''),
                'required': getattr(attr, 'required', False),
            }

        return schema

    def unflatten(self, data):
        return self.colander_schema.unflatten(data)

    def flatten(self, data):
        return self.colander_schema.flatten(data)

    @classmethod
    def from_colander(klass, colander_schema, **kwargs):
        return CorniceSchema(colander_schema, **kwargs)


def validate_colander_schema(schema, request):
    """Validates that the request is conform to the given schema"""
    from colander import Invalid, Sequence, drop, null, Mapping

    # CorniceSchema.colander_schema guarantees that we have a colander
    #  instance and not a class so we should use `typ` and not
    #  `schema_type()` to determine the type.
    schema_type = schema.colander_schema.typ
    unknown = getattr(schema_type, 'unknown', None)

    if not isinstance(schema_type, Mapping):
        raise SchemaError('colander schema type is not a Mapping: %s' %
                          type(schema_type))

    def _extract_fields(location, data):
        if location == 'body':
            try:
                original = data
                data = webob.multidict.MultiDict(schema.unflatten(data))
                data.update(original)
            except KeyError:
                pass

        if location == 'querystring':
            try:
                original = data
                data = schema.unflatten(original)
            except KeyError:
                pass

        meta = {
            'cstruct': {},
            'locations': {},
        }

        for attr in schema.get_attributes(location=location,
                                          request=request):
            if (location == 'querystring' and
                    isinstance(attr.typ, Sequence)):
                meta['cstruct'][attr.name] = original.getall(attr.name)
            elif attr.name in data:
                meta['cstruct'][attr.name] = data[attr.name]

            meta['locations'][attr.name] = location

        if location == "body" and unknown == 'preserve':
            for field, value in data.items():
                if field not in request.validated and\
                   field not in meta['cstruct']:
                    request.validated[field] = value

        return meta

    qs, headers, body, path = extract_request_data(request)

    cstruct = {}
    attr_locs = {}

    # tried to preserve original order here since each call could overwrite
    # existing keys
    for location in [('path', path), ('header', headers),
                     ('body', body), ('querystring', qs)]:
        meta = _extract_fields(location[0], location[1])
        cstruct.update(meta['cstruct'])
        attr_locs.update(meta['locations'])

    try:
        appstruct = schema.colander_schema.deserialize(cstruct)
    except Invalid as e:
        for k, v in e.asdict().iteritems():
            v = '%s is missing' % k if v == 'Required' else v

            try:
                location = attr_locs[k]
            except KeyError:
                for attr in attr_locs.keys():
                    if k.startswith(attr):
                        location = attr_locs[attr]

            request.errors.add(location, k, v)

        return

    for k,v in appstruct.iteritems():
        request.validated[k] = v

    # validate unknown
    if unknown == 'raise':
        attrs = schema.get_attributes(location=('body', 'querystring'),
                                      request=request)
        params = list(qs.keys()) + list(body.keys())
        msg = '%s is not allowed'
        for param in set(params) - set([attr.name for attr in attrs]):
            request.errors.add('body' if param in body else 'querystring',
                               param, msg % param)
