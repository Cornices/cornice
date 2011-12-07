import unittest
import simplejson as json

from webtest import TestApp
from cornice.tests.validationapp import main
from cornice.schemas import Errors


class TestServiceDefinition(unittest.TestCase):

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

        # let's see the docstring !
        apidocs = app.app.registry.settings['apidocs']
        post_doc = apidocs[('/service', 'POST')]['docstring']
        self.assertEqual(post_doc.strip(),
                         'The request body should be a JSON object.')

    def test_accept(self):
        # tests that the accept headers are handled the proper way
        app = TestApp(main({}))

        # requesting the wrong accept header should return a 406 ...
        res = app.get('/service2', headers={'Accept': 'audio/*'}, status=406)

        # ... with the list of accepted content-types
        self.assertTrue('text/json' in res.json)

        app.get('/service2', headers={'Accept': 'text/*'}, status=200)

        # it should also work with multiple Accept headers
        app.get('/service2', headers={'Accept': 'audio/*, text/*'}, status=200)

        # test that using a callable to define what's accepted works as well
        app.get('/service3', headers={'Accept': 'audio/*'}, status=406)
        app.get('/service3', headers={'Accept': 'text/*'}, status=200)

        # if we are not asking for a particular content-type, everything
        # should work just fine
        app.get('/service2', status=200)
