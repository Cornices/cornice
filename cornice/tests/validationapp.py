import json
from cornice import Service
from pyramid.config import Configurator
from webob.exc import HTTPBadRequest


class GetSchema(object):
    def __call__(self, request):
        pass


class PostSchema(object):
    def __call__(self, request):
        try:
            json.loads(request.body)
        except ValueError:
            return 'Malformed JSON'



service = Service(name="service", path="/service")

@service.get(validator=GetSchema())
def get1(request):
    return {"test": "succeeded"}


@service.post(validator=PostSchema())
def post1(request):
    return {"body": request.body}


def includeme(config):
    config.include("cornice")
    config.scan("cornice.tests.validationapp")


def main(global_config, **settings):
    config = Configurator(settings={})
    config.include(includeme)
    return config.make_wsgi_app()
