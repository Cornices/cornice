Frequently Asked Questions (FAQ)
################################

Here is a list of frequently asked questions related to Cornice.

Cornice registers exception handlers, how do I deal with it?
============================================================

Cornice registers its own exception handlers so it's able to behave the right
way in some edge cases (it's mostly done for CORS support).

Sometimes, you will need to register your own exception handlers, and Cornice
might get on your way.

You can disable the exception handling by using the `handle_exceptions`
setting in your configuration file or in your main app:

.. code-block:: python

    config.add_settings(handle_exceptions=False)
