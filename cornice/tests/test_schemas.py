from unittest import TestCase
from cornice.schemas import CorniceSchema
from cornice.tests.validationapp import FooBarSchema


class TestSchemas(TestCase):

    def test_colander_integration(self):
        schema = CorniceSchema.from_colander(FooBarSchema)
        body_fields = schema.get_attributes(location="body")
        qs_fields = schema.get_attributes(location="querystring")

        self.assertEquals(len(body_fields), 4)
        self.assertEquals(len(qs_fields), 1)
