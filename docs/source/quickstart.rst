QuickStart for people in a hurry
================================

You are in a hurry, so we'll assume you are familiar with Pyramid, Paster, and
Pip ;)

To use Cornice, install it::

    $ pip install cornice


That'll give you a Paster template to use::

    $ pcreate -t cornice project
    ...

The template creates a working Cornice application.

If you want to add cornice support to an already existing project, you'll need
to include cornice in your project `includeme`::

    config.include("cornice")

You can then start to poke at the :file:`views.py` file it
created in the package.

For example, let's
define a service where you can **GET** and **POST** a value at
**/values/{value}**, where *value* is an ascii value representing the
name of the value.

The :file:`views` module can look like this::

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
            _VALUES[key] = json.loads(request.body)
        except ValueError:
            return False
        return True


By default, Cornice uses a Json renderer.
