Upgrading
#########

1.X to 2.X
==========

Validators
----------

Validators now receive the kwargs of the related service definition.

Before:

.. code-block:: python

    def has_payed(request):
        if 'paid' not in request.GET:
            request.errors.add('body', 'paid', 'You must pay!')

After:

.. code-block:: python

    def has_payed(request, **kwargs):
        free_access = kwargs.get('free_access')
        if not free_access and 'paid' not in request.GET:
            request.errors.add('body', 'paid', 'You must pay!')


Colander validation
-------------------

Colander schema validation now requires an explicit validator, and an additional
level of mapping for ``body``, ``querystring`` or ``headers`` instead of the former
``location`` attribute. The ``request.validated`` hences reflects this additional level.

Before:

.. code-block:: python

    class SignupSchema(colander.MappingSchema):
        username = colander.SchemaNode(colander.String(), location='body')
        referrer = colander.SchemaNode(colander.String(), location='querystring',
                                       missing=colander.drop)

    @signup.get(schema=SignupSchema)
    def signup_get(request):
        username = request.validated['username']
        referrer = request.validated['referrer']
        return {'success': True}

After:

.. code-block:: python

    from cornice.validators import colander_validator

    class Querystring(colander.MappingSchema):
        referrer = colander.SchemaNode(colander.String(), missing=colander.drop)

    class Payload(colander.MappingSchema):
        username = colander.SchemaNode(colander.String())

    class SignupSchema(colander.MappingSchema):
        body = Payload()
        querystring = Querystring()

    signup = cornice.Service()

    @signup.get(schema=SignupSchema, validators=(colander_validator,))
    def signup_get(request):
        username = request.validated['body']['username']
        referrer = request.validated['querystring']['referrer']
        return {'success': True}


Error handler
-------------

* The ``error_handler`` callback of services now receives a ``request`` object instead of ``errors``.

Before:

.. code-block:: python

    def xml_error(errors):
        request = errors.request
        ...

After:

.. code-block:: python

    def xml_error(request):
        errors = request.errors
        ...


Deserializers
-------------

The support of ``config.add_deserializer()`` and ``config.registry.cornice_deserializers``
was dropped.


Services schemas introspection
------------------------------

The ``schema`` argument of services is now treated as service kwarg.
The ``service.schemas_for()`` method was dropped as well as the ``service.schemas``
property.

Before:

.. code-block:: python

    schema = service.schemas_for(method="POST")

After:

.. code-block:: python

    schema = [kwargs['schema'] for method, view, kwargs in service.definitions
              if method == "POST"][0]

