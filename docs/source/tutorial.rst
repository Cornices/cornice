Full tutorial
=============

Let's create a full working application with **Cornice**. We want to
create a light messaging service.

You can find its whole source code at https://github.com/mozilla-services/cornice/blob/master/examples/messaging

Features:

- users can register to the service
- users can list all registered users
- users can send messages
- users can retrieve the latest messages
- messages have three fields: sender, content, color (red or black)
- adding a message is done through authentication

Limitations:

- there's a single channel for all messages.
- if a user with the same name is already registered,
  he cannot register.
- all messages and users are kept in memory.


Design
------

The application provides two services:

- **users**, at **/users**: where you can list all users or register a new one
- **messages**, at **/**: where you can read the messages or add new ones

On the server, the data is kept in memory.

We'll provide a single CLI client in Python, using Curses.


Setting up the development environment
--------------------------------------

To create this application, we'll use Python 2.7. Make sure you
have it on your system, then install **virtualenv** (see
http://pypi.python.org/pypi/virtualenv.)

Create a new directory and a virtualenv in it::

    $ mkdir messaging
    $ cd messaging
    $ virtualenv --no-site-packages .

Once you have it, install Cornice in it with Pip::

    $ bin/pip install cornice

Cornice provides a Paster Template you can use to create a new
application::

    $ bin/pcreate -t cornice messaging
    Creating directory <...path ...>/messaging
      Recursing into +package+
        Creating <...path ...>/messaging/messaging/
        Copying __init__.py_tmpl to <...path ...>/messaging/messaging/__init__.py
        Copying views.py_tmpl to <...path ...>/messaging/messaging/views.py
      Copying +package+.ini_tmpl to <...path ...>/messaging/messaging.ini
      Copying README.rst_tmpl to <...path ...>/messaging/README.rst
      Copying setup.py_tmpl to <...path ...>/messaging/setup.py
    Welcome to Pyramid.  Sorry for the convenience.

Once your application is generated, go there and call *develop* against it::

    $ cd messaging
    $ ../bin/python setup.py develop
    ...

The application can now be launched via embedded Pyramid pserve, it provides a default "Hello"
service check::

    $ ../bin/pserve messaging.ini
    Starting server in PID 7618.
    serving on 0.0.0.0:6543 view at http://127.0.0.1:6543

Once the application is running, visit http://127.0.0.1:6543 in your browser or
Curl and make sure you get::

    {'Hello': 'World'}


Defining the services
---------------------

Let's open the file in messaging/views.py, it contains all the Services::

    from cornice import Service

    hello = Service(name='hello', path='/', description="Simplest app")

    @hello.get()
    def get_info(request):
        """Returns Hello in JSON."""
        return {'Hello': 'World'}


Users management
:::::::::::::::


We're going to get rid of the Hello service, and change this file in order
to add our first service - the users management ::

    from cornice import Service

    _USERS = {}
    users = Service(name='users', path='/users', description="User registration")

    @users.get(validators=valid_token)
    def get_users(request):
        """Returns a list of all users."""
        return {'users': _USERS.keys()}

    @users.post(validators=unique)
    def create_user(request):
        """Adds a new user."""
        user = request.validated['user']
        _USERS[user['name']] = user['token']
        return {'token': '%s-%s' % (user['name'], user['token'])}

    @users.delete(validators=valid_token)
    def del_user(request):
        """Removes the user."""
        name = request.validated['user']
        del _USERS[name]
        return {'Goodbye': name}


What we have here is 3 methods on **/users**:

- **GET**: simply return the list of users names -- the keys of _USERS
- **POST**: adds a new user and returns a unique token
- **DELETE**: removes the user.

Remarks:

- **POST** uses the **unique** validator to make sure that the user
  name is not already taken. That validator is also in charge of
  generating a unique token associated with the user.
- **GET** users the **valid_token** to verify that a **X-Messaging-Token**
  header is provided in the request, with a valid token. That also identifies
  the user.
- **DELETE** also identifies the user then removes it.

Validators are filling the **request.validated** mapping, the service can
then use.

Here's their code::

    import os
    import binascii
    import json

    from webob import Response, exc
    from cornice import Service

    users = Service(name='users', path='/users', description="Users")
    _USERS = {}


    #
    # Helpers
    #
    def _create_token():
        return binascii.b2a_hex(os.urandom(20))


    class _401(exc.HTTPError):
        def __init__(self, msg='Unauthorized'):
            body = {'status': 401, 'message': msg}
            Response.__init__(self, json.dumps(body))
            self.status = 401
            self.content_type = 'application/json'


    def valid_token(request):
        header = 'X-Messaging-Token'
        token = request.headers.get(header)
        if token is None:
            raise _401()

        token = token.split('-')
        if len(token) != 2:
            raise _401()

        user, token = token

        valid = user in _USERS and _USERS[user] == token
        if not valid:
            raise _401()

        request.validated['user'] = user


    def unique(request):
        name = request.body
        if name in _USERS:
            request.errors.add('url', 'name', 'This user exists!')
        else:
            user = {'name': name, 'token': _create_token()}
            request.validated['user'] = user


    #
    # Services
    #

    #
    # User Management
    #


    @users.get(validators=valid_token)
    def get_users(request):
        """Returns a list of all users."""
        return {'users': _USERS.keys()}


    @users.post(validators=unique)
    def create_user(request):
        """Adds a new user."""
        user = request.validated['user']
        _USERS[user['name']] = user['token']
        return {'token': '%s-%s' % (user['name'], user['token'])}


    @users.delete(validators=valid_token)
    def del_user(request):
        """Removes the user."""
        name = request.validated['user']
        del _USERS[name]
        return {'Goodbye': name}


When the validator finds errors, it adds them to the **request.errors**
mapping, and that will return a 400 with the errors.

Let's try our application so far with CURL::


    $ curl http://localhost:6543/users
    {"status": 401, "message": "Unauthorized"}

    $ curl -X POST http://localhost:6543/users -d 'tarek'
    {"token": "tarek-a15fa2ea620aac8aad3e1b97a64200ed77dc7524"}

    $ curl http://localhost:6543/users -H "X-Messaging-Token:tarek-a15fa2ea620aac8aad3e1b97a64200ed77dc7524"
    {'users': ['tarek']}

    $ curl -X DELETE http://localhost:6543/users -H "X-Messaging-Token:tarek-a15fa2ea620aac8aad3e1b97a64200ed77dc7524"
    {'Goodbye': 'tarek}



Messages management
::::::::::::::::::

Now that we have users, let's post and get messages. This is done via two very
simple functions we're adding in the :file:`views.py` file::


    messages = Service(name='messages', path='/', description="Messages")

    _MESSAGES = []


    @messages.get()
    def get_messages(request):
        """Returns the 5 latest messages"""
        return _MESSAGES[:5]


    @messages.post(validator=(valid_token, valid_message))
    def post_message(request):
        """Adds a message"""
        _MESSAGES.insert(0, request.validated['message'])
        return {'status': 'added'}



The first one simply returns the five first messages in a list, and the second
one inserts a new message in the beginning of the list.

The **POST** uses two validators:

- :func:`valid_token`: the function we used previously that makes sure the
  user is registered
- :func:`valid_message`: a function that looks at the message provided in the
  POST body, and puts it in the validated dict.


Here's the :func:`valid_message` function::

    def valid_message(request):
        try:
            message = json.loads(request.body)
        except ValueError:
            request.errors.add('body', 'message', 'Not valid JSON')
            return

        # make sure we have the fields we want
        if 'text' not in message:
            request.errors.add('body', 'text', 'Missing text')
            return

        if 'color' in message and message['color'] not in ('red', 'black'):
            request.errors.add('body', 'color', 'only red and black supported')
        elif 'color' not in message:
            message['color'] = 'black'

        message['user'] = request.validated['user']
        request.validated['message'] = message


This function extracts the json body, then checks that it contains a text key
at least. It adds a color or use the one that was provided,
and reuse the user name provided by the previous validator
with the token control.


Generating the documentation
----------------------------

Now that we have a nifty web application, let's add some doc.

Go back to the root of your project and install Sphinx::

    $ bin/pip install Sphinx

Then create a Sphinx structure with **sphinx-quickstart**::


    $ mkdir docs
    $ bin/sphinx-quickstart
    Welcome to the Sphinx 1.0.7 quickstart utility.

    ..

    Enter the root path for documentation.
    > Root path for the documentation [.]: docs
    ...
    > Separate source and build directories (y/N) [n]: y
    ...
    > Project name: Messaging
    > Author name(s): Tarek
    ...
    > Project version: 1.0
    ...
    > Create Makefile? (Y/n) [y]:
    > Create Windows command file? (Y/n) [y]:


Once the initial structure is created, we need to declare the Cornice
extension, by editing the :file:`source/conf.py` file. We want to change
**extensions = []** into::

    import cornice   # makes sure cornice is available
    extensions = ['cornice.ext.sphinxext']


The last step is to document your services by editing the
:file:`source/index.rst` file like this::

    Welcome to Messaging's documentation!
    =====================================

    .. services::
       :modules: messaging.views


The **services** directive is told to look at the services in the **messaging**
package. When the documentation is built, you will get a nice
output of all the services we've described earlier.


The Client
----------

A simple client to use against our service can do three things:

1. let the user register a name
2. poll for the latest messages
3. let the user send a message !

Without going into great details, there's a Python CLI against messaging
that uses Curses.

See https://github.com/mozilla-services/cornice/blob/master/examples/messaging/messaging/client.py
