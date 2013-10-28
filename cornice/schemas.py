# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.util import to_list, extract_request_data


class CorniceSchema(object):
    """Defines a cornice schema"""

    def __init__(self, _colander_schema):
        self._c_schema = _colander_schema

    def bind_attributes(self, request=None):
        if callable(self._c_schema):
            self._schema_inst = self._c_schema()
        else:
            self._schema_inst = self._c_schema
        if request:
            self._attributes = self._schema_inst.bind(request=request).children
        else:
            self._attributes = self._schema_inst.children

    def get_attributes(self, location=("body", "header", "querystring"),
                       required=(True, False),
                       request=None):
        """Return a list of attributes that match the given criteria.

        By default, if nothing is specified, it will return all the attributes,
        without filtering anything.
        """
        if not hasattr(self, '_attributes'):
            self.bind_attributes(request)

        def _filter(attr):
            if not hasattr(attr, "location"):
                valid_location = 'body' in location
            else:
                valid_location = attr.location in to_list(location)
            return valid_location and attr.required in to_list(required)

        return list(filter(_filter, self._attributes))

    def as_dict(self):
        """returns a dict containing keys for the different attributes, and
        for each of them, a dict containing information about them::

            >>> schema.as_dict()
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
        if not hasattr(self, '_attributes'):
            self.bind_attributes()
        schema = {}
        for attr in self._attributes:
            schema[attr.name] = {
                'type': getattr(attr, 'type', attr.typ),
                'name': attr.name,
                'description': getattr(attr, 'description', ''),
                'required': getattr(attr, 'required', False),
            }

        return schema

    @classmethod
    def from_colander(klass, colander_schema):
        return CorniceSchema(colander_schema)


def validate_colander_schema(schema, request):
    """Validates that the request is conform to the given schema"""
    from colander import Invalid, Sequence, drop

    def _validate_fields(location, data):
        for attr in schema.get_attributes(location=location,
                                          request=request):
            if attr.required and not attr.name in data:
                # missing
                request.errors.add(location, attr.name,
                                   "%s is missing" % attr.name)
            else:
                try:
                    if not attr.name in data:
                        deserialized = attr.deserialize()
                    else:
                        if (location == 'querystring' and
                                isinstance(attr.typ, Sequence)):
                            serialized = data.getall(attr.name)
                        else:
                            serialized = data[attr.name]
                        deserialized = attr.deserialize(serialized)
                except Invalid as e:
                    # the struct is invalid
                    try:
                        request.errors.add(location, attr.name,
                                           e.asdict()[attr.name])
                    except KeyError:
                        for k, v in e.asdict().items():
                            if k.startswith(attr.name):
                                request.errors.add(location, k, v)
                else:
                    if deserialized is not drop:
                        request.validated[attr.name] = deserialized

    qs, headers, body, path = extract_request_data(request)

    _validate_fields('path', path)
    _validate_fields('header', headers)
    _validate_fields('body', body)
    _validate_fields('querystring', qs)

    # These taken from colander's _SchemaNode::deserialize
    # to apply preparer/validator on the root node
    from colander.compat import is_nonstr_iter
    c_schema = schema._schema_inst
    if c_schema.preparer is not None:
        # if the preparer is a function, call a single preparer
        if hasattr(c_schema.preparer, '__call__'):
            request.validated = c_schema.preparer(request.validated)
            # if the preparer is a list, call each separate preparer
        elif is_nonstr_iter(c_schema.preparer):
            for preparer in c_schema.preparer:
                request.validated = preparer(request.validated)

    from colander import deferred
    if c_schema.validator is not None:
        if not isinstance(c_schema.validator, deferred): # unbound
            c_schema.validator(c_schema, request.validated)