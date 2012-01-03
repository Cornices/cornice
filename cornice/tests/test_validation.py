# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Cornice (Sagrada)
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
#   Alexis Metaireau (alexis@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
import unittest
import simplejson as json

from webtest import TestApp
from cornice.tests.validationapp import main, _json
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

        # the "apidocs" registry entry contains all the needed information
        # to build up documentation
        # in this case, this means the function is registered and the argument
        # of the service are defined (e.g "validator" is set)
        apidocs = app.app.registry.settings['apidocs']

        self.assertTrue(_json in apidocs[('/service', 'POST')]['validators'])

    def test_accept(self):
        # tests that the accept headers are handled the proper way
        app = TestApp(main({}))

        # requesting the wrong accept header should return a 406 ...
        res = app.get('/service2', headers={'Accept': 'audio/*'}, status=406)

        # ... with the list of accepted content-types
        self.assertTrue('application/json' in res.json)
        self.assertTrue('text/json' in res.json)

        app.get('/service2', headers={'Accept': 'application/*'}, status=200)

        # it should also work with multiple Accept headers
        app.get('/service2', headers={'Accept': 'audio/*, application/*'},
                status=200)

        # test that using a callable to define what's accepted works as well
        res = app.get('/service3', headers={'Accept': 'audio/*'}, status=406)
        self.assertTrue('text/json' in res.json)

        app.get('/service3', headers={'Accept': 'text/*'}, status=200)

        # if we are not asking for a particular content-type, everything
        # should work just fine
        app.get('/service2', status=200)

    def test_filters(self):
        app = TestApp(main({}))

        # filters can be applied to all the methods of a service
        self.assertTrue("filtered response" in app.get('/filtered').body)
        self.assertTrue("unfiltered" in app.post('/filtered').body)
