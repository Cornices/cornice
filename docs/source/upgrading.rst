Upgrading
#########

1.X to 2.X
==========

Project template
----------------

We now rely on `Cookiecutter <https://cookiecutter.readthedocs.io>`_ instead of
the deprecated Pyramid scaffolding feature::

    $ cookiecutter gh:Cornices/cookiecutter-cornice

Validators
----------

Validators now receive the kwargs of the related service definition.

Before:

.. code-block:: python

    def has_payed(request):
        if 'paid' not in request.GET:
            request.errors.add('body', 'paid', 'You must pay!')

Now:

.. code-block:: python

    def has_payed(request, **kwargs):
        free_access = kwargs.get('free_access')
        if not free_access and 'paid' not in request.GET:
            request.errors.add('body', 'paid', 'You must pay!')


Colander validation
-------------------

Colander schema validation now requires an explicit validator on the service
view definition.

Before:

.. code-block:: python

    class SignupSchema(colander.MappingSchema):
        username = colander.SchemaNode(colander.String())

    @signup.get(schema=SignupSchema)
    def signup_get(request):
        username = request.validated['username']
        return {'success': True}

Now:

.. code-block:: python

    from cornice.validators import colander_body_validator

    class SignupSchema(colander.MappingSchema):
        username = colander.SchemaNode(colander.String())

    @signup.get(schema=SignupSchema, validators=(colander_body_validator,))
    def signup_get(request):
        username = request.validated['username']
        return {'success': True}

This makes declarations a bit more verbose, but decorrelates Cornice from Colander.
Now any validation library can be used.


Complex Colander validation
---------------------------

If you have complex use-cases where data has to be validated accross several locations
of the request (like querystring, body etc.), Cornice provides a validator that
takes an additionnal level of mapping for ``body``, ``querystring``, ``path`` or ``headers``
instead of the former ``location`` attribute on schema fields.

The ``request.validated`` hences reflects this additional level.

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

Now:

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

This now allows to have validation at the schema level that validates data from several
locations:

.. code-block:: python

    class SignupSchema(colander.MappingSchema):
        body = Payload()
        querystring = Querystring()

        def deserialize(self, cstruct=colander.null):
            appstruct = super(SignupSchema, self).deserialize(cstruct)
            username = appstruct['body']['username']
            referrer = appstruct['querystring'].get('referrer')
            if username == referred:
                self.raise_invalid('Referrer cannot be the same as username')
            return appstruct


Error handler
-------------

* The ``error_handler`` callback of services now receives a ``request`` object instead of ``errors``.

Before:

.. code-block:: python

    def xml_error(errors):
        request = errors.request
        ...

Now:

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

Now:

.. code-block:: python

    schema = [kwargs['schema'] for method, view, kwargs in service.definitions
              if method == "POST"][0]
