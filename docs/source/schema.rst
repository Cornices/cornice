Schema validation
#################

Validating requests data using a schema is a powerful pattern.

As you would do for a database table, you define some fields and
their type, and make sure that incoming requests comply.

There are many schema libraries in the Python ecosystem you can
use. The most known ones are Colander & formencode.

You can do schema validation using either those libraries or either
custom code.

Using a schema is done in 2 steps:

1/ linking a schema to your service definition
2/ implement a validator that uses the schema to verify the request

Here's a dummy example:

.. code-block:: python


    def my_validator(request, \*\*kw):
        schema = kw['schema']
        # do something with the schema


    schema = {'id': int, 'name': str}


    @service.post(validators=my_validator, schema=schema)
    def post(request):
        return {'OK': 1}


Cornice will call ``my_validator`` with the incoming request, and will
provide the schema in the keywords.



Using Colander
~~~~~~~~~~~~~~

Colander (http://docs.pylonsproject.org/projects/colander/en/latest/) is a
validation framework from the Pylons project that can be used with Cornice's
validation hook to control a request and deserialize its content into
objects.

Cornice provides a helper to ease Colander integration.

To describe a schema, using Colander and Cornice, here is how you can do::

    from cornice import Service
    from cornice.validators import colander_validator
    from colander import MappingSchema, SchemaNode, String, drop


    foobar = Service(name="foobar", path="/foobar")


    class FooBarSchema(MappingSchema):
        # foo and bar are required in the body (json), baz is optional
        # yeah is required, but in the querystring.
        foo = SchemaNode(String(), location="body", type='str')
        bar = SchemaNode(String(), location="body", type='str')
        baz = SchemaNode(String(), location="body", type='str', missing=drop)
        yeah = SchemaNode(String(), location="querystring", type='str')


    @foobar.post(schema=FooBarSchema, validator=colander_validator)
    def foobar_post(request):
        return {"test": "succeeded"}

You can even use Schema-Inheritance as introduced by Colander 0.9.9.


If you want to do specific things with the schema at validation step,
like having a schema per request method, you can provide whatever
you want as the schema key and built a custom validator.

Example::


    def dynamic_schema(request):
        if request.method == 'POST':
            schema = foo_schema
        elif request.method == 'PUT':
            schema = bar_schema
        return schema


    def my_validator(request, **kw):
        kw['schema'] = dynamic_schema(request)
        return colander_validator(request, **kw)


    @service.post(validators=my_validator, schema=schema)
    def post(request):
        return {'OK': 1}


Cornice provides built-in support for JSON and HTML forms
(``application/x-www-form-urlencoded``) input validation using
``colander_validator``.

If you need to validate other input formats, such as XML, you need to
implement your own deserializer and pass it to the service.

The general pattern in this case is::


    from cornice.validators import colander_validator

    def my_deserializer(request):
        return extract_data_somehow(request)


    @service.post(validators=my_validator, schema=MySchema,
                  deserializer=my_deserializer)
    def post(request):
        return {'OK': 1}


Using formencode
~~~~~~~~~~~~~~~~

FormEncode (http://www.formencode.org/en/latest/index.html) is yet another
validation system that can be used with Cornice.

For example, if you want to make sure the optional query option **max**
is an integer, and convert it, you can use FormEncode in a Cornice validator
like this::


    from cornice import Service
    from formencode import validators

    foo = Service(name='foo', path='/foo')
    validator = validators.Int()

    def validate(request, **kw):
        try:
            request.validated['max'] = validator.to_python(request.GET['max'])
        except formencode.Invalid, e:
            request.errors.add('url', 'max', e.message)

    @foo.get(validators=(validate,))
    def get_value(request):
        """Returns the value.
        """
        return 'Hello'


