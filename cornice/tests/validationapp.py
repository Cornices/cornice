from pyramid.config import Configurator

from cornice import Service
from cornice.schemas import JsonBody, save_converted


class GetSchema(object):
    """Makes sure the foo param is an int if given
    """
    def __call__(self, request):
        if 'foo' in request.GET:
            foo = request.GET['foo']
            try:
                # converting it
                save_converted(request, 'foo', int(foo))
            except ValueError:
                return "Could not convert 'foo' to int : %r" % foo


service = Service(name="service", path="/service")


@service.get(validator=GetSchema())
def get1(request):
    return {"test": "succeeded"}


@service.post(validator=JsonBody())
def post1(request):
    return {"body": request.body}


def includeme(config):
    config.include("cornice")
    config.scan("cornice.tests.validationapp")


def main(global_config, **settings):
    config = Configurator(settings={})
    config.include(includeme)
    return config.make_wsgi_app()
