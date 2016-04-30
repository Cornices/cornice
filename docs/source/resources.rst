Defining resources
##################

Cornice is also able to handle rest "resources" for you. You can declare
a class with some put, post, get etc. methods (the HTTP verbs) and they will be
registered as handlers for the appropriate methods / services.

Here is how you can register a resource:

.. code:: python

    from cornice.resource import resource, view

    _USERS = {1: {'name': 'gawel'}, 2: {'name': 'tarek'}}

    @resource(collection_path='/users', path='/users/{id}')
    class User(object):

        def __init__(self, request):
            self.request = request

        def collection_get(self):
            return {'users': _USERS.keys()}

        @view(renderer='json')
        def get(self):
            return _USERS.get(int(self.request.matchdict['id']))

        @view(renderer='json', accept='text/json')
        def collection_post(self):
            print(self.request.json_body)
            _USERS[len(_USERS) + 1] = self.request.json_body
            return True

Here is an example of how to define cornice resources in an imperative way:

.. code:: python

    from cornice import resource

    class User(object):

        def __init__(self, request):
            self.request = request

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

validators and filters
======================

You also can register validators and filters that are defined in your
`@resource` decorated class, like this:

.. code:: python

    @resource(path='/users/{id}')
    class User(object):

        def __init__(self, request):
            self.request = request

        @view(validators=('validate_req',))
        def get(self):
            # return the list of users

        def validate_req(self, request):
            # validate the request

Registered routes
=================

Cornice uses a default convention for the names of the routes it registers.

When defining resources, the pattern used is `collection_<service_name>` (it
prepends ``collection_`` to the service name) for the collection service.
