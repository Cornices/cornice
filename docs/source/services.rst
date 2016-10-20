Defining services
#################

As mentioned in the :ref:`quickstart` and :ref:`tutorial`, services are defined
this way:

.. code-block:: python

    from cornice import Service

    flush = Service(name='flush',
                    description='Clear database content',
                    path='/__flush__')

    @flush.post()
    def flush_post(request):
        return {"Done": True}

See :class:`cornice.service.Service` for an exhaustive list of options.

Imperatively
============

Here is an example of how to define cornice services in an imperative way:

.. code-block:: python

    def flush_post(request):
        return {"Done": True}

    flush = Service(name='flush',
                    description='Clear database content',
                    path='/__flush__')

    flush.add_view("POST", flush_post, **kwargs):

    def includeme(config):
        config.add_cornice_service(flush)
        # or
        config.scan("PATH_TO_THIS_MODULE")

.. _service-cors:

CORS
====

When enabling CORS, Cornice will take automatically define ``OPTIONS`` views
and appropriate headers validation.

.. code-block:: python

    flush = Service(name='flush',
                    description='Clear database content',
                    path='/__flush__',
                    cors_origins=('*',),
                    cors_max_age=3600)

There are also a number of parameters that are related to the support of
CORS (Cross Origin Resource Sharing). You can read the CORS specification
at http://www.w3.org/TR/cors/ and see :class:`the exhaustive list of options in Cornice <cornice.service.Service>`.


Route factory support
=====================

When defining a service, you can provide a `route factory
<http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/urldispatch.html#route-factories>`_,
just like when defining a pyramid route.

For example::

    flush = Service(name='flush', path='/__flush__', factory=user_factory)
