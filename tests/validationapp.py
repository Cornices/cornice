# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import json

from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPBadRequest

from cornice import Service

from .support import CatchErrors


# Service for testing callback-based validators.
service = Service(name="service", path="/service")


def has_payed(request, **kw):
    if 'paid' not in request.GET:
        request.errors.add('body', 'paid', 'You must pay!')


def foo_int(request, **kw):
    if 'foo' not in request.GET:
        return
    try:
        request.validated['foo'] = int(request.GET['foo'])
    except ValueError:
        request.errors.add('url', 'foo', 'Not an int')


@service.get(validators=(has_payed, foo_int))
def get1(request):
    res = {"test": "succeeded"}
    try:
        res['foo'] = request.validated['foo']
    except KeyError:
        pass

    return res


def _json(request, **kw):
    """The request body should be a JSON object."""
    try:
        request.validated['json'] = json.loads(request.body.decode('utf-8'))
    except ValueError:
        request.errors.add('body', 'json', 'Not a json body')


@service.post(validators=_json)
def post1(request):
    return {"body": request.body}


# Service for testing the "accept" parameter (scalar and list).
service2 = Service(name="service2", path="/service2")


@service2.get(accept=("application/json", "text/json"))
@service2.get(accept=("text/plain"), renderer="string")
def get2(request):
    return {"body": "yay!"}


# Service for testing the "accept" parameter (callable).
service3 = Service(name="service3", path="/service3")


@service3.get(accept=lambda request: ('application/json', 'text/json'))
@service3.put(accept=lambda request: 'text/json')
def get3(request):
    return {"body": "yay!"}


def _filter(response):
    response.body = b"filtered response"
    return response

service4 = Service(name="service4", path="/service4")


def fail(request, **kw):
    request.errors.add('body', 'xml', 'Not XML')


def xml_error(request):
    errors = request.errors
    lines = ['<errors>']
    for error in errors:
        lines.append('<error>'
                     '<location>%(location)s</location>'
                     '<type>%(name)s</type>'
                     '<message>%(description)s</message>'
                     '</error>' % error)
    lines.append('</errors>')
    return HTTPBadRequest(body=''.join(lines))


@service4.post(validators=fail, error_handler=xml_error)
def post4(request):
    raise ValueError("Shouldn't get here")

# test filtered services
filtered_service = Service(name="filtered", path="/filtered", filters=_filter)


@filtered_service.get()
@filtered_service.post(exclude=_filter)
def get4(request):
    return "unfiltered"  # should be overwritten on GET


# Service for testing the "content_type" parameter (scalar and list).
service5 = Service(name="service5", path="/service5")


@service5.get()
@service5.post(content_type='application/json')
@service5.put(content_type=('text/plain', 'application/json'))
def post5(request):
    return "some response"


# Service for testing the "content_type" parameter (callable).
service6 = Service(name="service6", path="/service6")


@service6.post(content_type=lambda request: ('text/xml', 'application/json'))
@service6.put(content_type=lambda request: 'text/xml')
def post6(request):
    return {"body": "yay!"}


# Service for testing a mix of "accept" and "content_type" parameters.
service7 = Service(name="service7", path="/service7")


@service7.post(accept='text/xml', content_type='application/json')
@service7.put(accept=('text/xml', 'text/plain'),
              content_type=('application/json', 'text/xml'))
def post7(request):
    return "some response"


try:
    from colander import (
        Invalid,
        MappingSchema,
        SequenceSchema,
        SchemaNode,
        String,
        Integer,
        Range,
        Email,
        drop,
        null
    )

    from cornice.validators import colander_validator, colander_body_validator

    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:

    signup = Service(name="signup", path="/signup")

    class SignupSchema(MappingSchema):
        username = SchemaNode(String())

    @signup.post(schema=SignupSchema, validators=(colander_body_validator,))
    def signup_post(request):
        return request.validated

    def validate_bar(node, value):
        if value != 'open':
            raise Invalid(node, "The bar is not open.")

    class Integers(SequenceSchema):
        integer = SchemaNode(Integer(), type='int')

    class BodySchema(MappingSchema):
        # foo and bar are required, baz is optional
        foo = SchemaNode(String())
        bar = SchemaNode(String(), validator=validate_bar)
        baz = SchemaNode(String(), missing=None)
        ipsum = SchemaNode(Integer(), missing=1,
                           validator=Range(0, 3))
        integers = Integers(missing=())

    class Query(MappingSchema):
        yeah = SchemaNode(String(), type='str')

    class RequestSchema(MappingSchema):
        body = BodySchema()
        querystring = Query()

        def deserialize(self, cstruct):
            if 'body' in cstruct and cstruct['body'] == b'hello,open,yeah':
                values = cstruct['body'].decode().split(',')
                cstruct['body'] = dict(zip(['foo', 'bar', 'yeah'], values))

            return MappingSchema.deserialize(self, cstruct)

    foobar = Service(name="foobar", path="/foobar")

    @foobar.post(schema=RequestSchema, validators=(colander_validator,))
    def foobar_post(request):
        return {"test": "succeeded"}

    class StringSequence(SequenceSchema):
        _ = SchemaNode(String())

    class ListQuerystringSequence(MappingSchema):
        field = StringSequence()

        def deserialize(self, cstruct):
            if 'field' in cstruct and not isinstance(cstruct['field'], list):
                cstruct['field'] = [cstruct['field']]
            return MappingSchema.deserialize(self, cstruct)

    class QSSchema(MappingSchema):
        querystring = ListQuerystringSequence()

    foobaz = Service(name="foobaz", path="/foobaz")

    @foobaz.get(schema=QSSchema, validators=(colander_validator,))
    def foobaz_get(request):
        return {"field": request.validated['querystring']['field']}

    class NewsletterSchema(MappingSchema):
        email = SchemaNode(String(), validator=Email(), missing=drop)

    class RefererSchema(MappingSchema):
        ref = SchemaNode(Integer(), missing=drop)

    class NewsletterPayload(MappingSchema):
        body = NewsletterSchema()
        querystring = RefererSchema()

        def deserialize(self, cstruct=null):
            appstruct = super(NewsletterPayload, self).deserialize(cstruct)
            email = appstruct['body'].get('email')
            ref = appstruct['querystring'].get('ref')
            if email and ref and len(email) != ref:
                self.raise_invalid('Invalid email length')
            return appstruct

    email_service = Service(name='newsletter', path='/newsletter')

    @email_service.post(schema=NewsletterPayload,
                        validators=(colander_validator,))
    def newsletter(request):
        return request.validated


def includeme(config):
    config.include("cornice")
    config.scan("tests.validationapp")


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include(includeme)
    return CatchErrors(config.make_wsgi_app())
