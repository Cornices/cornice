Cornice: A REST framework for Pyramid
#####################################

**Cornice** provides helpers to build & document REST-ish Web Services
with Pyramid, with decent default behaviors. It takes care of following the
HTTP specification in an automated way where possible.

We designed and implemented cornice in a really simple way, so
it is easy to use and you can get started in a matter of minutes.

Show me some code!
==================

A **full** Cornice WGSI application looks like this (this example is taken from
the `demoapp project <https://github.com/mozilla-services/demoapp>`_)::

    from collections import defaultdict

    from pyramid.exceptions import Forbidden
    from pyramid.security import authenticated_userid, effective_principals
    from pyramid.view import view_config

    from cornice import Service


    info_desc = """\
    This service is useful to get and set data for a user.
    """


    user_info = Service(name='users', path='/{username}/info',
                        description=info_desc)

    _USERS = defaultdict(dict)


    @user_info.get()
    def get_info(request):
        """Returns the public information about a **user**.

        If the user does not exists, returns an empty dataset.
        """
        username = request.matchdict['username']
        return _USERS[username]


    @user_info.post()
    def set_info(request):
        """Set the public information for a **user**.

        You have to be that user, and *authenticated*.

        Returns *True* or *False*.
        """
        username = authenticated_userid(request)
        if request.matchdict["username"] != username:
            raise Forbidden()
        _USERS[username] = request.json_body
        return {'success': True}


    @view_config(route_name="whoami", permission="authenticated", renderer="json")
    def whoami(request):
        """View returning the authenticated user's credentials."""
        username = authenticated_userid(request)
        principals = effective_principals(request)
        return {"username": username, "principals": principals}

What Cornice will do for you here is:

- automatically raise a 405 if a DELETE or a PUT is called on
  **/{username}/info**
- automatically generate your doc via a Sphinx directive.
- provide a validation framework that will return a nice JSON structure
  in Bad Request 400 responses explaining what's wrong.
- provide an acceptable **Content-Type** whenever you send an HTTP "Accept"
  header
  to it, resulting in a *406 Not Acceptable* with the list of acceptable ones
  if it can't answer.

You can also have a complete overview of the builtin validations provided by
cornice in :doc:`builtin-features`


Documentation content
=====================

.. toctree::
   :maxdepth: 2

   quickstart
   tutorial
   config
   resources
   validation
   builtin_validation
   sphinx
   testing
   exhaustive_list
   exampledoc
   api
   internals
   spore
   faq


Contribution & Feedback
=======================

Cornice is a project initiated at Mozilla Services, where we build Web
Services for features like Firefox Sync. All of what we do is built with open
source, and this is one brick of our stack.

We welcome Contributors and Feedback!

- Developers Mailing List: https://mail.mozilla.org/listinfo/services-dev
- Repository: https://github.com/mozilla-services/cornice
