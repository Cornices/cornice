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


def wrap_request(request):
    """Adds a "validated" dict and a custom "errors" object to
    the request object if they don't already exists
    """
    if not hasattr(request, 'validated'):
        setattr(request, 'validated', {})

    if not hasattr(request, 'errors'):
        setattr(request, 'errors', Errors(request))


class Errors(list):

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
        return Errors.from_list(json.loads(string))

    @classmethod
    def from_list(cls, object):
        """Transforms a python list into an `Errors` instance"""
        errors = Errors()
        for error in object:
            errors.add(error['location'], error['name'],
                    error['description'])
        return errors


class JsonBody(object):
    """The request body should be a JSON object.
    """
    def __call__(self, request):
        try:
            body = json.loads(request.body)
            request.validated['body'] = body
        except ValueError:
            request.errors.add('body', description='Not a json body')


class Field(object):
    def __init__(self, name, required=False):
        self.name = name
        self.required = required

    def convert(self, value):
        return value

    def get_description(self):
        return self.name


class Integer(Field):
    def __init__(self, name, min=None, max=None, required=False):
        super(Integer, self).__init__(name, required)
        self.min = min
        self.max = max

    def convert(self, value):
        value = int(value)

        if self.min and value < self.min:
            raise ValueError('%r is too small' % self.name)

        if self.max and value > self.max:
            raise ValueError('%r is too big' % self.name)

        return value

    def get_description(self):
        desc = '%r must be an Integer.'
        if self.min:
            desc += ', min value: %d' % self.min
        if self.max:
            desc += ', max value: %d' % self.max
        if self.required:
            desc += ' (required)'

        return desc


class FormChecker(object):
    fields = []

    def __init__(self, description=None):
        if description is not None:
            self.__doc__ = description
        else:
            self.__doc__ = self._set_description()

    def _get_form(self, request):
        raise NotImplementedError()

    def _set_description(self):
        desc = []
        for field in self.fields:
            desc.append(field.get_description())
        self.__doc__ = '\n'.join(desc).strip()

    def __call__(self, request):
        form = self._get_form(request)

        for field in self.fields:
            if field.name not in form:
                if field.required:
                    request.errors.add('body', field.name,
                            '%r missing' % field.name)
            else:
                try:
                    request.validated[field.name] = \
                            field.convert(form[field.name])
                except ValueError, e:
                    request.errors.add('body', field.name, e.message)


class GetChecker(FormChecker):
    def _get_form(self, request):
        return request.GET


class PostChecker(FormChecker):
    def _get_form(self, request):
        return request.POST
