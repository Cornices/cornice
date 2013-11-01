Defining resources
##################

Cornice is also able to handle rest "resources" for you. You can declare
a class with some put, post, get etc. methods (the HTTP verbs) and they will be
registered as handlers for the appropriate methods / services.

Here is how you can register a resource::

    from cornice.resource import resource, view
    

    @resource(collection_path='/users', path='/users/{id}')
    class User(object):

        def __init__(self, request):
            self.request = request

        def collection_get(self):
            return {'users': USERS.keys()}

        @view(renderer='json')
        def get(self):
            return USERS.get(int(self.request.matchdict['id']))

As you can see, you can define methods for the collection (it will use the
**path** argument of the class decorator. When defining collection_* methods, the 
path defined in the **collection_path** will be used.

validators and filters
======================

You also can register validators and filters that are defined in your
`@resource` decorated class, like this::

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
