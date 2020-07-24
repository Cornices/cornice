.. _quickstart:

QuickStart for people in a hurry
================================

You are in a hurry, so we'll assume you are familiar with Pip ;)

To use Cornice, install it::

    $ pip install cornice

You'll also need **waitress** (see https://pypi.python.org/pypi/waitress)::

    $ pip install waitress

To start from scratch, you can use a `Cookiecutter <https://cookiecutter.readthedocs.io>`_ project template::

    $ pip install cookiecutter
    $ cookiecutter gh:Cornices/cookiecutter-cornice
    ...

Once your application is generated, go there and call *develop* against it::

    $ cd myapp
    $ python setup.py develop
    ...

The template creates a working Cornice application.

.. note::

    If you're familiar with Pyramid and just want to add *cornice* to an already
    existing project, you'll just need to include ``cornice`` in your project::

        config.include("cornice")

You can then start poking at the :file:`views.py` file.

For example, let's define a service where you can **GET** and **POST** a value
at **/values/{value}**, where *value* is an ascii value representing the
name of the value.

The :file:`views` module can look like this::

    from cornice import Service

    _VALUES = {}

    values = Service(name='foo',
                     path='/values/{value}',
                     description="Cornice Demo")

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


Check out what is stored in a ``foo`` value at http://localhost:6543/values/foo
