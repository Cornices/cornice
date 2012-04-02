Built-in features
#################

Here is a list of all the cornice built-in features. Cornice wants to provide
some tools so you don't mess up when making web services, so some of them are
activated by default.

If you need to add custom decorators to the list of default ones, or want to
disable some of them, please refer to :doc:`validation`.

Built-in filters
================

JSON XSRF filter
----------------

The `cornice.validators.filter_json_xsrf` filter checks out the views response,
looking for json objects returning lists.

It happens that json lists are subject to cross request forgery attacks (XSRF)
when returning lists (see http://wiki.pylonshq.com/display/pylonsfaq/Warnings), 
so cornice will drop a warning in case you're doing so.

Built-in validators
===================

XXX
