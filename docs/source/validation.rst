Validation features
###################

Cornice provides a way to to control the request before it's passed to the
code. A validator is a simple callable that gets the request object and fills
**request.errors** in case the request has some errors.

Validators can also convert values and saves them so they can be reused
by the code. This is done by filling the **request.validated** dictionary.

Once the request had been sent to the view, you can filter the results using so
called filters. This document describe both concepts, and how to deal with
them.

Disabling or adding filters/validators
======================================

Some validators and filters are activated by default, for all the services. In
case you want to disable them, or if you 

You can register a filter for all the services::

    from cornice.validators import DEFAULT_FILTERS

    def includeme(config):
        DEFAULT_FILTERS.append(your_callable)

The example above works as well for validators.

Dealing with errors
===================

When validating inputs using the different validation mechanisms (described in
this document),  Cornice can return errors. In case it returns errors, it will
do so in JSON by default.

The default returned JSON object is a dictionary of the following form::

    {
        'status': 'error',
        'errors': errors.
    }

With errors being a JSON dictionary with the keys "location", "name" and
"description".

* **location** is the location of the error. It can be "querystring", "header"
  or "body"
* **name** is the eventual name of the value that caused problems
* **description** is a description of the problem encountered.


Validators
==========

Schema validation
-----------------

You can do schema validation using either libraries or custom code. However, 
cornice integrates better when using Colander for instance, and will be able
to generate the documentation and describe the variables needed if you use it.

Using Colander
~~~~~~~~~~~~~~

Colander (http://docs.pylonsproject.org/projects/colander/en/latest/) is a
validation framework from the Pylons project that can be used with Cornice's
validation hook to control a request and deserialize its content into
objects.

To describe a schema, using colander and cornice, here is how you can do::

    from cornice import Service
    from cornice.schemas import CorniceSchema
    from colander import MappingSchema, SchemaNode, String


    foobar = Service(name="foobar", path="/foobar")


    class FooBarSchema(MappingSchema):
        # foo and bar are required in the body (json), baz is optional
        # yeah is required, but in the querystring.
        foo = SchemaNode(String(), location="body", type='str')
        bar = SchemaNode(String(), location="body", type='str')
        baz = SchemaNode(String(), location="body", type='str', required=False)
        yeah = SchemaNode(String(), location="querystring", type='str')


    @foobar.post(schema=FooBarSchema)
    def foobar_post(request):
        return {"test": "succeeded"}

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

    def validate(request):
        try:
            request.validated['max'] = validator.to_python(request.GET['max'])
        except formencode.Invalid, e:
            request.errors.add('url', 'max', e.message)

    @foo.get(validators=validate)
    def get_value(request):
        """Returns the value.
        """
        return 'Hello'


Validation using custom callables
---------------------------------

Let's take an example: we want to make sure the incoming request has an
**X-Verified** header. If not, we want the server to return a 400::


    from cornice import Service

    foo = Service(name='foo', path='/foo')


    def has_paid(request):
        if not 'X-Verified' in request.headers:
            request.errors.add('header', 'X-Verified', 'You need to provied a token')


    @foo.get(validators=has_paid)
    def get_value(request):
        """Returns the value.
        """
        return 'Hello'


Notice that you can chain the validators by passing a sequence
to the **validators** option.

In any case, when doing validation, cornice will try to extract information
coming from the validation functions you are providing to put them in the
generated documentation. Refer to :doc:`sphinx` for more information about
documentation automatic generation.


Content-Type validation
=======================

Cornice can automatically deal with content type validation for you.
If you want it to, you have to pass the `accept` argument to the decorator,
like this::

    @service.get(accept="text/html")
    def foo(request):
        return 'Foo'

In case the client sends a request, asking for some particular content types
(using the HTTP **Accept** header), cornice will check that it is able to 
handle it.

If not, it will return a 406 HTTP code, with the list of accepted
content types.

The `accept` argument can either be a callable, a string or a list of accepted
values. When a callable is specified, it is called *before* the request is
passed to the destination function, with the `request` object as an argument.

The callable should return a list of accepted content types::

    def _accept(request):
        # interact with request if needed
        return ("text/xml", "text/json")

    @service.get(accept=_accept)
    def foo(request):
        return 'Foo'

Managing ACLs
=============

You can also specify a way to deal with ACLs: pass in a function that takes 
a request and returns an ACL, and that ACL will be applied to all views 
in the service::

    foo = Service(name='foo', path='/foo', acl=_check_acls)


Filters
=======

Cornice can also filter the response returned by your views. This can be
useful if you want to add some behaviour once a response has been issued.

Here is how to define a validator for a service::

    foo = Service(name='foo', path='/foo', filters=your_callable)

You can just add the filter for a specific method::

    @foo.get(filters=your_callable)
    def foo_get(request):
        """some description of the validator for documentation reasons"""
        pass

In case you would like to register a filter for all the services but one, you
can use the `exclude` parameter. It works either on services or on methods::

    @foo.get(exclude=your_callable)
