Testing
=======

Testing is nice and useful. Some folks even said it helped saving kittens. And
childs.  Here is how you can test your cornices applications.

Let's suppose you have this service definition::

    
    from pyramid.config import Configurator

    from cornice import Service
    from cornice.tests.support import CatchErrors

    service = Service(name="service", path="/service")


    def has_payed(request):
        if not 'paid' in request.GET:
            request.errors.add('body', 'paid', 'You must pay!')


    @service.get(validator=has_payed)
    def get1(request):
        return {"test": "succeeded"}


    def includeme(config):
        config.include("cornice")
        config.scan("absolute.path.to.this.service")


    def main(global_config, **settings):
        config = Configurator(settings={})
        config.include(includeme)
        return CatchErrors(config.make_wsgi_app())


We have done three things here:

* setup a service, using the `Service` class and define our services with it
* register the app and cornice to pyramid in the `includeme` function
* define a `main` function to be used in tests

To test this service, we will use **webtest**, and the `TestApp` class::

    from webtest import TestApp
    import unittest

    from yourapp import main

    class TestYourApp(unittest.TestCase):

        def test_case(self):
            app = TestApp(main({}))
            app.get('/service', status=400)
