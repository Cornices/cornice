SPORE support
#############

Cornice has support for `SPORE <https://github.com/SPORE/specifications>`_.
SPORE is a way to describe your REST web services, as WSDL is for WS-*
services. This allows to ease the creation of generic SPORE clients, which are
able to consume any REST API with a SPORE endpoint.

Here is how you can let cornice describe your web service for you::

    from cornice.ext.spore import generate_spore_description
    from cornice.service import Service, get_services

    spore = Service('spore', path='/spore', renderer='jsonp')
    @spore.get
    def get_spore(request):
        services = get_services()
        return generate_spore_description(services, 'Service name', request.application_url, '1.0')

And you'll get a definition of your service, in SPORE, available at `/spore`.

Of course, you can use it to do other things, like generating the file locally
and exporting it wherever it makes sense to you, etc.
