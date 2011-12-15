===================================
Welcome to Cornice's documentation!
===================================

**Cornice** provides helpers to build & document REST-ish Web Services
with Pyramid, with decent default behaviors.


Documentation content
---------------------

.. toctree::
   :maxdepth: 1

   quickstart
   tutorial
   validation
   sphinx
   testing
   exampledoc


Show me some code !
-------------------

A **full** Cornice WGSI application looks like this (this example is taken from
the `demoapp project <https://github.com/mozilla-services/demoapp>`_)

.. literalinclude:: /../../examples/demoapp/demoapp/views.py


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


Contribution & Feedback
-----------------------

Cornice is a project initiated at Mozilla Services, where we build Web 
Services for features like Firefox Sync.

We welcome Contributors and Feedback !

- Developers Mailing List: https://mail.mozilla.org/listinfo/services-dev
- Repository: https://github.com/mozilla-services/cornice
