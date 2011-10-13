import os
import socket
import StringIO

from webob.exc import HTTPNotFound
from pyramid.config import Configurator

from pyramid.authorization import ACLAuthorizationPolicy
from pyramid_who.whov2 import WhoV2AuthenticationPolicy
from pyramid.interfaces import IAuthenticationPolicy
from zope.interface import implements

from pyramid.view import view_config
from pyramid.interfaces import IRoutesMapper
import venusian

from cornice.resources import Root
from cornice.config import Config


def dict2ini(mapping):
    res = []
    for section, values in mapping.items():
        res.append('[%s]' % section)
        for key, value in values.items():
            if isinstance(value, list):
                value = '\n'.join(value)
            res.append('%s = %s' % (key, value))
    return '\n'.join(res)


def is_local(request):
    environ = request.environ
    host = environ['HTTP_HOST'].split(':')[0]
    host_ip = socket.gethostbyname(host)

    if 'HTTP_X_FORWARDED_FOR' in request.environ:
        # proxied, let's see if it's local
        # get the first ip
        for_ = request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]
        for_ = for_.strip()
        try:
            for_ip = socket.gethostbyname(for_)
        except socket.gaierror:
            return False

        return for_ip == host_ip
    try:
        remote_ip = environ['REMOTE_ADDR']
    except socket.gaierror:
        return False

    return host_ip == remote_ip


def add_apidoc(config, pattern, docstring, renderer):
    apidocs = config.registry.settings.setdefault('apidocs', {})
    info = apidocs.setdefault(pattern, {})
    info['docstring'] = docstring
    info['renderer'] = renderer


class api(object):
    def __init__(self, **kw):
        self.route_pattern = kw.pop('pattern')
        self.route_method = kw.pop('method', 'GET')
        self.renderer = kw.pop('renderer', 'json')
        self.kw = kw

    def __call__(self, func):
        kw = self.kw.copy()
        docstring = func.__doc__
        def callback(context, name, ob):
            config = context.config.with_package(info.module)
            route_name = func.__name__
            route_method = self.route_method
            config.add_apidoc((self.route_pattern, route_method),
                              docstring, self.renderer)
            config.add_route(route_name, self.route_pattern,
                             request_method=route_method)
            config.add_view(view=ob, route_name=route_name,
                            renderer=self.renderer, **kw)

        info = venusian.attach(func, callback, category='pyramid')

        if info.scope == 'class':
            # if the decorator was attached to a method in a class, or
            # otherwise executed at class scope, we need to set an
            # 'attr' into the settings if one isn't already in there
            if 'attr' not in kw:
                kw['attr'] = func.__name__

        kw['_info'] = info.codeinfo # fbo "action_method"
        return func


@view_config(route_name='apidocs', renderer='apidocs.mako')
def apidocs(request):
    routes = []
    mapper = request.registry.getUtility(IRoutesMapper)
    for k, v in request.registry.settings['apidocs'].items():
        routes.append((k, v))
    return {'routes': routes}


HERE = os.path.dirname(__file__)


def get_config(request):
    return request.registry.settings.get('config')


def heartbeat(request):
    # checks the server's state -- if wrong, return a 503 here
    return 'OK'


def manage(request):
    # if it's not a local call, this does not exist
    if not is_local(request):
        raise HTTPNotFound()

    # now let's see if the config allows the debug mode
    config = get_config(request)
    if (not config.has_option('global', 'debug') or
        not config.get('global', 'debug')):
        raise HTTPNotFound()

    # local + activated
    return {'config': config}


def _prefixed_sections(config, prefix):
    res = {}
    for section in config.sections():
        if not section.startswith(prefix):
            continue
        res[section[len(prefix):]] = config.get_map(section)
    return res


def _null_callback(identity, request):
    return ()


class WhoAuth(WhoV2AuthenticationPolicy):
    implements(IAuthenticationPolicy)

    def __init__(self, conf_dir, config, identifier_id, callback=_null_callback):
        identifiers = authenticators = challengers = mdproviders = ()
        request_classifier = None
        challenge_decider = None

        from repoze.who.config import WhoConfig
        parser = WhoConfig(conf_dir)
        parser.parse(config)
        identifiers = parser.identifiers
        authenticators = parser.authenticators
        challengers = parser.challengers
        mdproviders = parser.mdproviders
        request_classifier = parser.request_classifier
        challenge_decider = parser.challenge_decider

        from repoze.who.api import APIFactory

        self._api_factory = APIFactory(identifiers,
                                       authenticators,
                                       challengers,
                                       mdproviders,
                                       request_classifier,
                                       challenge_decider,
                                       remote_user_key='REMOTE_USER',
                                        logger=None,
                                        )
        self._identifier_id = identifier_id
        self._callback = callback


def main(package=None):
    def _main(global_config, **settings):
        config_file = global_config['__file__']
        config_file = os.path.abspath(
                        os.path.normpath(
                        os.path.expandvars(
                            os.path.expanduser(
                            config_file))))

        settings['config'] = config = Config(config_file)
        conf_dir, _ = os.path.split(config_file)

        # extracting the who config
        who_config = _prefixed_sections(config, 'who:')
        who_ini = dict2ini(who_config)
        authn_policy = WhoAuth(conf_dir, who_ini, "basicauth")
        authz_policy = ACLAuthorizationPolicy()
        config = Configurator(root_factory=Root, settings=settings,
                            authorization_policy=authz_policy,
                            authentication_policy=authn_policy)

        # set up custom forbidden view
        config.add_view("cornice.security.forbidden_view",
                        context="pyramid.exceptions.Forbidden")

        # adding default views: __heartbeat__, __apis__
        config.add_route('heartbeat', '/__heartbeat__',
                        renderer='string',
                        view='cornice.wsgiapp.heartbeat')

        config.add_route('manage', '/__config__',
                        renderer='config.mako',
                        view='cornice.wsgiapp.manage')

        config.add_static_view('static', 'cornice:static', cache_max_age=3600)
        config.add_directive('add_apidoc', add_apidoc)
        config.add_route('apidocs', '/__apidocs__')
        config.scan()
        config.scan(package=package)
        return config.make_wsgi_app()
    return _main


def make_main(package=None):
    """Factory to build apps."""
    return main(package)
