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
        self.assertTrue('Not a json body' in res.body)

        res = app.post('/service', params=json.dumps('buh'))

        self.assertEqual(res.body, json.dumps({'body': '"buh"'}))

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
        self.assertTrue('<errors>' in res.body)

    def test_accept(self):
        # tests that the accept headers are handled the proper way
        app = TestApp(main({}))

        # requesting the wrong accept header should return a 406 ...
        res = app.get('/service2', headers={'Accept': 'audio/*'}, status=406)

        # ... with the list of accepted content-types
        self.assertTrue('application/json' in res.json)
        self.assertTrue('text/json' in res.json)
        self.assertTrue('text/plain' in res.json)

        # requesting a supported type should give an appropriate response type
        r = app.get('/service2', headers={'Accept': 'application/*'})
        self.assertEquals(r.content_type, "application/json")

        r = app.get('/service2', headers={'Accept': 'text/plain'})
        self.assertEquals(r.content_type, "text/plain")

        # it should also work with multiple Accept headers
        r = app.get('/service2', headers={'Accept': 'audio/*, application/*'})
        self.assertEquals(r.content_type, "application/json")

        # and requested preference order should be respected
        r = app.get('/service2',
                    headers={'Accept': 'application/json, text/plain'})
        self.assertEquals(r.content_type, "application/json")

        r = app.get('/service2',
                    headers={'Accept': 'text/plain, application/json'})
        self.assertEquals(r.content_type, "application/json")

        # test that using a callable to define what's accepted works as well
        res = app.get('/service3', headers={'Accept': 'audio/*'}, status=406)
        self.assertTrue('text/json' in res.json)

        app.get('/service3', headers={'Accept': 'text/*'}, status=200)

        # if we are not asking for a particular content-type,
        # we should get the type defined by outermost declaration.
        r = app.get('/service2', status=200)
        self.assertEquals(r.content_type, "application/json")

    def test_filters(self):
        app = TestApp(main({}))

        # filters can be applied to all the methods of a service
        self.assertTrue("filtered response" in app.get('/filtered').body)
        self.assertTrue("unfiltered" in app.post('/filtered').body)

    def test_json_xsrf(self):
        # a view returning a json list should issue a warning
        resp = Response(json.dumps(('value1', 'value2')))
        resp.status = 200
        resp.content_type = 'application/json'
        filter_json_xsrf(resp)
        self.assertEquals(len(self.get_logs()), 1)

        # json lists can also start end end with spaces
        resp = Response(" ('value1', 'value2') ")
        resp.status = 200
        resp.content_type = 'application/json'
        filter_json_xsrf(resp)
        self.assertEquals(len(self.get_logs()), 1)
