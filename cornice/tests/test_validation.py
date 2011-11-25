import unittest
import json

from webtest import TestApp
from cornice.tests.validationapp import main
from webtest.app import AppError


class TestServiceDefinition(unittest.TestCase):

    def test_validation(self):
        app = TestApp(main({}))
        app.get('/service')

        self.assertRaises(AppError, app.post, '/service', params='buh')
        res = app.post('/service', params=json.dumps('buh'))

        self.assertEqual(res.body, json.dumps({'body': '"buh"'}))

        app.get('/service')

        # valid = foo is one
        res = app.get('/service?foo=1')
        self.assertEqual(res.json['foo'], 1)

        # invalid value for foo
        self.assertRaises(AppError, app.get, '/service?foo=buh')
