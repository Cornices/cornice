Sphinx integration
==================

Maintaining documentation while the code is evolving is painful.
Avoiding information duplication is also quite a challenge.

Cornice tries to reduce a bit the pain by providing a Sphinx
(http://sphinx.pocoo.org/) directive that scans the web
services and build the documentation using:

- the description provided when a Service instance is created
- the docstrings of all functions involved in creating the response:
  the web services function itself and the validators.

The assumption made is that maintaining those docstrings while
working on the code is easier.


Activate the extension
----------------------

To activate Cornice's directive, you must include it in your
Sphinx project :file:`conf.py` file::

    import cornice

    sys.path.insert(0, os.path.abspath(cornice.__file__))
    extensions = ['cornice.sphinxext']

Of course this may vary if you have other extensions.


The service directive
---------------------

Cornice provides a single **service** directive you can use to
inject the Web Services documentation into Sphinx.

The directive has two options:

- **package**: the name of the Python package that contains Cornice web
  services. Cornice will scan it and look for the services. **mandatory**

- **service**: the name of the service to document. This is the name
  you provide when you create a **Service** class. If not given, Cornice
  will include **all** Services in the order it found them. **optional**


Full example
------------

Let's say you have a **quote** project with a single service where you
can **PUT** and **GET** a quote.

The service makes sure the quote starts with a majuscule and ends with
a dot !

Here's the **full** app::

    from cornice import Service
    from pyramid.config import Configurator
    from pyramid.httpexceptions import HTTPNotFound
    import string

    desc = """\
    Service that maintains a quote.
    """

    quote = Service(name='quote', path='/quote', description=desc)


    def check_quote(request):
        """Makes sure the quote starts with a majuscule and ends with a dot"""
        quote = request.body
        if quote[0] not in uppercase:
            request.errors.add('body', 'quote', 'Does not start with a majuscule')

        if quote[-1] not in ('.', '?', '!'):
            request.errors.add('body', 'quote', 'Does not end properly')

        if len(request.errors) == 0:
            request.validated['quote'] = quote


    _quote = "Not set, yet !"

    @quote.get()
    def get_quote(request):
        """Returns the quote"""
        return _quote


    @quote.post(validator=check_quote)
    def post_quote(request):
        """Update the quote"""
        global _quote
        _quote = request.validated['quote']


    def main(global_config, **settings):
        config = Configurator(settings={})
        config.include("cornice")
        config.scan("coolapp")
        return config.make_wsgi_app()

    if __name__ == '__main__':
        from wsgiref.simple_server import make_server
        app = main({})
        httpd = make_server('', 8000, app)
        print "Listening on port 8000...."
        httpd.serve_forever()


And here's the **full** sphinx doc example::

    Welcome to coolapp's documentation!
    ===================================

    My **Cool** app provides a way to send cool quotes to the server !

    .. services::
       :package: coolapp
       :service: quote

The resulting doc is:

.. image:: cornice.png
