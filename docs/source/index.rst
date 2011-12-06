===================================
Welcome to Cornice's documentation!
===================================

**Cornice** provides helpers to build & document REST-ish Web Services
with Pyramid, with decent default behaviors.


A **full** Cornice WGSI application looks like this::


    from cornice import Service
    from pyramid.config import Configurator
    from pyramid.httpexceptions import HTTPNotFound


    user = Service('user', '/user/{id}', description='Users WS')

    def extract_user(request):
        try:
            request.validated['user'] = json.dumps(request.body)
        except ValueError:
            request.errors.add('body', description='Invalid record')

    _USERS = {}

    @user.get(accept='text/plan'):
    def get_user(request):
        """Returns the user"""
        uid = request.matchdict['id']
        if uid not in _USERS:
            raise HTTPNotFound(uid)
        return _USERS[uid]

    @user.post(validation=extract_user)
    def post_user(request):
        """Update the user"""
        user = request.validated['user']


    def main(global_config, **settings):
        config = Configurator(settings={})
        config.include("cornice")
        return config.make_wsgi_app()


What Cornice will do for you here is:

- automatically raise a 405 if a DELETE or a PUT is called on **/user/{id}**
- automatically generate your doc via a Sphinx directive.
- provide a validation framework that will return a nice JSON structure
  in Bad Request 400 responses explaining what's wrong.
- provide an acceptable content-type whenver you send an HTTP "accept" header 
  to it, resulting in a 406 NOT ACCEPTABLE with the list of acceptable ones
  if it can answer.


Documentation content
---------------------

.. toctree::
   :maxdepth: 2

   quickstart
   validation
   sphinx
   testing


Contribution & Feedback
-----------------------

Cornice is a project initiated at Mozilla Services, where we build Web 
Services for features like Firefox Sync.

We welcome Contributors and Feedback !

- Developers Mailing List: https://mail.mozilla.org/listinfo/services-dev
- Repository: https://github.com/mozilla-services/cornice
