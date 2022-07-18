Schema validation
#################

Validating requests data using a schema is a powerful pattern.

As you would do for a database table, you define some fields and
their type, and make sure that incoming requests comply.

There are many schema libraries in the Python ecosystem you can
use. The most known ones are Colander, Marshmallow & formencode.

You can do schema validation using either those libraries or either
custom code.

Using a schema is done in 2 steps:

1/ linking a schema to your service definition
2/ implement a validator that uses the schema to verify the request

Here's a dummy example:

.. code-block:: python

    def my_validator(request, **kwargs):
        schema = kwargs['schema']
        # do something with the schema

    schema = {'id': int, 'name': str}

    @service.post(schema=schema, validators=(my_validator,))
    def post(request):
        return {'OK': 1}


Cornice will call ``my_validator`` with the incoming request, and will
provide the schema in the keywords.



Using Colander
==============

Colander (http://docs.pylonsproject.org/projects/colander/en/latest/) is a
validation framework from the Pylons project that can be used with Cornice's
validation hook to control a request and deserialize its content into
objects.

Cornice provides a helper to ease Colander integration.

To describe a schema, using Colander and Cornice, here is how you can do:

.. code-block:: python

    import colander

    from cornice import Service
    from cornice.validators import colander_body_validator

    class SignupSchema(colander.MappingSchema):
        username = colander.SchemaNode(colander.String())

    @signup.post(schema=SignupSchema(), validators=(colander_body_validator,))
    def signup_post(request):
        username = request.validated['username']
        return {'success': True}

.. note::

    When you use one of ``colander_body_validator``, ``colander_headers_validator``,
    ``colander_querystring_validator`` etc. it is necessary to set schema which 
    inherits from :class:`colander.MappingSchema`. If you need to deserialize 
    :class:`colander.SequenceSchema` you need to use ``colander_validator`` instead.


Using Marshmallow
=================

Marshmallow (https://marshmallow.readthedocs.io/en/latest/)
is an ORM/ODM/framework-agnostic library for converting complex
datatypes, such as objects, to and from native Python datatypes that can also
be used with Cornice validation hooks.

Cornice provides a helper to ease Marshmallow integration.

To describe a schema, using Marshmallow and Cornice, here is how you can do:

.. code-block:: python

    import marshmallow

    from cornice import Service
    from cornice.validators import marshmallow_body_validator

    class SignupSchema(marshmallow.Schema):
        username = marshmallow.fields.String(required=True)

    @signup.post(schema=SignupSchema, validators=(marshmallow_body_validator,))
    def signup_post(request):
        username = request.validated['username']
        return {'success': True}

Dynamic schemas
~~~~~~~~~~~~~~~

If you want to do specific things with the schema at validation step,
like having a schema per request method, you can provide whatever
you want as the schema key and built a custom validator.

Example:

.. code-block:: python

    def dynamic_schema(request):
        if request.method == 'POST':
            schema = foo_schema()
        elif request.method == 'PUT':
            schema = bar_schema()
        return schema


    def my_validator(request, **kwargs):
        kwargs['schema'] = dynamic_schema(request)
        return colander_body_validator(request, **kwargs)


    @service.post(validators=(my_validator,))
    def post(request):
        return request.validated

In addition to ``colander_body_validator()`` as demonstrated above, there are also three more
similar validators, ``colander_headers_validator()``, ``colander_path_validator()``, and
``colander_querystring_validator()`` (and similarly named ``marshmallow_*``
functions), which validate the given ``Schema`` against the headers, path,
or querystring parameters, respectively.


Multiple request attributes
~~~~~~~~~~~~~~~~~~~~~~~~~~~


If you have complex use-cases where data has to be validated across several locations
of the request (like querystring, body etc.), Cornice provides a validator that
takes an additional level of mapping for ``body``, ``querystring``, ``path`` or ``headers``
instead of the former ``location`` attribute on schema fields.

The ``request.validated`` hences reflects this additional level.

.. code-block:: python

    # colander
    from cornice.validators import colander_validator

    class Querystring(colander.MappingSchema):
        referrer = colander.SchemaNode(colander.String(), missing=colander.drop)

    class Payload(colander.MappingSchema):
        username = colander.SchemaNode(colander.String())

    class SignupSchema(colander.MappingSchema):
        body = Payload()
        querystring = Querystring()

    signup = cornice.Service()

    @signup.post(schema=SignupSchema(), validators=(colander_validator,))
    def signup_post(request):
        username = request.validated['body']['username']
        referrer = request.validated['querystring']['referrer']
        return {'success': True}


    # marshmallow
    from cornice.validators import marshmallow_validator

    class Querystring(marshmallow.Schema):
        referrer = marshmallow.fields.String()

    class Payload(marshmallow.Schema):
        username = marshmallow.fields.String(validate=[
            marshmallow.validate.Length(min=3)
        ], required=True)

    class SignupSchema(marshmallow.Schema):
        body = marshmallow.fields.Nested(Payload)
        querystring = marshmallow.fields.Nested(Querystring)

    @signup.post(schema=SignupSchema, validators=(marshmallow_validator,))
    def signup_post(request):
        username = request.validated['body']['username']
        referrer = request.validated['querystring']['referrer']
        return {'success': True}

This allows to have validation at the schema level that validates data from several
places on the request:

.. code-block:: python

    # colander
    class SignupSchema(colander.MappingSchema):
        body = Payload()
        querystring = Querystring()

        def deserialize(self, cstruct=colander.null):
            appstruct = super(SignupSchema, self).deserialize(cstruct)
            username = appstruct['body']['username']
            referrer = appstruct['querystring'].get('referrer')
            if username == referrer:
                self.raise_invalid('Referrer cannot be the same as username')
            return appstruct


    # marshmallow
    class SignupSchema(marshmallow.Schema):
        body = marshmallow.fields.Nested(Payload)
        querystring = marshmallow.fields.Nested(Querystring)

        @marshmallow.validates_schema(skip_on_field_errors=True)
        def validate_multiple_fields(self, data):
            username = data['body'].get('username')
            referrer = data['querystring'].get('referrer')
            if username == referrer:
                raise marshmallow.ValidationError(
                    'Referrer cannot be the same as username')


Cornice provides built-in support for JSON and HTML forms
(``application/x-www-form-urlencoded``) input validation using the provided
validators.

If you need to validate other input formats, such as XML, you need to
implement your own deserializer and pass it to the service.

The general pattern in this case is:

.. code-block:: python

    from cornice.validators import colander_body_validator

    def my_deserializer(request):
        return extract_data_somehow(request)


    @service.post(schema=MySchema(),
                  deserializer=my_deserializer,
                  validators=(colander_body_validator,))
    def post(request):
        return {'OK': 1}


Marshmallow schemas have access to request as context object which can be handy
for things like CSRF validation:

.. code-block:: python

    class MNeedsContextSchema(marshmallow.Schema):
        somefield = marshmallow.fields.Float(missing=lambda: random.random())
        csrf_secret = marshmallow.fields.String()

        @marshmallow.validates_schema
        def validate_csrf_secret(self, data):
            # simulate validation of session variables
            if self.context['request'].get_csrf() != data.get('csrf_secret'):
                raise marshmallow.ValidationError('Wrong token')



Using formencode
================

FormEncode (http://www.formencode.org/en/latest/index.html) is yet another
validation system that can be used with Cornice.

For example, if you want to make sure the optional query option **max**
is an integer, and convert it, you can use FormEncode in a Cornice validator
like this:

.. code-block:: python

    from formencode import validators

    from cornice import Service
    from cornice.validators import extract_cstruct

    foo = Service(name='foo', path='/foo')

    def form_validator(request, **kwargs):
        data = extract_cstruct(request)
        validator = validators.Int()
        try:
            max = data['querystring'].get('max')
            request.validated['max'] = validator.to_python(max)
        except formencode.Invalid, e:
            request.errors.add('querystring', 'max', e.message)

    @foo.get(validators=(form_validator,))
    def get_value(request):
        """Returns the value.
        """
        return {'posted': request.validated}

See also
========

Several libraries exist in the wild to validate data in Python and that can easily
be plugged with Cornice.

* JSONSchema (https://pypi.python.org/pypi/jsonschema)
* Cerberus (https://pypi.python.org/pypi/Cerberus)
* marshmallow (https://pypi.python.org/pypi/marshmallow)
