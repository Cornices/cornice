# -*- encoding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import mock
import unittest
import warnings

import simplejson as json
from webtest import TestApp

from tests.support import get_request

try:
    import colander
    COLANDER = True
except ImportError:
    COLANDER = False

from cornice.errors import Errors
from cornice.validators import colander_validator, colander_body_validator

from .validationapp import main
from .support import LoggingCatcher, TestCase, DummyRequest


skip_if_no_colander = unittest.skipIf(COLANDER is False,
                                      "colander is not installed.")


@skip_if_no_colander
class TestServiceDefinition(LoggingCatcher, TestCase):

    def test_validation(self):
        app = TestApp(main({}))
        app.get('/service', status=400)

        response = app.post('/service', params='buh', status=400)
        self.assertTrue(b'Not a json body' in response.body)

        response = app.post('/service', params=json.dumps('buh'))

        expected = json.dumps({'body': '"buh"'}).encode('ascii')
        self.assertEqual(response.body, expected)

        app.get('/service?paid=yup')

        # valid = foo is one
        response = app.get('/service?foo=1&paid=yup')
        self.assertEqual(response.json['foo'], 1)

        # invalid value for foo
        response = app.get('/service?foo=buh&paid=yup', status=400)

        # check that json is returned
        errors = Errors.from_json(response.body)
        self.assertEqual(len(errors), 1)

    def test_validation_hooked_error_response(self):
        app = TestApp(main({}))

        response = app.post('/service4', status=400)
        self.assertTrue(b'<errors>' in response.body)

    def test_accept(self):
        # tests that the accept headers are handled the proper way
        app = TestApp(main({}))

        # requesting the wrong accept header should return a 406 ...
        response = app.get('/service2', headers={'Accept': 'audio/*'},
                           status=406)

        # ... with the list of accepted content-types
        error_location = response.json['errors'][0]['location']
        error_name = response.json['errors'][0]['name']
        error_description = response.json['errors'][0]['description']
        self.assertEquals('header', error_location)
        self.assertEquals('Accept', error_name)
        self.assertIn('application/json', error_description)
        self.assertIn('text/json', error_description)
        self.assertIn('text/plain', error_description)

        # requesting a supported type should give an appropriate response type
        response = app.get('/service2', headers={'Accept': 'application/*'})
        self.assertEqual(response.content_type, "application/json")

        response = app.get('/service2', headers={'Accept': 'text/plain'})
        self.assertEqual(response.content_type, "text/plain")

        # it should also work with multiple Accept headers
        response = app.get('/service2', headers={
            'Accept': 'audio/*, application/*'
        })
        self.assertEqual(response.content_type, "application/json")

        # and requested preference order should be respected
        headers = {'Accept': 'application/json; q=1.0, text/plain; q=0.9'}
        response = app.get('/service2', headers=headers)
        self.assertEqual(response.content_type, "application/json")

        headers = {'Accept': 'application/json; q=0.9, text/plain; q=1.0'}
        response = app.get('/service2', headers=headers)
        self.assertEqual(response.content_type, "text/plain")

        # test that using a callable to define what's accepted works as well
        response = app.get('/service3', headers={'Accept': 'audio/*'},
                           status=406)
        error_description = response.json['errors'][0]['description']
        self.assertIn('text/json', error_description)

        response = app.get('/service3', headers={'Accept': 'text/*'})
        self.assertEqual(response.content_type, "text/json")

        # Test that using a callable to define what's accepted works as well.
        # Now, the callable returns a scalar instead of a list.
        response = app.put('/service3', headers={'Accept': 'audio/*'},
                           status=406)
        error_description = response.json['errors'][0]['description']
        self.assertIn('text/json', error_description)

        response = app.put('/service3', headers={'Accept': 'text/*'})
        self.assertEqual(response.content_type, "text/json")

        # If we are not asking for a particular content-type,
        # we should get one of the two types that the service supports.
        response = app.get('/service2')
        self.assertIn(response.content_type,
                      ("application/json", "text/plain"))

    def test_accept_issue_113_text_star(self):
        app = TestApp(main({}))

        response = app.get('/service3', headers={'Accept': 'text/*'})
        self.assertEqual(response.content_type, "text/json")

    def test_accept_issue_113_text_application_star(self):
        app = TestApp(main({}))

        response = app.get('/service3', headers={'Accept': 'application/*'})
        self.assertEqual(response.content_type, "application/json")

    def test_accept_issue_113_text_application_json(self):
        app = TestApp(main({}))

        response = app.get('/service3', headers={'Accept': 'application/json'})
        self.assertEqual(response.content_type, "application/json")

    def test_accept_issue_113_text_html_not_acceptable(self):
        app = TestApp(main({}))

        # Requesting an unsupported content type should
        # return HTTP response "406 Not Acceptable".
        app.get('/service3', headers={'Accept': 'text/html'}, status=406)

    def test_accept_issue_113_audio_or_text(self):
        app = TestApp(main({}))

        response = app.get('/service2', headers={
            'Accept': 'audio/mp4; q=0.9, text/plain; q=0.5'
        })
        self.assertEqual(response.content_type, "text/plain")

        # If we are not asking for a particular content-type,
        # we should get one of the two types that the service supports.
        response = app.get('/service2')
        self.assertIn(response.content_type,
                      ("application/json", "text/plain"))

    def test_override_default_accept_issue_252(self):
        # Override default acceptable content_types for interoperate with
        # legacy applications i.e. ExtJS 3.
        from cornice.util import _JsonRenderer
        _JsonRenderer.acceptable += ('text/html',)

        app = TestApp(main({}))

        response = app.get('/service5', headers={'Accept': 'text/html'})
        self.assertEqual(response.content_type, "text/html")
        # revert the override
        _JsonRenderer.acceptable = _JsonRenderer.acceptable[:-1]

    def test_filters(self):
        app = TestApp(main({}))

        # filters can be applied to all the methods of a service
        self.assertTrue(b"filtered response" in app.get('/filtered').body)
        self.assertTrue(b"unfiltered" in app.post('/filtered').body)

    def test_multiple_querystrings(self):
        app = TestApp(main({}))

        # it is possible to have more than one value with the same name in the
        # querystring
        self.assertEquals(b'{"field": ["5"]}', app.get('/foobaz?field=5').body)
        self.assertEquals(b'{"field": ["5", "2"]}',
                          app.get('/foobaz?field=5&field=2').body)

    def test_content_type_missing(self):
        # test that a Content-Type request headers is present
        app = TestApp(main({}))

        # Requesting without a Content-Type header should
        # return "415 Unsupported Media Type" ...
        request = app.RequestClass.blank('/service5', method='POST',
                                         POST="some data")
        response = app.do_request(request, 415, True)
        self.assertEqual(response.status_code, 415)

        # ... with an appropriate json error structure.
        error_location = response.json['errors'][0]['location']
        error_name = response.json['errors'][0]['name']
        error_description = response.json['errors'][0]['description']
        self.assertEqual('header', error_location)
        self.assertEqual('Content-Type', error_name)
        self.assertIn('application/json', error_description)

    def test_validated_body_content_from_schema(self):
        app = TestApp(main({}))
        content = {'email': 'alexis@notmyidea.org'}
        response = app.post_json('/newsletter', params=content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['body'], content)

    def test_validated_querystring_content_from_schema(self):
        app = TestApp(main({}))
        response = app.post_json('/newsletter?ref=3')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['querystring'], {"ref": 3})

    def test_validated_querystring_and_schema_from_same_schema(self):
        app = TestApp(main({}))
        content = {'email': 'alexis@notmyidea.org'}
        response = app.post_json('/newsletter?ref=20', params=content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['body'], content)
        self.assertEqual(response.json['querystring'], {"ref": 20})

        response = app.post_json('/newsletter?ref=2', params=content,
                                 status=400)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['errors'][0]['description'],
                         'Invalid email length')

    def test_validated_path_content_from_schema(self):
        # Test validation request.matchdict.  (See #411)
        app = TestApp(main({}))
        response = app.get('/item/42', status=200)
        self.assertEqual(response.json, {'item_id': 42})

    def test_content_type_with_no_body_should_pass(self):
        app = TestApp(main({}))

        request = app.RequestClass.blank('/newsletter', method='POST',
                                         headers={'Content-Type':
                                                  'application/json'})
        response = app.do_request(request, 200, True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['body'], {})

    def test_content_type_missing_with_no_body_should_pass(self):
        app = TestApp(main({}))

        # requesting without a Content-Type header nor a body should
        # return a 200.
        request = app.RequestClass.blank('/newsletter', method='POST')
        response = app.do_request(request, 200, True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['body'], {})

    def test_content_type_wrong_single(self):
        # Tests that the Content-Type request header satisfies the requirement.
        app = TestApp(main({}))

        # Requesting the wrong Content-Type header should
        # return "415 Unsupported Media Type" ...
        response = app.post('/service5',
                            headers={'Content-Type': 'text/plain'},
                            status=415)

        # ... with an appropriate json error structure.
        error_description = response.json['errors'][0]['description']
        self.assertIn('application/json', error_description)

    def test_content_type_wrong_multiple(self):
        # Tests that the Content-Type request header satisfies the requirement.
        app = TestApp(main({}))

        # Requesting without a Content-Type header should
        # return "415 Unsupported Media Type" ...
        response = app.put('/service5',
                           headers={'Content-Type': 'text/xml'},
                           status=415)

        # ... with an appropriate json error structure.
        error_description = response.json['errors'][0]['description']
        self.assertIn('text/plain', error_description)
        self.assertIn('application/json', error_description)

    def test_content_type_correct(self):
        # Tests that the Content-Type request header satisfies the requirement.
        app = TestApp(main({}))

        # Requesting with one of the allowed Content-Type headers should work,
        # even when having a charset parameter as suffix.
        response = app.put('/service5', headers={
            'Content-Type': 'text/plain; charset=utf-8'
        })
        self.assertEqual(response.json, "some response")

    def test_content_type_on_get(self):
        # Test that a Content-Type request header is not
        # checked on GET requests, they don't usually have a body.
        app = TestApp(main({}))
        response = app.get('/service5')
        self.assertEqual(response.json, "some response")

    def test_content_type_with_callable(self):
        # Test that using a callable for content_type works as well.
        app = TestApp(main({}))
        response = app.post('/service6', headers={'Content-Type': 'audio/*'},
                            status=415)
        error_description = response.json['errors'][0]['description']
        self.assertIn('text/xml', error_description)
        self.assertIn('application/json', error_description)

    def test_content_type_with_callable_returning_scalar(self):
        # Test that using a callable for content_type works as well.
        # Now, the callable returns a scalar instead of a list.
        app = TestApp(main({}))
        response = app.put('/service6', headers={'Content-Type': 'audio/*'},
                           status=415)
        error_description = response.json['errors'][0]['description']
        self.assertIn('text/xml', error_description)

    def test_accept_and_content_type(self):
        # Tests that using both the "Accept" and "Content-Type"
        # request headers satisfy the requirement.
        app = TestApp(main({}))

        # POST endpoint just has one accept and content_type definition
        response = app.post('/service7', headers={
            'Accept': 'text/xml, application/json',
            'Content-Type': 'application/json; charset=utf-8'
        })
        self.assertEqual(response.json, "some response")

        response = app.post(
            '/service7',
            headers={
                'Accept': 'text/plain, application/json',
                'Content-Type': 'application/json; charset=utf-8'
            },
            status=406)

        response = app.post(
            '/service7',
            headers={
                'Accept': 'text/xml, application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            status=415)

        # PUT endpoint has a list of accept and content_type definitions
        response = app.put('/service7', headers={
            'Accept': 'text/xml, application/json',
            'Content-Type': 'application/json; charset=utf-8'
        })
        self.assertEqual(response.json, "some response")

        response = app.put(
            '/service7',
            headers={
                'Accept': 'audio/*',
                'Content-Type': 'application/json; charset=utf-8'
            },
            status=406)

        response = app.put(
            '/service7',
            headers={
                'Accept': 'text/xml, application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }, status=415)


@skip_if_no_colander
class TestRequestDataExtractors(LoggingCatcher, TestCase):

    def make_ordinary_app(self):
        return TestApp(main({}))

    def test_valid_json(self):
        app = self.make_ordinary_app()
        response = app.post_json('/signup', {
            'username': 'man',
        })
        self.assertEqual(response.json['username'], 'man')

    def test_invalid_json(self):
        app = self.make_ordinary_app()
        response = app.post('/signup',
                            '{"foo": "bar"',
                            headers={'content-type': 'application/json'},
                            status=400)
        self.assertEqual(response.json['status'], 'error')
        error_description = response.json['errors'][0]['description']
        self.assertIn('Invalid JSON: Expecting', error_description)

    def test_json_text(self):
        app = self.make_ordinary_app()
        response = app.post('/signup',
                            '"invalid json input"',
                            headers={'content-type': 'application/json'},
                            status=400)
        self.assertEqual(response.json['status'], 'error')
        error_description = response.json['errors'][0]['description']
        self.assertIn('Should be a JSON object', error_description)

    def test_www_form_urlencoded(self):
        app = self.make_ordinary_app()
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        response = app.post('/signup',
                            'username=man',
                            headers=headers)
        self.assertEqual(response.json['username'], 'man')


@skip_if_no_colander
class TestErrorMessageTranslation(TestCase):

    def post(self, settings={}, headers={}):
        app = TestApp(main({}, **settings))
        return app.post_json('/foobar?yeah=test', {
            'foo': 'hello',
            'bar': 'open',
            'yeah': 'man',
            'ipsum': 10,
        }, status=400, headers=headers)

    def assertErrorDescription(self, response, message):
        error_description = response.json['errors'][0]['description']
        self.assertEqual(error_description, message)

    def test_accept_language_header(self):
        response = self.post(
            settings={'available_languages': 'fr en'},
            headers={'Accept-Language': 'fr'})
        self.assertErrorDescription(
            response,
            u'10 est plus grand que la valeur maximum autorisée (3)')

    def test_default_language(self):
        response = self.post(settings={
            'available_languages': 'fr ja',
            'pyramid.default_locale_name': 'ja',
        })
        self.assertErrorDescription(
            response,
            u'10 は最大値 3 を超過しています')

    def test_default_language_fallback(self):
        """Should fallback to default language if requested language is not
        available"""
        response = self.post(
            settings={
                'available_languages': 'ja en',
                'pyramid.default_locale_name': 'ja',
            },
            headers={'Accept-Language': 'ru'})
        self.assertErrorDescription(
            response,
            u'10 は最大値 3 を超過しています')

    def test_no_language_settings(self):
        response = self.post()
        self.assertErrorDescription(
            response,
            u'10 is greater than maximum value 3')


@skip_if_no_colander
class TestValidatorEdgeCases(TestCase):

    @staticmethod
    def _create_request_schema(schema):
        class Schema(colander.MappingSchema):
            body = schema()
        return Schema

    def test_schema_class_deprecated(self):
        RequestSchema = TestValidatorEdgeCases._create_request_schema(
            colander.MappingSchema)

        request = DummyRequest()
        request.validated = {}
        with warnings.catch_warnings(record=True) as w:
            warnings.resetwarnings()
            colander_validator(request, schema=RequestSchema)
        self.assertEqual(len(w), 1)
        self.assertIs(w[0].category, DeprecationWarning)

    def test_no_schema(self):
        request = DummyRequest()
        request.validated = mock.sentinel.validated
        colander_validator(request)
        self.assertEqual(request.validated, mock.sentinel.validated)
        self.assertEqual(len(request.errors), 0)

    def test_no_body_schema(self):
        request = DummyRequest()
        request.validated = mock.sentinel.validated
        colander_body_validator(request)
        self.assertEqual(request.validated, mock.sentinel.validated)
        self.assertEqual(len(request.errors), 0)

    def test_schema_sequence_none(self):
        """None can be passed to a sequence field"""
        class BodyNoneSchema(colander.MappingSchema):
            foo = colander.SchemaNode(colander.String())
            bar = colander.SchemaNode(
                colander.Sequence(),
                colander.SchemaNode(colander.String()), missing=None)

        RequestBodyNoneSchema = TestValidatorEdgeCases._create_request_schema(
            BodyNoneSchema)

        request = get_request(body={'foo': '1', 'bar': None})
        request.validated = {}
        colander_validator(request, schema=RequestBodyNoneSchema)
        self.assertEqual(len(request.errors), 0)

    def test_schema_sequence_nested_none(self):
        """None can be passed to a nested sequence field"""
        class BodyNoneSchema(colander.MappingSchema):
            foo = colander.SchemaNode(colander.String())
            bar = colander.SchemaNode(
                colander.Sequence(),
                colander.SchemaNode(colander.String()), missing=None)

        class BodyNestedNoneSchema(colander.MappingSchema):
            a = colander.SchemaNode(colander.String())
            b = BodyNoneSchema()

        RequestBodyNestedNoneSchema = \
            TestValidatorEdgeCases._create_request_schema(
                BodyNestedNoneSchema)

        request = get_request(body={"a": "a", "b": {"foo": "abc", "bar": None}})
        request.validated = {}
        colander_validator(request, schema=RequestBodyNestedNoneSchema)
        self.assertEqual(len(request.errors), 0)

    def test_schema_nested_none(self):
        """None can be passed to a mapping field"""
        class SchemaA(colander.MappingSchema):
            val = colander.SchemaNode(colander.String())

        class SchemaB(colander.MappingSchema):
            a = SchemaA(missing=colander.drop)

        class BodySchemaC(colander.MappingSchema):
            b = SchemaB()

        RequestBodySchemaC = TestValidatorEdgeCases._create_request_schema(
            BodySchemaC)

        request = get_request(body={"b": {"a": {"val": "ok"}}})
        request.validated = {}
        colander_validator(request, schema=RequestBodySchemaC)
        self.assertEqual(len(request.errors), 0)

        request = get_request(body={"b": {"a": None}})
        request.validated = {}
        colander_validator(request, schema=RequestBodySchemaC)
        self.assertEqual(len(request.errors), 0)

    def test_schema_nested_tuple_none(self):
        """None can be passed to a tuple field"""
        class Tuple(colander.TupleSchema):
            val1 = colander.SchemaNode(colander.String())
            val2 = colander.SchemaNode(colander.Int())

        class TupleSchema(colander.MappingSchema):
            t = Tuple(missing=colander.drop)

        class BodyNestedTupleSchema(colander.MappingSchema):
            n = TupleSchema()

        RequestBodyNestedTupleSchema = \
            TestValidatorEdgeCases._create_request_schema(
                BodyNestedTupleSchema)

        request = get_request(body={"n": {"t": ["s", 1]}})
        request.validated = {}
        colander_validator(request, schema=RequestBodyNestedTupleSchema)
        self.assertEqual(len(request.errors), 0)

        request = get_request(body={"n": {"t": None}})
        request.validated = {}
        colander_validator(request, schema=RequestBodyNestedTupleSchema)
        self.assertEqual(len(request.errors), 0)
