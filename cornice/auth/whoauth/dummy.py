
from zope.interface import implements
from repoze.who.interfaces import IAuthenticator


class DummyAuthenticator(object):
    """Authenticator that accepts any and all login credentials."""

    implements(IAuthenticator)

    def authenticate(self, environ, identity):
        return identity.get("login")
