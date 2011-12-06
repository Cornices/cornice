from pyramid.config import Configurator

from cornice import Service
from cornice.schemas import *  # NOQA
from cornice.tests import CatchErrors


class Checker(GetChecker):
    fields = [Integer('foo')]


service = Service(name="service", path="/service")


def has_payed(request):
    if not 'paid' in request.GET:
        request.errors.add('body', 'paid', 'You must pay!')


@service.get(validator=(Checker(), has_payed))
def get1(request):
    res = {"test": "succeeded"}
    try:
        res['foo'] = request.validated['foo']
    except KeyError:
        pass

    return res


@service.post(validator=JsonBody())
def post1(request):
    return {"body": request.body}


service2 = Service(name="service2", path="/service2")


@service2.get(accept="text/json")
def get2(request):
    return {"body": "yay!"}


service3 = Service(name="service3", path="/service3")


@service3.get(accept=lambda x: ('text/html',))
def get3(request):
    return {"body": "yay!"}


def includeme(config):
    config.include("cornice")
    config.scan("cornice.tests.validationapp")


def main(global_config, **settings):
    config = Configurator(settings={})
    config.include(includeme)
    return CatchErrors(config.make_wsgi_app())
