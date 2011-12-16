Full tutorial
=============

Let's create a full working application with **Cornice**. We want to
create a light messaging service.

Features:

- users can register to the service
- users can list all registered users
- users can send messages
- users can retrieve the latest messages
- messages have three fields: sender, content, color (red or black)
- all operations are done with authentication

Limitations:

- there's a single channel for all messages.
- if a user with the same name is already registered,
  he cannot register.

Design
------

The application provides two services:

- **users**: where you can list all users or register a new one
- **messages**: where you can read the messages or add new ones

On the server, the data is kept in a SQLite Database.

We'll provide a single CLI client in Python


Setting up the development environment
--------------------------------------

To create this application, we'll use Python 2.7. Make sure you
have it on your system, then install **virtualenv** (see
http://pypi.python.org/pypi/virtualenv.)

Create a new directory and a virtualenv in it::

    $ mkdir messaging
    $ cd messaging
    $ virtualenv --no-site packages --distribute .

Once you have it, install Cornice in it with Pip::

    $ bin/pip install Cornice

Cornice provides a Paster Template you can use to create a new
application::

    $ bin/paster create -t cornice messaging
    Selected and implied templates:
    cornice#cornice  A Cornice application

    Variables:
    egg:      messaging
    package:  messaging
    project:  messaging
    Enter appname (Application name) ['']: Messaging
    Enter description (One-line description of the project) ['']: A simple messaging service.
    Enter author (Author name) ['']: Tarek
    Creating template cornice
    ...
    Generating Application...
    Running python2.7 setup.py egg_info


Once your application is generated, go there and call *develop* against it::

    $ cd messaging
    $ ../bin/python setup.py develop
    ...

The application can now be launched via Paster, it provides a default "Hello"
service check::

    $ cd messaging
    $ ../bin/paster serve messaging.ini
    Starting server in PID 7618.
    serving on 0.0.0.0:5000 view at http://127.0.0.1:5000

Once the application is running, visit http://127.0.0.1:5000 in your browser or
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


We're going to get rid of the Hello service, and change this file in order
to add our first service - the users managment ::

    _USERS = []

    @users.get(validator=valid_token)
    def get_users(request):
        """Returns a list of all users."""
        return {'users': _USERS.keys()}

    @users.put(validator=unique)
    def create_user(request):
        """Adds a new user."""
        user = request.validated['user']
        _USERS[user['name']] = user['token']
        return {'token': '%s-%s' % (user['name'], user['token'])}

    @users.delete(validator=valid_token)
    def del_user(request):
        """Removes the user."""
        user = request.validated['user']
        del _USERS[user['name']]
        return {'goodbye': user['name']}


What we have here is 3 methods on **/users**:

- **GET**: simply return the list of users names -- the keys of _USERS
- **PUT**: adds a new user and returns a unique token
- **DELETE**: removes the user.

Remarks:

- **PUT** uses the **unique** validator to make sure that the user
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
    from webob import HTTPUnauthorized


    def _create_token():
        return binascii.b2a_hex(os.urandom(20))

    def valid_token(request):
        header = 'X-Messaging-Token'

        token = request.headers.get(header)
        if token is None:
            raise exc.HTTPUnauthorized()

        token = token.split('-')
        if len(token) != 2:
            raise exc.HTTPUnauthorized()

        user, token = token

        valid = user in _USERS and _USERS[user] == token
        if not valid:
            raise exc.HTTPUnauthorized()

        request.validated['user'] = user


    def unique(request):
        name = request.body
        if name in _USERS:
            request.errors.add('url', 'name', 'This user exists!')
        else:
            user = {'name': name, 'token': _create_token()}
            request.validated['user'] = user


When the validator finds errors, it adds them to the **request.errors**
mapping, and that will return a 400 with the errors.

Let's try our application so far with CURL::


    $ curl http://localhost:5000/users
    {"status": "error", "errors": [{"location": "header", "name": "X-Messaging-Token", "description": "No token"}]}

    $ curl -X PUT http://localhost:5000/users -d 'tarek'
    {"token": "tarek-a15fa2ea620aac8aad3e1b97a64200ed77dc7524"}


    $ curl http://localhost:5000/users -H "X-Messaging-Token:tarek-a15fa2ea620aac8aad3e1b97a64200ed77dc7524"
    {'users': ['tarek']}

    $ curl -X DELETE http://localhost:5000/users -H "X-Messaging-Token:tarek-a15fa2ea620aac8aad3e1b97a64200ed77dc7524"
    {'Goodbye': 'tarek}


XXX

Generating the documentation
----------------------------

XXX

The Client
----------

XXX

Wrapping up everything
----------------------

XXX

