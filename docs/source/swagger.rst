Overview
========

To create a full swagger spec, this module will maximize extracting
documentation data from functional code, while allowing users to
directly specify parts of the Swagger Spec. This documentation serves as
a "how-to". Readers are encouraged to look at the source for more
detailed documentation if needed.

This module creates a `Swagger 2.0 compliant spec`_.

Throughout this documentation, ``code-styled text`` indicates a sort of
"proper noun" matching the official names used in related documentation
(Swagger Spec, Cornice, Pyramid, Colander).

**Outline**

1. Docstrings
2. Swagger Module
3. Converters

   1. Colander for input parameters

4. Scaffold

Description Docstrings
======================

-  ``cornice.@resource()``-decorated classes in your view file should
   have docstrings (triple-quoted strings immediately after your class
   declaration)

   -  This docstring becomes the description for the respective endpoint
      group.
   -  Each endpoint group is a collection of Swagger Paths which start
      with the same URL base (the text between the first two ``/``
      characters in your URL after the true URL base).

-  ``cornice.@view()``-decorated methods with your decorated Cornice
   Resource classes should have docstrings to document the individual
   HTTP method descriptions

*Note* The Swagger UI groups together endpoints which share the same
``tag``. The swagger module auto-tags all endpoints based on their path
beginning. Technically, a Swagger Spec stores a ``basePath`` in the
`root document object`_. However, as a well-formed REST URI begins with
a RESTful object with which to be interacted, this object (between the
first slashes) will be used to tag similar paths into a group.

*Warning* ﻿If you implement multiple ``@resource``-decorated classes
beginning with the same first URL segment in the ``path`` argument, it
may become ambiguous which docstring will be displayed in Swagger UI.
Only put a docstring on one such class to remove ambiguity.

Swagger Module
==============

``swagger.py`` uses
``generate_swagger_spec(services, title, version, **kwargs)`` to make
the actual Swagger Spec JSON. The arguments are:

.. _Swagger 2.0 compliant spec: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md
.. _root document object: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#fixed-fields
1. ``services`` - a list of Pyramid Services. Note that Cornice
   Resources are really Services under the hood.
2. ``title`` and ``version`` are both required Swagger Spec details for
   the `Info Object`_.
3. ``kwargs`` can be made of anything else which would go into the base
   `Swagger Object`_.

*Note* If you want to add to the ``Info Object``, simply pass in as an
``info`` argument with the additional details. The ``Info Object``
populated by the ``title`` and ``version`` args provided earlier will
simply be updated.

An example of a Pyramid Service which itself scans other Cornice
Resources and Services to generate a ``swagger.json`` Spec:

.. code:: python

    from pyramid.view import view_config
    from cornice import service
    from swagger import generate_swagger_spec
    # This OrderedDict import is for Extra Credit below
    from collections import OrderedDict

    @view_config(route_name='swagger_json', renderer='json')
    def swagger_json(request):
        info = {'title': 'Joes API', 'version': '0.1', 'contact': {
                'name': 'Joe Smith',
                'email': 'joe.cool@swagger.com'}
                }

        # Pretend our API is served on our host with a prefix, such as
        # an API version number or a username
        base_path = '/jcool'
        security_definition = {
            "authId": {
                "type": "apiKey",
                "name": "ID-Token",
                "in": "header"
            }
        }

        # Get our list of services
        services = service.get_services()
        swagger_spec = generate_swagger_spec(services, info['title'], info['version'],
                                             info=info, basePath=base_path)

        # Extra Credit: We want to put paths in a special order with /cool
        # endpoints first, and OrderedPaths act just like a dict as far ase
        # the JSON parser is concerned.
        paths_dict = swagger_spec['paths']
        ordered_paths = OrderedDict()
        first_items = ['/tokens', '/tokens/{authId}']
        for item in first_items:
            ordered_paths[item] = paths_dict[item]
        # Now add all the other paths
        ordered_paths.update(sorted(paths_dict.items(), key=lambda t: t[0]))
        # Replace our paths with the ordered ones
        swagger_spec['paths'] = ordered_paths
        return swagger_spec


Converters
----------

Ideally, we’d maximaize how much documentation comes from functional code. As
we’re already using Cornice, we can leverage its operators internally to
``generate_swagger_spec()``. This only gets us so far, and currently only
leverages the ``@resource`` decorator as it identifies services and provides
some path info from which to gleen ``path`` parameters and a description. For
example, this code...

.. code:: python

    class FooSchema(colander.MappingSchema):
        username = colander.SchemaNode(colander.String(), location="header")
        password = SchemaNode(colander.Password(), location="header")

    @resource(collection_path='/tokens', path='/tokens/{authId}',
              description='quick token description')
    class Token(object):
        """Authenticate by POSTing here"""
        def __init__(self, request):
            self.request = request

        @view(schema=FooSchema)
        def collection_post(self):
            """Get authKey here and use as X-Identity-Token for future calls"""
            ...
        def delete(self):
            """Log out of system by deleting a token from your previous authId"""
            ...

Colander
~~~~~~~~

Since Cornice recommends Colander for validation, there are some handy
converters to convert Colander ``Schemas Nodes`` to Swagger ``Parameter
Objects``.

If you have defined Cornice ``Schema`` objects (comprised of ``Schema Nodes``),
you can pass it to ``schema_to_parameters`` which then converts the ``Schema``
to a list of ``Swagger Parameters``. Since ``Schema Nodes`` take in a Colander
type as an argument (``Tuple``, ``Boolean``, etc) the Swagger ``Parameter
Object`` "type" can be derived. This function is used by
``generate_swagger_spec`` to scan for Colander Schmas being decorated onto an
``Operation`` with the Cornice ``@view(schema=MyCoolSchema`` decorator, and the
create ``Parameter Objects``

Scaffold
--------

There is a swagger scaffold to get startet.

::

   $ pcreate -t cornice_swagger swagger_demo
   $ cd swagger_demo
   $ pip install -e .
   $ cd swagger_demo/static
   $ bower install
