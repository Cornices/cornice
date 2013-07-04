Built-in features
#################

Here is a list of all the cornice built-in features. Cornice wants to provide
some tools so you don't mess up when making web services, so some of them are
activated by default.

If you need to add custom decorators to the list of default ones, or want to
disable some of them, please refer to :doc:`validation`.

Built-in filters
================

JSON XSRF filter
----------------

The `cornice.validators.filter_json_xsrf` filter checks out the views response,
looking for json objects returning lists.

It happens that json lists are subject to cross request forgery attacks (XSRF)
when returning lists (see http://wiki.pylonshq.com/display/pylonsfaq/Warnings), 
so cornice will drop a warning in case you're doing so.

Built-in validators
===================

Schema validation
-----------------

Cornice is able to do schema validation for you. It is able to use colander
schemas with some annotation in them. Here is an example of a validation
schema, taken from the cornice test suite::

    class FooBarSchema(MappingSchema):
        # foo and bar are required, baz is optional
        foo = SchemaNode(String(), type='str')
        bar = SchemaNode(String(), type='str', validator=validate_bar)
        baz = SchemaNode(String(), type='str', missing=None)
        yeah = SchemaNode(String(), location="querystring", type='str')
        ipsum = SchemaNode(Integer(), type='int', missing=1,
                           validator=Range(0, 3))
        integers = Integers(location="body", type='list', missing=())

    foobar = Service(name="foobar", path="/foobar")

    @foobar.post(schema=FooBarSchema)
    def foobar_post(request):
        return {"test": "succeeded"}

We are passing the schema as another argument (than the `validators` one)
so that cornice can do the heavy lifting for you. Another interesting thing to
notice is that we are passing a `location` argument which specifies where
cornice should look in the request for this argument.


Route factory support
=====================

When defining a service or a resource, you can provide a `route factory 
<http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/urldispatch.html#route-factories>`_,
just like when defining a pyramid route. Cornice will then pass its result
into the ``__init__`` of your service.

For example::

    @resource(path='/users', factory=user_factory)
    class User(object):

        def __init__(self, context, request):
            self.request = request
            self.user = context
