from pyramid.config import Configurator

from cornice import Service
from cornice.schemas import *  # NOQA
from cornice.tests import CatchErrors


service = Service(name="service", path="/service")


def has_payed(request):
    if not 'paid' in request.GET:
        request.errors.add('body', 'paid', 'You must pay!')


def foo_int(request):
    if 'foo' not in request.GET:
        return
    try:
        request.validated['foo'] = int(request.GET['foo'])
    except ValueError:
        request.errors.add('url', 'foo', 'Not an int')


@service.get(validator=(has_payed, foo_int))
def get1(request):
    res = {"test": "succeeded"}
    try:
        res['foo'] = request.validated['foo']
    except KeyError:
        pass

    return res


def _json(request):
    """The request body should be a JSON object."""
    try:
        request.validated['json'] = json.loads(request.body)
    except ValueError:
        request.errors.add('body', 'json', 'Not a json body')


@service.post(validator=_json)
def post1(request):
    return {"body": request.body}


service2 = Service(name="service2", path="/service2")


@service2.get(accept="application/json")
def get2(request):
    return {"body": "yay!"}


service3 = Service(name="service3", path="/service3")


def _accept(request):
    """Accepts text/html"""
    return ('text/html',)


@service3.get(accept=_accept)
def get3(request):
    return {"body": "yay!"}


def includeme(config):
    config.include("cornice")
    config.scan("cornice.tests.validationapp")


def main(global_config, **settings):
    config = Configurator(settings={})
    config.include(includeme)
    return CatchErrors(config.make_wsgi_app())
