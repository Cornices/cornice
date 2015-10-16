# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.resource import resource, view
from cornice.service import (Service, clear_services, get_services,
                             decorate_view, _UnboundView)
from cornice.tests import validationapp
from cornice.tests.support import TestCase
from cornice.ext.swagger import generate_swagger_spec


schema = validationapp.FooBarSchema


def _validator(req):
    return True


def _generate_swagger(services):
    info = {'title': 'Joes API', 'version': '0.1', 'contact': {
            'name': 'Joe Smith',
            'email': 'joe.cool@swagger.com'}
            }
    base_path = '/jcool'
    spec = generate_swagger_spec(services, info['title'],
                                 info['version'], info=info,
                                 basePath=base_path)
    return spec


class TestSwaggerService(TestCase):

    def tearDown(self):
        clear_services()

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
        ret = _generate_swagger([service])
        self.assertEqual(ret["info"], {'version': '0.1', 'contact': {'name': 'Joe Smith', 'email': 'joe.cool@swagger.com'}, 'title': 'Joes API'})
        self.assertEqual(ret["basePath"], '/jcool')
        self.assertEqual(ret["swagger"], '2.0')
        self.assertEqual(ret["tags"], [
            {'name': 'freshair', 'description': 'Temp class docstring'}])
        self.assertEqual(ret["paths"], {'/freshair': {'head': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'String', 'description': '', 'in': 'query', 'name': 'yeah'}, {'in': 'body', 'description': 'Defines a cornice schema', 'name': 'body', 'schema': {'$ref': '#/definitions/FooBarSchema'}}], 'produces': ['application/json']}, 'get': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'String', 'description': '', 'in': 'query', 'name': 'yeah'}, {'in': 'body', 'description': 'Defines a cornice schema', 'name': 'body', 'schema': {'$ref': '#/definitions/FooBarSchema'}}], 'produces': ['application/json']}}})
        self.assertEqual(ret["definitions"], {'FooBarSchema': {'required': ['foo', 'bar'], 'type': 'object', 'properties': {'baz': {'required': False, 'type': 'string', 'name': 'baz'}, 'foo': {'required': True, 'type': 'string', 'name': 'foo'}, 'bar': {'required': True, 'type': 'string', 'name': 'bar'}, 'integers': {'required': False, 'name': 'integers', 'schema': {'items': {'required': True, 'type': 'integer', 'name': 'integer'}, 'type': 'array'}}, 'ipsum': {'minimum': 0, 'required': False, 'type': 'integer', 'maximum': 3, 'name': 'ipsum'}}}})

    def test_declerative(self):
        service = Service("TemperatureCooler", "/freshair")

        class TemperatureCooler(object):
            """Temp class docstring"""
            @service.get(validators=_validator, schema=schema)
            def view_get(self, request):
                """Temp view docstring"""
                return "red"

        ret = _generate_swagger([service])
        self.assertEqual(ret["tags"], [
            {'name': 'freshair'}])
        self.assertEqual(ret["paths"], {'/freshair': {'head': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'String', 'description': '', 'in': 'query', 'name': 'yeah'}, {'in': 'body', 'description': 'Defines a cornice schema', 'name': 'body', 'schema': {'$ref': '#/definitions/FooBarSchema'}}], 'produces': ['application/json']}, 'get': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'String', 'description': '', 'in': 'query', 'name': 'yeah'}, {'in': 'body', 'description': 'Defines a cornice schema', 'name': 'body', 'schema': {'$ref': '#/definitions/FooBarSchema'}}], 'produces': ['application/json']}}})
        self.assertEqual(ret["definitions"], {'FooBarSchema': {'required': ['foo', 'bar'], 'type': 'object', 'properties': {'baz': {'required': False, 'type': 'string', 'name': 'baz'}, 'foo': {'required': True, 'type': 'string', 'name': 'foo'}, 'bar': {'required': True, 'type': 'string', 'name': 'bar'}, 'integers': {'required': False, 'name': 'integers', 'schema': {'items': {'required': True, 'type': 'integer', 'name': 'integer'}, 'type': 'array'}}, 'ipsum': {'minimum': 0, 'required': False, 'type': 'integer', 'maximum': 3, 'name': 'ipsum'}}}})

    def test_imperative(self):
        service = Service("TemperatureCooler", "/freshair")

        class TemperatureCooler(object):
            """Temp class docstring"""
            def view_get(self, request):
                """Temp view docstring"""
                return "red"

        service.add_view("GET", TemperatureCooler.view_get,
                         validators=_validator, schema=schema)
        ret = _generate_swagger([service])
        self.assertEqual(ret["tags"], [
            {'name': 'freshair', 'description': 'Temp class docstring'}])
        self.assertEqual(ret["paths"], {'/freshair': {'head': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'String', 'description': '', 'in': 'query', 'name': 'yeah'}, {'in': 'body', 'description': 'Defines a cornice schema', 'name': 'body', 'schema': {'$ref': '#/definitions/FooBarSchema'}}], 'produces': ['application/json']}, 'get': {'tags': ['freshair'], 'summary': 'Temp view docstring', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'String', 'description': '', 'in': 'query', 'name': 'yeah'}, {'in': 'body', 'description': 'Defines a cornice schema', 'name': 'body', 'schema': {'$ref': '#/definitions/FooBarSchema'}}], 'produces': ['application/json']}}})
        self.assertEqual(ret["definitions"], {'FooBarSchema': {'required': ['foo', 'bar'], 'type': 'object', 'properties': {'baz': {'required': False, 'type': 'string', 'name': 'baz'}, 'foo': {'required': True, 'type': 'string', 'name': 'foo'}, 'bar': {'required': True, 'type': 'string', 'name': 'bar'}, 'integers': {'required': False, 'name': 'integers', 'schema': {'items': {'required': True, 'type': 'integer', 'name': 'integer'}, 'type': 'array'}}, 'ipsum': {'minimum': 0, 'required': False, 'type': 'integer', 'maximum': 3, 'name': 'ipsum'}}}})


class TestSwaggerResource(TestCase):

    def tearDown(self):
        clear_services()

    def test_resource(self):
        @resource(collection_path='/users', path='/users/{id}',
                  name='user_service')
        class User(object):
            def __init__(self, request, context=None):
                self.request = request
                self.context = context

            def collection_get(self):
                return {'users': [1, 2, 3]}

            @view(renderer='json', content_type='application/json',
                  schema=schema)
            def collection_post(self):
                return {'test': 'yeah'}
        services = get_services()
        ret = _generate_swagger(services)

        self.assertEqual(ret["paths"], {'/users': {'head': {'summary': '', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'tags': ['users'], 'produces': ['application/json']}, 'post': {'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'String', 'description': '', 'in': 'query', 'name': 'yeah'}, {'in': 'body', 'description': 'Defines a cornice schema', 'name': 'body', 'schema': {'$ref': '#/definitions/FooBarSchema'}}], 'produces': ['application/json'], 'tags': ['users'], 'consumes': ['application/json'], 'summary': ''}, 'get': {'summary': '', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'tags': ['users'], 'produces': ['application/json']}}, '/coffee': {'head': {'summary': '', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'tags': ['coffee'], 'produces': ['application/json']}, 'get': {'summary': '', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'tags': ['coffee'], 'produces': ['application/json']}}, '/users/{id}': {'parameters': [{'required': True, 'type': 'string', 'name': 'id', 'in': 'path'}]}, '/coffee/{bar}/{id}': {'head': {'tags': ['coffee'], 'summary': '', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'string', 'name': 'bar', 'in': 'path'}, {'required': True, 'type': 'string', 'name': 'id', 'in': 'path'}], 'produces': ['application/json']}, 'parameters': [{'required': True, 'type': 'string', 'name': 'bar', 'in': 'path'}, {'required': True, 'type': 'string', 'name': 'id', 'in': 'path'}], 'get': {'tags': ['coffee'], 'summary': '', 'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}}, 'parameters': [{'required': True, 'type': 'string', 'name': 'bar', 'in': 'path'}, {'required': True, 'type': 'string', 'name': 'id', 'in': 'path'}], 'produces': ['application/json']}}})
