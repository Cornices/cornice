# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.resource import resource
from cornice.service import (Service, get_services, clear_services,
                             decorate_view, _UnboundView)
from cornice.tests import validationapp
from cornice.tests.support import TestCase, DummyRequest
from cornice.ext.swagger import generate_swagger_spec


schema = validationapp.FooBarSchema


def _validator(req):
    return True


class TestSwaggerService(TestCase):

    def tearDown(self):
        clear_services()

    def _generate_swagger(self, service):
        info = {'title': 'Joes API', 'version': '0.1', 'contact': {
                'name': 'Joe Smith',
                'email': 'joe.cool@swagger.com'}
                }
        base_path = '/jcool'
        spec = generate_swagger_spec([service], info['title'],
                                     info['version'], info=info,
                                     basePath=base_path)
        return spec

    def test_with_klass(self):
        class TemperatureCooler(object):
            """Temp class docstring"""
            def get_view(self):
                """Temp view docstring"""
                pass
        service = Service("TemperatureCooler", "/freshair",
                          klass=TemperatureCooler)
        service.add_view("get", "get_view", validators=_validator,
                         schema=schema)
        ret = self._generate_swagger(service)
        self.assertEqual(ret["info"], {'version': '0.1', 'contact': {'name': 'Joe Smith', 'email': 'joe.cool@swagger.com'}, 'title': 'Joes API'})
        self.assertEqual(ret["basePath"], '/jcool')
        self.assertEqual(ret["swagger"], '2.0')
        self.assertEqual(ret["tags"], [
            {'name': 'freshair', 'description': 'Temp class docstring'}])
        self.assertEqual(ret["paths"], {'/freshair': {'head': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'string', 'description': '', 'in': 'query', 'name': 'yeah'}], 'produces': ['application/json']}, 'get': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'string', 'description': '', 'in': 'query', 'name': 'yeah'}], 'produces': ['application/json']}}})

    def test_declerative(self):
        service = Service("TemperatureCooler", "/freshair")

        class TemperatureCooler(object):
            """Temp class docstring"""
            @service.get(validators=_validator, schema=schema)
            def view_get(self, request):
                """Temp view docstring"""
                return "red"

        # service.add_view("GET", lambda x: "red", validators=_validator,
        #                  schema=schema)
        ret = self._generate_swagger(service)
        self.assertEqual(ret["tags"], [
            {'name': 'freshair'}])
        self.assertEqual(ret["paths"], {'/freshair': {'head': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'string', 'description': '', 'in': 'query', 'name': 'yeah'}], 'produces': ['application/json']}, 'get': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'string', 'description': '', 'in': 'query', 'name': 'yeah'}], 'produces': ['application/json']}}})

    def test_imperative(self):
        service = Service("TemperatureCooler", "/freshair")

        class TemperatureCooler(object):
            """Temp class docstring"""
            def view_get(self, request):
                """Temp view docstring"""
                return "red"

        service.add_view("GET", TemperatureCooler.view_get,
                         validators=_validator, schema=schema)
        ret = self._generate_swagger(service)
        self.assertEqual(ret["tags"], [
            {'name': 'freshair', 'description': 'Temp class docstring'}])
        self.assertEqual(ret["paths"], {'/freshair': {'head': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'string', 'description': '', 'in': 'query', 'name': 'yeah'}], 'produces': ['application/json']}, 'get': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'string', 'description': '', 'in': 'query', 'name': 'yeah'}], 'produces': ['application/json']}}})
