import unittest
import simplejson as json

from webtest import TestApp
from webtest.app import AppError
from cornice.tests.validationapp import main


class TestServiceDefinition(unittest.TestCase):

    def test_validation(self):
        app = TestApp(main({}))
        app.get('/service', status=402)

        res = app.post('/service', params='buh', status=400)
        self.assertTrue('Not a json body' in res.body)

        res = app.post('/service', params=json.dumps('buh'))

        self.assertEqual(res.body, json.dumps({'body': '"buh"'}))

        app.get('/service?paid=yup')

        # valid = foo is one
        res = app.get('/service?foo=1&paid=yup')
        self.assertEqual(res.json['foo'], 1)

        # invalid value for foo
        self.assertRaises(AppError, app.get, '/service?foo=buh&paid=yup')

        # let's see the docstring !
        apidocs = app.app.registry.settings['apidocs']
        post_doc = apidocs[('/service', 'POST')]['docstring']
        self.assertEqual(post_doc, 'The request body should be a JSON object.')
