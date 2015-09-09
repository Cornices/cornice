# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

import abc
import collections

from cornice import util


class InvalidSchemaError(Exception):
    pass


class UnsuitableSchemaCtrl(Exception):
    pass


class GenericAdapter(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, schema):
        self.schema = schema

    @abc.abstractmethod
    def __call__(self, request):
        pass


class CallableAdapter(GenericAdapter):
    def __init__(self, schema):
        if not isinstance(schema, collections.Callable):
            raise UnsuitableSchemaCtrl
        super(CallableAdapter, self).__init__(schema)

    def __call__(self, request):
        payload = util.extract_request_body(request)
        return self.schema(payload), tuple()


# Backward compatibility
class CorniceSchema(object):
    def __init__(self, schema, bind_request=True):
        self.schema = schema
        self.bind_request = bind_request

    @classmethod
    def from_colander(cls, schema, **kwargs):
        return cls(schema, **kwargs)


def init():
    return CallableAdapter
