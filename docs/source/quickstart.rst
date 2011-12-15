QuickStart for people in a hurry
================================

You are in a hurry, so we'll assume you are familiar with Pyramid ;)


To use Cornice, start by including it in your project with the **include**
method provided by Pyramid's config object::


    def main(global_config, **settings):
        ...
        config.include("cornice")
        ...
        return config.make_wsgi_app()


This will simply point Cornice's directives to Pyramid so they're loaded.

.. note::

    You can learn more about the include mechanism at 
    http://docs.pylonsproject.org/projects/pyramid/1.0/narr/advconfig.html#including-configuration-from-external-sources


Once this is done, you can start to define web services in your views.

**Cornice** provides a *Service* class you can use to define web services in
Pyramid.

Each instance of a Service class corresponds to a server path and you may
implement various methods HTTP on the path with simple decorators.

Cornice will automatically return a 405 error with the right Allow header
if a method that was not implemented is requested.

For example, let's
define a service where you can **GET** and **POST** a value at
**/values/{value}**, where *value* is an ascii value representing the
name of the value::


    import json
    from cornice import Service

    values = Service(name='foo', path='/values/{value}',
                     description="Cornice Demo")

    _VALUES = {}


    @values.get()
    def get_value(request):
        """Returns the value.
        """
        key = request.matchdict['value']
        return _VALUES.get(key)


    @values.post()
    def set_value(request):
        """Set the value.

        Returns *True* or *False*.
        """
        key = request.matchdict['value']
        try:
            _VALUES.set(key, json.loads(request.body))
        except ValueError:
            return False
        return True


By default, Cornice uses a Json renderer.
