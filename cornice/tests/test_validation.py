# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import simplejson as json

from webtest import TestApp
from pyramid.response import Response

from cornice.errors import Errors
from cornice.tests.validationapp import main
from cornice.tests.support import LoggingCatcher, TestCase
from cornice.validators import filter_json_xsrf


class TestServiceDefinition(LoggingCatcher, TestCase):

    def test_validation(self):
        app = TestApp(main({}))
        app.get('/service', status=400)

        res = app.post('/service', params='buh', status=400)
        self.assertTrue(b'Not a json body' in res.body)

        res = app.post('/service', params=json.dumps('buh'))

        self.assertEqual(res.body, json.dumps({'body': '"buh"'}).encode('ascii'))

        app.get('/service?paid=yup')

        # valid = foo is one
        res = app.get('/service?foo=1&paid=yup')
        self.assertEqual(res.json['foo'], 1)

        # invalid value for foo
        res = app.get('/service?foo=buh&paid=yup', status=400)

        # check that json is returned
        errors = Errors.from_json(res.body)
        self.assertEqual(len(errors), 1)

    def test_validation_hooked_error_response(self):
        app = TestApp(main({}))

        res = app.post('/service4', status=400)
        self.assertTrue(b'<errors>' in res.body)

    def test_accept(self):
        # tests that the accept headers are handled the proper way
        app = TestApp(main({}))

        # requesting the wrong accept header should return a 406 ...
        res = app.get('/service2', headers={'Accept': 'audio/*'}, status=406)

        # ... with the list of accepted content-types
        error_location = res.json['errors'][0]['location']
        error_name = res.json['errors'][0]['name']
        error_description = res.json['errors'][0]['description']
        self.assertEquals('header', error_location)
        self.assertEquals('Accept', error_name)
        self.assertTrue('application/json' in error_description)
        self.assertTrue('text/json' in error_description)
        self.assertTrue('text/plain' in error_description)

        # requesting a supported type should give an appropriate response type
        r = app.get('/service2', headers={'Accept': 'application/*'})
        self.assertEqual(r.content_type, "application/json")

        r = app.get('/service2', headers={'Accept': 'text/plain'})
        self.assertEqual(r.content_type, "text/plain")

        # it should also work with multiple Accept headers
        r = app.get('/service2', headers={'Accept': 'audio/*, application/*'})
        self.assertEqual(r.content_type, "application/json")

        # and requested preference order should be respected
        r = app.get('/service2',
                    headers={'Accept': 'application/json; q=1.0, text/plain; q=0.9'})
        self.assertEqual(r.content_type, "application/json")

        r = app.get('/service2',
                    headers={'Accept': 'text/plain; q=0.9, application/json; q=1.0'})
        self.assertEqual(r.content_type, "application/json")

        # test that using a callable to define what's accepted works as well
        res = app.get('/service3', headers={'Accept': 'audio/*'}, status=406)
        error_description = res.json['errors'][0]['description']
        self.assertTrue('text/json' in error_description)

        res = app.get('/service3', headers={'Accept': 'text/*'}, status=200)
        self.assertEqual(res.content_type, "text/json")

        # if we are not asking for a particular content-type,
        # we should get one of the two types that the service supports.
        r = app.get('/service2', status=200)
        self.assertTrue(r.content_type in ("application/json", "text/plain"))

    def test_accept_issue_113_text_star(self):
        app = TestApp(main({}))

        res = app.get('/service3', headers={'Accept': 'text/*'}, status=200)
        self.assertEqual(res.content_type, "text/json")

    def test_accept_issue_113_text_application_star(self):
        app = TestApp(main({}))

        res = app.get('/service3', headers={'Accept': 'application/*'}, status=200)
        self.assertEqual(res.content_type, "application/json")

    def test_accept_issue_113_text_application_json(self):
        app = TestApp(main({}))

        res = app.get('/service3', headers={'Accept': 'application/json'}, status=200)
        self.assertEqual(res.content_type, "application/json")

    def test_accept_issue_113_text_html_not_acceptable(self):
        app = TestApp(main({}))

        # requesting an unsupported content type should return a HTTP 406 (Not Acceptable)
        res = app.get('/service3', headers={'Accept': 'text/html'}, status=406)

    def test_accept_issue_113_audio_or_text(self):
        app = TestApp(main({}))

        res = app.get('/service2', headers={'Accept': 'audio/mp4; q=0.9, text/plain; q=0.5'}, status=200)
        self.assertEqual(res.content_type, "text/plain")

        # if we are not asking for a particular content-type,
        # we should get one of the two types that the service supports.
        r = app.get('/service2', status=200)
        self.assertTrue(r.content_type in ("application/json", "text/plain"))

    def test_filters(self):
        app = TestApp(main({}))

        # filters can be applied to all the methods of a service
        self.assertTrue(b"filtered response" in app.get('/filtered').body)
        self.assertTrue(b"unfiltered" in app.post('/filtered').body)

    def test_json_xsrf(self):

        def json_response(string_value):
            resp = Response(string_value)
            resp.status = 200
            resp.content_type = 'application/json'
            filter_json_xsrf(resp)

        # a view returning a vulnerable json response should issue a warning
        for value in [
            '["value1", "value2"]',  # json array
            '  \n ["value1", "value2"] ',  # may include whitespace
            '"value"',  # strings may contain nasty characters in UTF-7
            ]:
            resp = Response(value)
            resp.status = 200
            resp.content_type = 'application/json'
            filter_json_xsrf(resp)
            assert len(self.get_logs()) == 1, "Expected warning: %s" % value

        # a view returning safe json response should not issue a warning
        for value in [
            '{"value1": "value2"}',  # json object
            '  \n {"value1": "value2"} ',  # may include whitespace
            'true', 'false', 'null',  # primitives
            '123', '-123', '0.123',  # numbers
            ]:
            resp = Response(value)
            resp.status = 200
            resp.content_type = 'application/json'
            filter_json_xsrf(resp)
            assert len(self.get_logs()) == 0, "Unexpected warning: %s" % value

    def test_multiple_querystrings(self):
        app = TestApp(main({}))

        # it is possible to have more than one value with the same name in the
        # querystring
        self.assertEquals(b'{"field": ["5"]}', app.get('/foobaz?field=5').body)
        self.assertEquals(b'{"field": ["5", "2"]}',
                          app.get('/foobaz?field=5&field=2').body)

    def test_email_field(self):
        app = TestApp(main({}))
        content = json.dumps({'email': 'alexis@notmyidea.org'})
        app.post('/newsletter', params=content)

    def test_content_type_missing(self):
        # test that a Content-Type request headers is present
        app = TestApp(main({}))

        # requesting without a Content-Type header should return a 415 ...
        request = app.RequestClass.blank('/service5', method='POST')
        response = app.do_request(request, 415, True)

        # ... with an appropriate json error structure
        error_location = response.json['errors'][0]['location']
        error_name = response.json['errors'][0]['name']
        error_description = response.json['errors'][0]['description']
        self.assertEqual('header', error_location)
        self.assertEqual('Content-Type', error_name)
        self.assertTrue('application/json' in error_description)

    def test_content_type_wrong_single(self):
        # tests that the Content-Type request header satisfies the requirement
        app = TestApp(main({}))

        # requesting the wrong Content-Type header should return a 415 ...
        response = app.post('/service5',
            headers={'Content-Type': 'text/plain'}, status=415)

        # ... with an appropriate json error structure
        error_description = response.json['errors'][0]['description']
        self.assertTrue('application/json' in error_description)

    def test_content_type_wrong_multiple(self):
        # tests that the Content-Type request header satisfies the requirement
        app = TestApp(main({}))

        # requesting the wrong Content-Type header should return a 415 ...
        response = app.put('/service5',
            headers={'Content-Type': 'text/xml'}, status=415)

        # ... with an appropriate json error structure
        error_description = response.json['errors'][0]['description']
        self.assertTrue('text/plain' in error_description)
        self.assertTrue('application/json' in error_description)

    def test_content_type_correct(self):
        # tests that the Content-Type request header satisfies the requirement
        app = TestApp(main({}))

        # requesting with one of the allowed Content-Type headers should work,
        # even when having a charset parameter as suffix
        response = app.put('/service5',
            headers={'Content-Type': 'text/plain; charset=utf-8'}, status=200)
        self.assertEqual(response.json, "some response")

    def test_content_type_on_get(self):
        # test that a Content-Type request header is not
        # checked on GET requests, they don't usually have a body
        app = TestApp(main({}))
        response = app.get('/service5')
        self.assertEqual(response.json, "some response")

    def test_content_type_with_callable(self):
        # test that using a callable for content_type works as well
        app = TestApp(main({}))
        res = app.post('/service6', headers={'Content-Type': 'audio/*'}, status=415)
        error_description = res.json['errors'][0]['description']
        self.assertTrue('text/xml' in error_description)
        self.assertTrue('application/json' in error_description)

        app.post('/service6', headers={'Content-Type': 'text/xml'}, status=200)

    def test_accept_and_content_type(self):
        # tests that giving both Accept and Content-Type
        # request headers satisfy the requirement
        app = TestApp(main({}))

        # POST endpoint just has one accept and content_type definition
        response = app.post('/service7',
            headers={
                'Accept': 'text/xml, application/json',
                'Content-Type': 'application/json; charset=utf-8'}, status=200)
        self.assertEqual(response.json, "some response")

        response = app.post('/service7',
            headers={
                'Accept': 'text/plain, application/json',
                'Content-Type': 'application/json; charset=utf-8'}, status=406)

        response = app.post('/service7',
            headers={
                'Accept': 'text/xml, application/json',
                'Content-Type': 'application/x-www-form-urlencoded'}, status=415)

        # PUT endpoint has a list of accept and content_type definitions
        response = app.put('/service7',
            headers={
                'Accept': 'text/xml, application/json',
                'Content-Type': 'application/json; charset=utf-8'}, status=200)
        self.assertEqual(response.json, "some response")

        response = app.put('/service7',
            headers={
                'Accept': 'audio/*',
                'Content-Type': 'application/json; charset=utf-8'}, status=406)

        response = app.put('/service7',
            headers={
                'Accept': 'text/xml, application/json',
                'Content-Type': 'application/x-www-form-urlencoded'}, status=415)
