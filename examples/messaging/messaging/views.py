""" Cornice services.
"""
from cornice import Service
import os
import binascii
import json

from webob import Response, exc
from cornice import Service
import logging
FORMAT = "%(asctime)s %(levelname)-5.5s [%(name)s][%(threadName)s] %(message)s"
logging.basicConfig(format=FORMAT)
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

users = Service(name='users', path='/users', description="Users")
messages = Service(name='messages', path='/', description="Messages")

_USERS = {}
_MESSAGES = []

#
# Helpers
#
def _create_token():
    return binascii.b2a_hex(os.urandom(20)).decode('utf-8') # decode from bytes to utf-8


class _401(exc.HTTPError):
    def __init__(self, msg='Unauthorized'):
        body = {'status': 401, 'message': msg}
        Response.__init__(self, json.dumps(body))
        self.status = 401
        self.content_type = 'application/json'


def valid_token(request):
    LOG.info('valid_token: {0}'.format(str(request.headers)))
    header = 'X-Messaging-Token'
    htoken = request.headers.get(header)
    LOG.info('htoken: {0}'.format(str(htoken)))
    if htoken is None:
        raise _401()
    try:
        user, token = htoken.split('-', 1)
    except ValueError:
        raise _401()

    valid = user in _USERS and _USERS[user] == token
    if not valid:
        raise _401()

    request.validated['user'] = user


def unique(request):
    name = request.body.strip()
    if name in _USERS:
        request.errors.add('url', 'name', 'This user exists!')
    else:
        user = {'name': name, 'token': _create_token()}
        request.validated['user'] = user

def valid_message(request):
    LOG.info('valid_message: {0}'.format(request))
    try:
        message = json.loads(request.body.decode('utf-8'))
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

#
# Services - User Management
#
@users.get(validators=valid_token)
def get_users(request):
    """Returns a list of all users."""
    LOG.info('_USERS: {0}'.format(_USERS.keys()))

    return {'users': list(_USERS.keys())}


@users.post(validators=unique)
def create_user(request):
    """Adds a new user."""
    user = request.validated['user']
    
    name = user['name'].decode('utf-8') # decode from bytes to utf-8
    _USERS[name] = user['token']
    LOG.info('_USERS: {0}'.format(_USERS))
    return {'token': '%s-%s' % (name, user['token'])}


@users.delete(validators=valid_token)
def del_user(request):
    """Removes the user."""
    name = request.validated['user']
    del _USERS[name]
    return {'Goodbye': name}
    
#
# Services - Message Management
#
@messages.get()
def get_messages(request):
    """Returns the 5 latest messages"""
    return _MESSAGES[:5]


@messages.post(validators=(valid_token, valid_message))
def post_message(request):
    """Adds a message"""
    _MESSAGES.insert(0, request.validated['message'])
    LOG.info('_MESSAGES: {0}'.format(_MESSAGES))
    return {'status': 'added'}
