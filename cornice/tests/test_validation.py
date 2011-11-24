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
