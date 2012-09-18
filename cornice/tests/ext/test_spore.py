from cornice.tests.support import TestCase

from cornice.service import Service, get_services
from cornice.ext.spore import generate_spore_description


class TestSporeGeneration(TestCase):

    def _define_coffee_methods(self, service):
        @service.get()
        def get_coffee(request):
            pass

    def test_generate_spore_description(self):

        coffees = Service(name='Coffees', path='/coffee')
        coffee = Service(name='coffee', path='/coffee/{bar}/{id}')

        @coffees.post()
        def post_coffees(request):
            """Post information about the coffee"""
            return "ok"

        self._define_coffee_methods(coffee)
        self._define_coffee_methods(coffees)

        services = get_services(names=('coffee', 'Coffees'))
        spore = generate_spore_description(
                services, name="oh yeah",
                base_url="http://localhost/", version="1.0")

        # basic fields
        self.assertEqual(spore['name'], "oh yeah")
        self.assertEqual(spore['base_url'], "http://localhost/")
        self.assertEqual(spore['version'], "1.0")

        # methods
        methods = spore['methods']
        self.assertIn('get_coffees', methods)
        self.assertDictEqual(methods['get_coffees'], {
            'path': '/coffee',
            'method': 'GET',
            'format': 'json',
            })

        self.assertIn('post_coffees', methods)
        self.assertDictEqual(methods['post_coffees'], {
            'path': '/coffee',
            'method': 'POST',
            'format': 'json',
            'description': post_coffees.__doc__
            })

        self.assertIn('get_coffee', methods)
        self.assertDictEqual(methods['get_coffee'], {
            'path': '/coffee/:bar/:id',
            'method': 'GET',
            'format': 'json',
            'required_params': ['bar', 'id']
            })
