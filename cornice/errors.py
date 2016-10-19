# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
try:
    import simplejson as json
except ImportError:
    import json


class Errors(list):
    """Holds Request errors
    """
    def __init__(self, status=400):
        self.status = status
        super(Errors, self).__init__()

    def add(self, location, name=None, description=None, **kw):
        """Registers a new error."""
        allowed = ('body', 'querystring', 'url', 'header', 'path',
                   'cookies', 'method')
        if location != '' and location not in allowed:
            raise ValueError('%r not in %s' % (location, allowed))

        self.append(dict(
            location=location,
            name=name,
            description=description, **kw))

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
