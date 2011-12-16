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

