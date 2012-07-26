# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.util import to_list, extract_request_data


class CorniceSchema(object):
    """Defines a cornice schema"""

    def __init__(self, nodes):
        self._attributes = nodes

    def get_attributes(self, location=("body", "headers", "querystring"),
                       required=(True, False)):
        """Return a list of attributes that match the given criteria.

        By default, if nothing is specified, it will return all the attributes,
        without filtering anything.
        """
        def _filter(attr):
            if not hasattr(attr, "location"):
                valid_location = 'body' in location
            else:
                valid_location = attr.location in to_list(location)
            return valid_location and attr.required in to_list(required)

        return filter(_filter, self._attributes)

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
        return CorniceSchema(colander_schema.nodes)


def validate_colander_schema(schema, request):
    """Validates that the request is conform to the given schema"""
    from colander import Invalid

    def _validate_fields(location, data):
        for attr in schema.get_attributes(location=location):
            if attr.required and not attr.name in data:
                # missing
                request.errors.add(location, attr.name,
                                   "%s is missing" % attr.name)
            else:
                try:
                    if not attr.name in data:
                        deserialized = attr.deserialize()
                    else:
                        deserialized = attr.deserialize(data[attr.name])
                except Invalid, e:
                    # the struct is invalid
                    try:
                        request.errors.add(location, attr.name,
                                           e.asdict()[attr.name])
                    except KeyError:
                        for k, v in e.asdict().items():
                            if k.startswith(attr.name):
                                request.errors.add(location, k, v)
                else:
                    request.validated[attr.name] = deserialized

    qs, headers, body, path = extract_request_data(request)

    _validate_fields('path', path)
    _validate_fields('header', headers)
    _validate_fields('body', body)
    _validate_fields('querystring', qs)
