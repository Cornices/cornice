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

You can register a filter for all the services by tweaking the `DEFAULT_FILTER`
parameter::

    from cornice.validators import DEFAULT_FILTERS

    def includeme(config):
        DEFAULT_FILTERS.append(your_callable)

(this also works for validators)

You also can add or remove filters and validators for a particular service. To
do that, you need to define its `default_validators` and `default_filters`
class parameters.

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

You can override the default JSON error handler for a view with your own
callable.  The following function, for instance, returns the error response
with an XML document as its payload:

.. code-block:: python

    def xml_error(errors):
        lines = ['<errors>']
        for error in errors:
            lines.append('<error>'
                        '<location>%(location)s</location>'
                        '<type>%(name)s</type>'
                        '<message>%(description)s</message>'
                        '</error>' % error)
        lines.append('</errors>')
        return HTTPBadRequest(body=''.join(lines),
                              content_type='application/xml')

Configure your views by passing your handler as ``error_handler``:

.. code-block:: python

    @service.post(validators=my_validator, error_handler=xml_error)
    def post(request):
        return {'OK': 1}


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
    from colander import MappingSchema, SchemaNode, String, drop


    foobar = Service(name="foobar", path="/foobar")


    class FooBarSchema(MappingSchema):
        # foo and bar are required in the body (json), baz is optional
        # yeah is required, but in the querystring.
        foo = SchemaNode(String(), location="body", type='str')
        bar = SchemaNode(String(), location="body", type='str')
        baz = SchemaNode(String(), location="body", type='str', missing=drop)
        yeah = SchemaNode(String(), location="querystring", type='str')


    @foobar.post(schema=FooBarSchema)
    def foobar_post(request):
        return {"test": "succeeded"}

You can even use Schema-Inheritance as introduced by Colander 0.9.9.

If you want the schema to be dynamic, i.e. you want to chose which one to use per request you can define it as a property on your class and it will be used instead. In this case, however, you must explitly bind it yourself. For example::

    @property
    def schema(self):
        if self.request.method == 'POST':
            schema = foo_schema
        elif self.request.method == 'PUT':
            schema = bar_schema
        schema = schema().bind(context=self.context, request=self.request)
        return CorniceSchema(schema.children)

Cornice provides built-in support for JSON and HTML forms
(``application/x-www-form-urlencoded``) input validation using Colander. If
you need to validate other input formats, such as XML, you can provide callable
objects taking a ``request`` argument and returning a Python data structure
that Colander can understand::

    def dummy_deserializer(request):
        return parse_my_input_format(request.body)


You can then instruct a specific view to use it with the ``deserializer``
parameter::

    @foobar.post(schema=FooBarSchema, deserializer=dummy_deserializer)
    def foobar_post(request):
        return {"test": "succeeded"}


If you'd like to configure deserialization globally, you can use the
``add_cornice_deserializer`` configuration directive in your app configuration
code to tell Cornice which deserializer to use for a given content
type::

    config = Configurator(settings={})
    # ...
    config.add_cornice_deserializer('text/dummy', dummy_deserializer)

With this configuration, when a request comes with a Content-Type header set to
``text/dummy``, Cornice will call ``dummy_deserializer`` on the ``request``
before passing the result to Colander.

View-specific deserializers have priority over global content-type
deserializers.


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

    @foo.get(validators=(validate,))
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

Changing the status code from validators
----------------------------------------

You also can change the status code returned from your validators. Here is an
example of this::

    def user_exists(request):
        if not request.POST['userid'] in userids:
            request.errors.add('body', 'userid', 'The user id does not exist')
            request.errors.status = 404

Doing validation and filtering at class level
---------------------------------------------

If you want to use class methods to do validation, you can do so by passing the
`klass` parameter to the `hook_view` or `@method` decorators, plus a string
representing the name of the method you want to invoke on validation.

Take care, though, because this only works if the class you are using has  an
`__init__` method which takes a `request` as the first argument.

This means something like this::

    class MyClass(object):
        def __init__(self, request):
            self.request = request

        def validate_it(request):
            # pseudo-code validation logic
            if whatever is wrong:
                request.errors.add('something')

    @service.get(klass=MyClass, validators=('validate_it',))
    def view(request):
        return "ok"


Content validation
==================

There are two flavors of content validations cornice can apply to services:

    - **Content-Type validation** will match the ``Content-Type`` header sent
      by the client against a list of allowed content types.
      When failing on that, it will croak with a ``415 Unsupported Media Type``.

    - **Content negotiation** checks if cornice is able to respond with the
      requested content type asked by the client sending an ``Accept`` header.
      Otherwise it will croak with a ``406 Not Acceptable``.


Content-Type validation
-----------------------

You can specify a list of allowed ingress content types using the
`content_type` argument to the decorator, like this::

    @service.post(content_type="application/json")
    def foo(request):
        return 'Foo'

In case the client sends a request with a disallowed header - e.g.
``Content-Type: application/x-www-form-urlencoded`` -
cornice will reject the request with a http status of
``415 Unsupported Media Type``.

Additionally, a list of valid content types is sent using the configured
`error_handler`. When using the default json `error_handler`, the response
might look like this::

    {
        'status': 'error',
        'errors': [
            {
                'location': 'header',
                'name': 'Content-Type',
                'description': 'Content-Type header should be one of ["application/json"]'
            }
        ]
    }


The `content_type` argument can either be a callable, a string or a list of
accepted values. When a callable is specified, it is called *before* the
request is passed to the destination function, with the `request` object as
an argument.

The callable should return a list of accepted content types::

    def _content_type(request):
        # interact with request if needed
        return ("text/xml", "application/json")

    @service.post(content_type=_content_type)
    def foo(request):
        return 'Foo'

The match is done against the plain internet media type string without
additional parameters like ``charset=utf-8`` or the like.

.. seealso::

    "Return the content type, but leaving off any parameters."

    -- http://docs.webob.org/en/latest/modules/webob.html#webob.request.BaseRequest.content_type


Content negotiation
-------------------

Cornice can automatically deal with egress content negotiation for you.
If you want it to, you have to pass the `accept` argument to the decorator,
like this::

    @service.get(accept="text/html")
    def foo(request):
        return 'Foo'

In case the client sends a request, asking for some particular content types
(using the HTTP **Accept** header), cornice will check that it is able to 
handle it.

If not, it will respond with a http status of ``406 Not Acceptable``. The body
is an error message containing the list of available response content types.

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

.. seealso:: https://developer.mozilla.org/en-US/docs/HTTP/Content_negotiation


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
