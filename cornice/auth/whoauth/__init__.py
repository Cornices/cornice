"""
repoze.who auth plugins for pyramid.
"""

from zope.interface import implements

from pyramid.interfaces import IAuthenticationPolicy
from pyramid.security import Everyone, Authenticated
from pyramid.response import Response

from repoze.who.config import WhoConfig
from repoze.who.api import APIFactory


def forbidden_view(request):
    """Custom "forbidden" view for connecting pyramid and repoze.who.

    This is a simple view that uses the repoze.who challenge API to prompt
    for credentials.
    """
    api = request.environ.get("repoze.who.api")
    challenge_app = api.challenge()
    if challenge_app:
        return request.get_response(challenge_app)
    return Response("403 Forbidden", status="403 Forbidden")


def _null_callback(userid, request):
    """Default group-finder callback for WhoAuthenticationPolicy."""
    return ()


class WhoAuthenticationPolicy(object):
    """Pyramid authentication policy built on top of repoze.who.

    This is a pyramid authentication policy built on top of the repoze.who
    API.  It's a lot like the one found in the "pyramid_who" package, but
    has some API tweaks and simplifications to fit in better with cornice.
    """

    implements(IAuthenticationPolicy)

    def __init__(self, config, callback=_null_callback):
        # XXX cornice should pass in config file location, so we
        #     can pass it on to WhoConfig
        parser = WhoConfig("")
        parser.parse(config)

        identifiers = parser.identifiers
        authenticators = parser.authenticators
        challengers = parser.challengers
        mdproviders = parser.mdproviders
        request_classifier = parser.request_classifier
        challenge_decider = parser.challenge_decider

        self._api_factory = APIFactory(identifiers,
                                       authenticators,
                                       challengers,
                                       mdproviders,
                                       request_classifier,
                                       challenge_decider)
        self._callback = callback

    def authenticated_userid(self, request):
        userid = self.unauthenticated_userid(request)
        if userid is None:
            return None
        if self._callback(userid, request) is None:
            return None
        return userid

    def unauthenticated_userid(self, request):
        identity = request.environ.get("repoze.who.identity")
        if identity is None:
            api = self._api_factory(request.environ)
            identity = api.authenticate()
        if identity is None:
            return None
        return identity["repoze.who.userid"]

    def effective_principals(self, request):
        principals = [Everyone]
        userid = self.unauthenticated_userid(request)
        if userid is None:
            return principals
        groups = self._callback(userid, request)
        if groups is None:
            return principals
        principals.append(userid)
        principals.append(Authenticated)
        principals.extend(groups)
        return principals

    def remember(self, request, principal, **kw):
        headers = []
        identity = {"repoze.who.userid": principal}
        api = self._api_factory(request.environ)
        #  Give all IIdentifiers a chance to remember the login.
        #  This is the same logic as inside the api.login() method,
        #  but without repeating the authentication step.
        for name, plugin in api.identifiers:
            i_headers = plugin.remember(request.environ, identity)
            if i_headers is not None:
                headers.extend(i_headers)
        return headers

    def forget(self, request):
        api = self._api_factory(request.environ)
        return api.logout()


def _prefixed_sections(config, prefix):
    """Extract prefixed sections from a cornice Config object."""
    res = {}
    for section in config.sections():
        if not section.startswith(prefix):
            continue
        res[section[len(prefix):]] = config.get_map(section)
    return res


def _dict2ini(mapping):
    """Turn a Config mapping dict into ini-formatted text."""
    res = []
    for section, values in mapping.items():
        res.append('[%s]' % section)
        for key, value in values.items():
            if isinstance(value, list):
                value = '\n'.join(value)
            res.append('%s = %s' % (key, value))
    return '\n'.join(res)


def includeme(config):
    """Include default whoauth settings into a pyramid config.

    This function provides a hook for pyramid to include the default settings
    for auth via repoze.who.  Activate it like so:

        config.include("cornice.auth.whoauth")

    It will set up the following defaults for you:

        * add a repoze.who-based AuthenticationPolicy
        * add a "forbidden view" to invoke repoze.who when auth is required

    """
    # Add the forbidden view.
    config.add_view(forbidden_view, context="pyramid.exceptions.Forbidden")
    # Extract repoze.who settings form the config file.
    settings = config.get_settings()
    if "config" in settings:
        who_config = _prefixed_sections(settings["config"], 'who:')
        who_ini = _dict2ini(who_config)
        # Use those settings for the authn policy.
        authn_policy = WhoAuthenticationPolicy(who_ini)
        config.set_authentication_policy(authn_policy)
