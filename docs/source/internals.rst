Cornice internals
#################

Internally, Cornice doesn't do a lot of magic. The logic is mainly split in two
different locations: the `services.py` module and the `pyramid_hook.py` module.

That's important to understand what they are doing in order to add new features
or tweak the existing ones.

The Service class
=================

The :class:`cornice.service.Service` class is a container for all the definition
information for a particular service. That's what you use when you use the
Cornice decorators for instance, by doing things like
``@myservice.get(**kwargs)``. Under the hood, all the information you're passing
to the service is stored in this class. Into other things you will find there:

- the `name` of the registered service.
- the `path` the service is available at.
- the `description` of the service, if any.
- the `defined_methods` for the current service. This is a list of strings. It
  shouldn't contain more than one time the same item.

That's for the basic things. The last interesting part is what we call the
"definitions". When you add a view to the service with the `add_view` method,
it populates the definitions list, like this:

.. code-block:: python

    self.definitions.append((method, view, args))

where `method` is the HTTP verb, `view` is the python callable and `args` are
the arguments that are registered with this definition. It doesn't look this
important, but this last argument is actually the most important one. It is a
python dict containing the filters, validators, content types etc.

There is one thing I didn't talk about yet: how we are getting the arguments
from the service class. There is a handy `get_arguments` method, which returns
the arguments from another list of given arguments. The goal is to fallback on
instance-level arguments or class-level arguments if no arguments are provided
at the add_view level. For instance, let's say I have a default service which
renders to XML. I set its renderer in the class to "XML".

When I register the information with :meth:`cornice.service.Service.add_view()`,
``renderer='XML'`` will be added automatically in the kwargs dict.

Registering the definitions into the Pyramid routing system
===========================================================

Okay, so once you added the services definition using the Service class, you
might need to actually register the right routes into pyramid. The
:mod:`cornice.pyramidhook` module takes care of this for you.

What it does is that it checks all the services registered and call some
functions of the pyramid framework on your behalf.

What's interesting here is that this mechanism is not really tied to pyramid.
for instance, we are doing the same thing `in cornice_sphinx <https://github.com/Cornices/cornice.ext.sphinx>`_
to generate the documentation: use the APIs that are exposed in the Service class
and do something from it.

To keep close to the flexibility of Pyramid's routing system, a ``traverse``
argument can be provided on service creation. It will be passed to the route
declaration. This way you can combine URL Dispatch and traversal to build an
hybrid application.
