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
import json

from pyramid import testing
from webtest import TestApp

from cornice import Service
from cornice.tests import CatchErrors
from cornice.schemas import CorniceSchema

try:
    from colander import Invalid, MappingSchema, SchemaNode, String, Integer, Range
    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:
    foobar = Service(name="foobar", path="/foobar")

    def validate_bar(node, value):
        if value != 'open':
            raise Invalid(node, "The bar is not open.")

    class FooBarSchema(MappingSchema):
        # foo and bar are required, baz is optional
        foo = SchemaNode(String(), location="body", type='str')
        bar = SchemaNode(String(), location="body", type='str', validator=validate_bar)
        baz = SchemaNode(String(), location="body", type='str', missing=None)
        yeah = SchemaNode(String(), location="querystring", type='str')
        ipsum = SchemaNode(Integer(), location="body", type='int', missing=1, validator=Range(0, 3))

    class SchemaFromQuerystring(MappingSchema):
        yeah = SchemaNode(String(), location="querystring", type='str')

    @foobar.post(schema=FooBarSchema)
    def foobar_post(request):
        return {"test": "succeeded", 'baz': request.validated['baz']}

    @foobar.get(schema=SchemaFromQuerystring)
    def foobar_get(request):
        return {"test": "succeeded"}

    class TestServiceDescription(unittest.TestCase):

        def setUp(self):
            self.config = testing.setUp()
            self.config.include("cornice")
            self.config.scan("cornice.tests.test_service_description")
            self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

        def tearDown(self):
            testing.tearDown()

        def test_get_from_colander(self):
            schema = CorniceSchema.from_colander(FooBarSchema)
            attrs = schema.as_dict()
            self.assertEqual(len(attrs), 5)

        def test_description_attached(self):
            # foobar should contain a schema argument containing the cornice
            # schema object, so it can be introspected if needed
            self.assertTrue('POST' in foobar.schemas)

        def test_schema_validation(self):
            # using a colander schema for the service should automatically
            # validate the request calls. Let's make some of them here.
            resp = self.app.post('/foobar', status=400)
            self.assertEqual(resp.json['status'], 'error')

            errors = resp.json['errors']
            # we should at have 1 missing value in the QS...
            self.assertEqual(1, len([e for e in errors
                                    if e['location'] == "querystring"]))

            # ... and 2 in the body (a json error as well)
            self.assertEqual(2, len([e for e in errors
                                    if e['location'] == "body"]))

            # let's do the same request, but with information in the
            # querystring
            resp = self.app.post('/foobar?yeah=test', status=400)

            # we should at have no missing value in the QS
            self.assertEqual(0, len([e for e in resp.json['errors']
                                    if e['location'] == "querystring"]))

            # and if we add the required values in the body of the post,
            # then we should be good
            data = {'foo': 'yeah', 'bar': 'open'}
            resp = self.app.post('/foobar?yeah=test', params=json.dumps(data),
                                status=200)

            self.assertEqual(resp.json, {u'baz': None, "test": "succeeded"})

        def test_schema_validation2(self):
            resp = self.app.get('/foobar?yeah=test', status=200)
            self.assertEqual(resp.json, {"test": "succeeded"})

        def test_bar_validator(self):
            # test validator on bar attribute
            data = {'foo': 'yeah', 'bar': 'closed'}
            resp = self.app.post('/foobar?yeah=test', params=json.dumps(data),
                                 status=400)

            self.assertEqual(resp.json, {
                    u'errors': [{u'description': u'The bar is not open.',
                    u'location': u'body',
                    u'name': u'bar'}],
                    u'status': u'error'})

        def test_foo_required(self):
            # test required attribute
            data = {'bar': 'open'}
            resp = self.app.post('/foobar?yeah=test', params=json.dumps(data),
                                 status=400)

            self.assertEqual(resp.json, {
                    u'errors': [{u'description': u'foo is missing',
                    u'location': u'body',
                    u'name': u'foo'}],
                    u'status': u'error'})

        def test_default_baz_value(self):
            # test required attribute
            data = {'foo': 'yeah', 'bar': 'open'}
            resp = self.app.post('/foobar?yeah=test', params=json.dumps(data),
                                 status=200)

            self.assertEqual(resp.json, {u'baz': None, "test": "succeeded"})

        def test_ipsum_error_message(self):
            # test required attribute
            data = {'foo': 'yeah', 'bar': 'open', 'ipsum': 5}
            resp = self.app.post('/foobar?yeah=test', params=json.dumps(data),
                                 status=400)

            self.assertEqual(resp.json, {
                    u'errors': [{u'description': u'5 is greater than maximum value 3',
                    u'location': u'body',
                    u'name': u'ipsum'}],
                    u'status': u'error'})

