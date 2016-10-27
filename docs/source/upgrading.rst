Upgrading
#########

1.X to 2.X
==========

Project template
----------------

We now rely on `Cookiecutter <https://cookiecutter.readthedocs.io>`_ instead of
the deprecated Pyramid scaffolding feature::

    $ cookiecutter gh:Cornices/cookiecutter-cornice

Sphinx documentation
--------------------

The Sphinx extension now lives in a separate package, that must be installed::

    pip install cornice_sphinx

Before in your :file:`docs/conf.py`:

.. code-block: python

    import cornice

    sys.path.insert(0, os.path.abspath(cornice.__file__))
    extensions = ['cornice.ext.sphinxext']

Now:

.. code-block: python

    import cornice_sphinx

    sys.path.insert(0, os.path.abspath(cornice_sphinx.__file__))
    extensions = ['cornice_sphinx']


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

    @signup.post(schema=SignupSchema)
    def signup_post(request):
        username = request.validated['username']
        return {'success': True}

Now:

.. code-block:: python

    from cornice.validators import colander_body_validator

    class SignupSchema(colander.MappingSchema):
        username = colander.SchemaNode(colander.String())

    @signup.post(schema=SignupSchema(), validators=(colander_body_validator,))
    def signup_postt(request):
        username = request.validated['username']
        return {'success': True}

This makes declarations a bit more verbose, but decorrelates Cornice from Colander.
Now any validation library can be used.

.. important::

    Some of the validation messages may have changed from version 1.2.
    For example ``Invalid escape sequence`` becomes ``Invalid \\uXXXX escape``.


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

    @signup.post(schema=SignupSchema)
    def signup_post(request):
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

    @signup.post(schema=SignupSchema(), validators=(colander_validator,))
    def signup_post(request):
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

Deserializers are still defined via the same API:

.. code-block:: python

    def dummy_deserializer(request):
        if request.headers.get("Content-Type") == "text/dummy":
            values = request.body.decode().split(',')
            return dict(zip(['foo', 'bar', 'yeah'], values))
        request.errors.add(location='body', description='Unsupported content')

    @myservice.post(schema=FooBarSchema(),
                    deserializer=dummy_deserializer,
                    validators=(my_validator,))

But now, instead of using the application registry, the ``deserializer`` is
accessed via the validator kwargs:

.. code-block:: python

    from cornice.validators import extract_cstruct

    def my_validator(request, deserializer=None, **kwargs):
        if deserializer is None:
            deserializer = extract_cstruct
        data = deserializer(request)
        ...

.. note::

    The built-in ``colander_validator`` supports custom deserializers and defaults
    to the built-in JSON deserializer ``cornice.validators.extract_cstruct``.

.. note::

    The attributes ``registry.cornice_deserializers`` and ``request.deserializer``
    are not set anymore.


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
