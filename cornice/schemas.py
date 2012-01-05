# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Sync Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
#   Alexis Metaireau (alexis@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
""" Validators.
"""
import simplejson as json

from cornice.util import to_list


class Errors(list):
    """Holds Request errors
    """
    def __init__(self, request=None):
        self.request = request
        super(Errors, self).__init__()

    def add(self, location, name=None, description=None):
        """Registers a new error."""
        self.append(dict(
            location=location,
            name=name,
            description=description))

    @classmethod
    def from_json(cls, string):
        """Transforms a json string into an `Errors` instance"""
        obj = json.loads(string)
        return Errors.from_list(obj.get('errors', []))

    @classmethod
    def from_list(cls, obj):
        """Transforms a python list into an `Errors` instance"""
        errors = Errors()
        for error in obj:
            errors.add(**error)
        return errors


class CorniceSchema(object):
    """Defines a cornice schema"""

    def __init__(self, nodes):
        self._attributes = nodes

    def get_attributes(self, location=("body", "headers", "querystring"),
                       required=True):
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
