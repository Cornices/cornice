""" Cornice services.
"""
from cornice import Service
import os
import binascii

users = Service(name='users', path='/users', description="Users")

_USERS = {}

#
# Helpers
#
def _create_token():
    return binascii.b2a_hex(os.urandom(20))

def valid_token(request):
    header = 'X-Messaging-Token'

    token = request.headers.get(header)
    if token is None:
        request.errors.add('header', header, 'No token')
        return

    token = token.split('-')
    if len(token) != 2:
        request.errors.add('header', header, 'Invalid')
        return

    user, token = token

    valid = user in _USERS and _USERS[user] == token
    if not valid:
        request.errors.add('header', header, 'Invalid')
    else:
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
    name = request.validated['user']['name']
    del _USERS[name]
    return {'Goodbye': name}
