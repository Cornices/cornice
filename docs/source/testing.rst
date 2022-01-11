Testing
=======

Running tests
-------------

To run all tests in all Python environments configured in ``tox.ini``,
just setup ``tox`` and run it inside the toplevel project directory::

    tox

To run a single test inside a specific Python environment, do e.g.::

    tox -e py39 tests/test_validation.py::TestServiceDefinition::test_content_type_missing


Testing cornice services
------------------------

Testing is nice and useful. Some folks even said it helped saving kittens. And
childs. Here is how you can test your Cornice's applications.

Let's suppose you have this service definition:

.. code-block:: python

    from pyramid.config import Configurator

    from cornice import Service

    service = Service(name="service", path="/service")


    def has_payed(request, **kwargs):
        if not 'paid' in request.GET:
            request.errors.add('body', 'paid', 'You must pay!')


    @service.get(validators=(has_payed,))
    def get1(request):
        return {"test": "succeeded"}


    def includeme(config):
        config.include("cornice")
        config.scan("absolute.path.to.this.service")


    def main(global_config, **settings):
        config = Configurator(settings={})
        config.include(includeme)
        return config.make_wsgi_app()


We have done three things here:

* setup a service, using the `Service` class and define our services with it
* register the app and cornice to pyramid in the `includeme` function
* define a `main` function to be used in tests

To test this service, we will use **webtest**, and the `TestApp` class:

.. code-block:: python

    from webtest import TestApp
    import unittest

    from yourapp import main

    class TestYourApp(unittest.TestCase):

        def test_case(self):
            app = TestApp(main({}))
            app.get('/service', status=400)
