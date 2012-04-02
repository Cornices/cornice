# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.util import to_list


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
            return (attr.location in to_list(location) and
                    attr.required in to_list(required))

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
