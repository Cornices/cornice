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
the request object and returns an HTTP Error code followed by an explanation
in case the request does not comply.

When it returns nothing, the request is considered valid.

Validators can also convert values and saves them so they can be reused
by the code. This is done with the **save_converted**, **get_converted**
functions from the **cornice.schemas** module.

Let's take an example: we want to make sure the incoming request has an
**X-Paid** header. If not, we want the server to return a 402 (payment
required) ::


    from cornice import Service

    foo = Service(name='foo', path='/foo')

    def has_paid(request):
        if not 'X-Paid' in request.headers:
            return 402, 'You need to pay'


    @foo.get(validator='has_paid')
    def get_value(request):
        """Returns the value.
        """
        return 'Hello'


Cornice comes with built-in validators:

- **JsonBody**: makes sure a POST body is a Json object
- **GetChecker**: checks the params for a GET
- **PostChecker**: checks a POST form

Notice that you can chain the validators by passing a sequence
to the **validator** option.

**GetChecker** and **PostChecker** are classes you can use to control
a request params. The classes have a **fields** attribute you
can fill with fields you expect in the request to have.

Each field is defined by a Field object. Cornice defines one built-in
field object: **Integer**. This field makes sure the value is an
integer then saves it with **save_converted**.


In the example below, we create a Checker that controls that the param
**foo** in a GET request is an integer::


    from cornice.schemas import Checker, get_converted


    class Checker(GetChecker):
        """When provided, the **foo** param must be an integer"""
        fields = [Integer('foo')]


    service = Service(name="service", path="/service")


    def has_payed(request):
        if not 'paid' in request.GET:
            return 402, 'You must pay!'


    @service.get(validator=(Checker(), has_payed))
    def get1(request):
        res = {"test": "succeeded"}
        try:
            res['foo'] = get_converted(request, 'foo')
        except KeyError:
            pass

        return res


The **get1** function uses two validators here, and grabs back the **foo**
value that was converted by the **Checker** validator. Notice that the
**foo** option is optional here.


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
          return 400, 'Bad Json data!'

      schema = Person()
      try:
          deserialized = schema.deserialized(person)
      except InvalidError, e:
           # the struct is invalid
           return 400, e.message

      save_converted(request, 'person', deserialized)


    @service.post(validator=check_person)
    def data_posted(request):
        person = get_converted(request, 'person')
        ... do the work on person ...


Here, Colander takes care of validating the data against its
schema then converting it into an object you can work with
in your code.

