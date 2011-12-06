=======
Cornice
=======

Overview
========

**Cornice** provides a *Service* class you can use to define web services in
Pyramid.

Each instance of a Service class corresponds to a server path and you may
implement various methods HTTP on the path with simple decorators.

Cornice will automatically return a 405 error with the right Allow header
if a method that was not implemented is requested.

Cornice also provides:

- a Sphinx directive that can be used to document your web services.
  The extension iterates over defined services and will automatically
  generate your web service documentation.

- a validation hook you can use to control the request


QuickStart
==========


To use Cornice, start by including it in your project with the **include**
method in Pyramid::

    def main(global_config, **settings):
        ...
        config.include("cornice")
        ...
        return config.make_wsgi_app()


Learn more about include at http://docs.pylonsproject.org/projects/pyramid/1.0/narr/advconfig.html#including-configuration-from-external-sources

Then you can start to define web services in your views.

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


By default, Cornice uses a Json rendered.


Validation
==========

Cornice provides a *validator* option that you can use to control the request
before it's passed to the code. A validator is a simple callable that gets
the request object and fills **request.error** in case the request has some
errors.

Validators can also convert values and saves them so they can be reused
by the code. This is done by filling the **request.validated** dictionary.

Let's take an example: we want to make sure the incoming request has an
**X-Paid** header. If not, we want the server to return a 402 (payment
required) ::


    from cornice import Service

    foo = Service(name='foo', path='/foo')


    def has_paid(request):
        if not 'X-Paid' in request.headers:
            request.errors.add('header', 'X-Paid', 'You need to pay')


    @foo.get(validator=has_paid)
    def get_value(request):
        """Returns the value.
        """
        return 'Hello'


Notice that you can chain the validators by passing a sequence
to the **validator** option.


Colander integration
--------------------

Colander (http://docs.pylonsproject.org/projects/colander/en/latest/) is a
validation framework from the Pylons project that can be used with Cornice's
validation hook to control a request and deserialize its content into
objects.

Let's say, you have a **Person** schema in Colander, that defines
a person's attributes -- See http://docs.pylonsproject.org/projects/colander/en/latest/basics.html#defining-a-schema-imperatively

And you want to provide a POST Web Service to create a person, where
the request body is the person data serialized in JSON.

Here's how you can do::


  def check_person(request):
     """Unserialize the data from the request."""
      try:
          person = json.loads(request)
      except ValueError:
          request.errors.append('body', 'person', 'Bad Json data!')
          # let's quit
          return

      schema = Person()
      try:
          deserialized = schema.deserialized(person)
      except InvalidError, e:
           # the struct is invalid
           request.errors.append('body', 'person', e.message)
      else:
           request.validated['person'] = deserialized


    @service.post(validator=check_person)
    def data_posted(request):
        person = request['validated'] = 'person'
        ... do the work on person ...


Here, Colander takes care of validating the data against its
schema then converting it into an object you can work with
in your code.


FormEncode integration
----------------------

FormEncode (http://www.formencode.org/en/latest/index.html) is yet another
validation system that can be used with Cornice.

For example, if you want to make sure the optional query option **max**
is an integer, and convert it, you can use FormEncode in a Cornice validator
like this::


    from cornice import Service
    from formencode import validators

    foo = Service(name='foo', path='/foo')
    validator = validators.Int()

    def validate(request):
        try:
            request.validated['max'] = validator.to_python(request.GET['max'])
        except formencode.Invalid, e:
            request.errors.add('url', 'max', e.message)

    @foo.get(validator=validate)
    def get_value(request):
        """Returns the value.
        """
        return 'Hello'
