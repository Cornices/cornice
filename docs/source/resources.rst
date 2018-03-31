Defining resources
##################

Cornice is also able to handle REST "resources" for you. You can declare
a class with some put, post, get etc. methods (the HTTP verbs) and they will be
registered as handlers for the appropriate methods / services.

Here is how you can register a resource:

.. code-block:: python

    from cornice.resource import resource

    _USERS = {1: {'name': 'gawel'}, 2: {'name': 'tarek'}}

    @resource(collection_path='/users', path='/users/{id}')
    class User(object):

        def __init__(self, request, context=None):
            self.request = request

        def __acl__(self):
            return [(Allow, Everyone, 'everything')]

        def collection_get(self):
            return {'users': _USERS.keys()}

        def get(self):
            return _USERS.get(int(self.request.matchdict['id']))

        def collection_post(self):
            print(self.request.json_body)
            _USERS[len(_USERS) + 1] = self.request.json_body
            return True

Imperatively
============

Here is an example of how to define cornice resources in an imperative way:

.. code-block:: python

    from cornice import resource

    class User(object):

        def __init__(self, request, context=None):
            self.request = request

        def __acl__(self):
            return [(Allow, Everyone, 'everything')]

        def collection_get(self):
            return {'users': _USERS.keys()}

        def get(self):
            return _USERS.get(int(self.request.matchdict['id']))

    resource.add_view(User.get, renderer='json')
    user_resource = resource.add_resource(User, collection_path='/users', path='/users/{id}')

    def includeme(config):
        config.add_cornice_resource(user_resource)
        # or
        config.scan("PATH_TO_THIS_MODULE")

As you can see, you can define methods for the collection (it will use the
**path** argument of the class decorator. When defining collection_* methods, the
path defined in the **collection_path** will be used.

Here is an example how to reuse existing pyramid routes instead of registering
new ones:

.. code-block:: python

   @resource(collection_pyramid_route='users', pyramid_route='user')
   class User(object):
       ....

Validators and filters
======================

You also can register validators and filters that are defined in your
`@resource` decorated class, like this:

.. code-block:: python

    from cornice.resource import resource, view

    @resource(path='/users/{id}')
    class User(object):

        def __init__(self, request, context=None):
            self.request = request

        def __acl__(self):
            return [(Allow, Everyone, 'everything')]

        @view(validators=('validate_req',))
        def get(self):
            # return the list of users

        def validate_req(self, request):
            # validate the request


Registered routes
=================

Cornice uses a default convention for the names of the routes it registers.

When defining resources, the pattern used is ``collection_<service_name>`` (it
prepends ``collection_`` to the service name) for the collection service.


Route factory support
=====================

When defining a resource, you can provide a `route factory
<http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/urldispatch.html#route-factories>`_,
just like when defining a pyramid route. Cornice will then pass its result
into the ``__init__`` of your service.

For example::

    @resource(path='/users', factory=user_factory)
    class User(object):

        def __init__(self, request, context=None):
            self.request = request
            self.user = context

When no `factory` is defined, the decorated class becomes the `route factory
<http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/urldispatch.html#route-factories>`_.
One advantage is that pyramid ACL authorization can be used out of the box: `Resource with ACL
<https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/security.html#assigning-acls-to-your-resource-objects>`_.

For example::

    @resource(path='/users')
    class User(object):

        def __init__(self, request, context=None):
            self.request = request
            self.user = context

        def __acl__(self):
            return [(Allow, Everyone, 'view')]
