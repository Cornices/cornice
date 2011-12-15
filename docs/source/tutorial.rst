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

XXX

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

