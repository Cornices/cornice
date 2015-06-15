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

You can then start poking at the :file:`views.py` file that
has been created.

For example, let's define a service where you can **GET** and **POST** a value
at **/values/{value}**, where *value* is an ascii value representing the
name of the value.

The :file:`views` module can look like this::

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
            # json_body is JSON-decoded variant of the request body
            _VALUES[key] = request.json_body
        except ValueError:
            return False
        return True


.. note::

    By default, Cornice uses a Json renderer.


Run your Cornice application with::

    $ pserve project.ini --reload


Set a key-value using Curl::

    $ curl -X POST http://localhost:6543/values/foo -d '{"a": 1}'


Check out what is stored in a foo values, open http://localhost:6543/values/foo
