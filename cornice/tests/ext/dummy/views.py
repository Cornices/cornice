from collections import defaultdict
from cornice import Service

_USERS = defaultdict(dict)


def get_info(request):
    "returns the user data"
    username = request.matchdict['username']
    return _USERS[username]


def includeme(config):
    # FIXME this should also work in includeme
    user_info = Service(name='users', path='/{username}/info')
    user_info.add_view('get', get_info)
    config.add_cornice_service(user_info)
