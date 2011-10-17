from zope.interface import implements
from repoze.who.interfaces import IAuthenticator


class DummyAuthenticator(object):
    """Authenticator that accepts any and all login credentials."""
    implements(IAuthenticator)

    def authenticate(self, environ, identity):
        return identity.get("login")


def forbidden_view(request):
    """Custom "forbidden" view for pyramid.

    This will use the repoze.who challenge API to prompt for credentials.
    We should submit such a view upstream to pyramid_who.
    """
    api = request.environ.get("repoze.who.api")
    return request.get_response(api.challenge())
