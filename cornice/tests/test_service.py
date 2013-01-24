# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.service import Service, get_services, clear_services
from cornice.tests import validationapp
from cornice.tests.support import TestCase

_validator = lambda req: True
_validator2 = lambda req: True
_stub = lambda req: None


class TestService(TestCase):

    def tearDown(self):
        clear_services()

    def test_service_instanciation(self):
        service = Service("coconuts", "/migrate")
        self.assertEquals(service.name, "coconuts")
        self.assertEquals(service.path, "/migrate")
        self.assertEquals(service.renderer, Service.renderer)

        service = Service("coconuts", "/migrate", renderer="html")
        self.assertEquals(service.renderer, "html")

        # test that lists are also set
        validators = [lambda x: True, ]
        service = Service("coconuts", "/migrate", validators=validators)
        self.assertEquals(service.validators, validators)

    def test_get_arguments(self):
        service = Service("coconuts", "/migrate")
        # not specifying anything, we should get the default values
        args = service.get_arguments({})
        for arg in Service.mandatory_arguments:
            self.assertEquals(args[arg], getattr(Service, arg, None))

        # calling this method on a configured service should use the values
        # passed at instanciation time as default values
        service = Service("coconuts", "/migrate", renderer="html")
        args = service.get_arguments({})
        self.assertEquals(args['renderer'], 'html')

        # if we specify another renderer for this service, despite the fact
        # that one is already set in the instance, this one should be used
        args = service.get_arguments({'renderer': 'foobar'})
        self.assertEquals(args['renderer'], 'foobar')

        # test that list elements are not overwritten
        # define a validator for the needs of the test

        service = Service("vaches", "/fetchez", validators=(_validator,))
        self.assertEquals(len(service.validators), 1)
        args = service.get_arguments({'validators': (_validator2,)})

        # the list of validators didn't changed
        self.assertEquals(len(service.validators), 1)

        # but the one returned contains 2 validators
        self.assertEquals(len(args['validators']), 2)

        # test that exclude effectively removes the items from the list of
        # validators / filters it returns, without removing it from the ones
        # registered for the service.
        service = Service("open bar", "/bar", validators=(_validator,
                                                          _validator2))
        self.assertEquals(service.validators, [_validator, _validator2])

        args = service.get_arguments({"exclude": _validator2})
        self.assertEquals(args['validators'], [_validator])

        # defining some non-mandatory arguments in a service should make
        # them available on further calls to get_arguments.

        service = Service("vaches", "/fetchez", foobar="baz")
        self.assertIn("foobar", service.arguments)
        self.assertIn("foobar", service.get_arguments())

    def test_view_registration(self):
        # registering a new view should make it available in the list.
        # The methods list is populated
        service = Service("color", "/favorite-color")

        def view(request):
            pass
        service.add_view("post", view, validators=(_validator,))
        self.assertEquals(len(service.definitions), 1)
        method, _view, _ = service.definitions[0]

        # the view had been registered. we also test here that the method had
        # been inserted capitalized (POST instead of post)
        self.assertEquals(("POST", view), (method, _view))

    def test_decorators(self):
        service = Service("color", "/favorite-color")

        @service.get()
        def get_favorite_color(request):
            return "blue, hmm, red, hmm, aaaaaaaah"

        self.assertEquals(2, len(service.definitions))
        method, view, _ = service.definitions[0]
        self.assertEquals(("GET", get_favorite_color), (method, view))
        method, view, _ = service.definitions[1]
        self.assertEquals(("HEAD", get_favorite_color), (method, view))

        @service.post(accept='text/plain', renderer='plain')
        @service.post(accept='application/json')
        def post_favorite_color(request):
            pass

        # using multiple decorators on a resource should register them all in
        # as many different definitions in the service
        self.assertEquals(4, len(service.definitions))

        @service.patch()
        def patch_favorite_color(request):
            return ""

        method, view, _ = service.definitions[4]
        self.assertEquals("PATCH", method)

    def test_get_acceptable(self):
        # defining a service with different "accept" headers, we should be able
        # to retrieve this information easily
        service = Service("color", "/favorite-color")
        service.add_view("GET", lambda x: "blue", accept="text/plain")
        self.assertEquals(service.get_acceptable("GET"), ['text/plain'])

        service.add_view("GET", lambda x: "blue", accept="application/json")
        self.assertEquals(service.get_acceptable("GET"),
                          ['text/plain', 'application/json'])

        # adding a view for the POST method should not break everything :-)
        service.add_view("POST", lambda x: "ok", accept=('foo/bar'))
        self.assertEquals(service.get_acceptable("GET"),
                          ['text/plain', 'application/json'])
        # and of course the list of accepted content-types  should be available
        # for the "POST" as well.
        self.assertEquals(service.get_acceptable("POST"),
                          ['foo/bar'])

        # it is possible to give acceptable content-types dynamically at
        # run-time. You don't always want to have the callables when retrieving
        # all the acceptable content-types
        service.add_view("POST", lambda x: "ok", accept=lambda r: "text/json")
        self.assertEquals(len(service.get_acceptable("POST")), 2)
        self.assertEquals(len(service.get_acceptable("POST", True)), 1)

    def test_get_validators(self):
        # defining different validators for the same services, even with
        # different calls to add_view should make them available in the
        # get_validators method

        def validator(request):
            """Super validator"""
            pass

        def validator2(request):
            pass

        service = Service('/color', '/favorite-color')
        service.add_view('GET', lambda x: 'ok',
                         validators=(validator, validator))
        service.add_view('GET', lambda x: 'ok', validators=(validator2))
        self.assertEquals(service.get_validators('GET'),
                          [validator, validator2])

    if validationapp.COLANDER:
        def test_schemas_for(self):
            schema = validationapp.FooBarSchema
            service = Service("color", "/favorite-color")
            service.add_view("GET", lambda x: "red", schema=schema)
            self.assertEquals(len(service.schemas_for("GET")), 1)
            service.add_view("GET", lambda x: "red", validators=_validator,
                             schema=schema)
            self.assertEquals(len(service.schemas_for("GET")), 2)

    def test_class_parameters(self):
        # when passing a "klass" argument, it gets registered. It also tests
        # that the view argument can be a string and not a callable.
        class TemperatureCooler(object):
            def get_fresh_air(self):
                pass
        service = Service("TemperatureCooler", "/freshair",
                          klass=TemperatureCooler)
        service.add_view("get", "get_fresh_air")

        self.assertEquals(len(service.definitions), 2)

        method, view, args = service.definitions[0]
        self.assertEquals(view, "get_fresh_air")
        self.assertEquals(args["klass"], TemperatureCooler)

    def test_get_services(self):
        self.assertEquals([], get_services())
        foobar = Service("Foobar", "/foobar")
        self.assertIn(foobar, get_services())

        barbaz = Service("Barbaz", "/barbaz")
        self.assertIn(barbaz, get_services())

        self.assertEquals([barbaz, ], get_services(exclude=['Foobar', ]))
        self.assertEquals([foobar, ], get_services(names=['Foobar', ]))
        self.assertEquals([foobar, barbaz],
                          get_services(names=['Foobar', 'Barbaz']))

    def test_default_validators(self):

        old_validators = Service.default_validators
        old_filters = Service.default_filters
        try:
            def custom_validator(request):
                pass

            def custom_filter(request):
                pass

            def freshair(request):
                pass

            # the default validators should be used when registering a service
            Service.default_validators = [custom_validator, ]
            Service.default_filters = [custom_filter, ]
            service = Service("TemperatureCooler", "/freshair")
            service.add_view("GET", freshair)
            method, view, args = service.definitions[0]

            self.assertIn(custom_validator, args['validators'])
            self.assertIn(custom_filter, args['filters'])

            # defining a service with additional filters / validators should
            # work as well
            def another_validator(request):
                pass

            def another_filter(request):
                pass

            def groove_em_all(request):
                pass

            service2 = Service('FunkyGroovy', '/funky-groovy',
                               validators=[another_validator],
                               filters=[another_filter])

            service2.add_view("GET", groove_em_all)
            method, view, args = service2.definitions[0]

            self.assertIn(custom_validator, args['validators'])
            self.assertIn(another_validator, args['validators'])
            self.assertIn(custom_filter, args['filters'])
            self.assertIn(another_filter, args['filters'])
        finally:
            Service.default_validators = old_validators
            Service.default_filters = old_filters

    def test_cors_support(self):
        self.assertFalse(
            Service(name='foo', path='/foo').cors_enabled)

        self.assertTrue(
            Service(name='foo', path='/foo', cors_enabled=True)
            .cors_enabled)

        self.assertFalse(
            Service(name='foo', path='/foo', cors_enabled=False)
            .cors_enabled)

        self.assertTrue(
            Service(name='foo', path='/foo', cors_origins=('*',))
            .cors_enabled)

        self.assertFalse(
            Service(name='foo', path='/foo',
                    cors_origins=('*'), cors_enabled=False)
            .cors_enabled)

    def test_cors_headers_for_service_instanciation(self):
        # When definining services, it's possible to add headers. This tests
        # it is possible to list all the headers supported by a service.
        service = Service('coconuts', '/migrate',
                          cors_headers=('X-Header-Coconut'))
        self.assertNotIn('X-Header-Coconut', service.cors_supported_headers)

        service.add_view('POST', _stub)
        self.assertIn('X-Header-Coconut', service.cors_supported_headers)

    def test_cors_headers_for_view_definition(self):
        # defining headers in the view should work.
        service = Service('coconuts', '/migrate')
        service.add_view('POST', _stub, cors_headers=('X-Header-Foobar'))
        self.assertIn('X-Header-Foobar', service.cors_supported_headers)

    def test_cors_headers_extension(self):
        # definining headers in the service and in the view
        service = Service('coconuts', '/migrate',
                          cors_headers=('X-Header-Foobar'))
        service.add_view('POST', _stub, cors_headers=('X-Header-Barbaz'))
        self.assertIn('X-Header-Foobar', service.cors_supported_headers)
        self.assertIn('X-Header-Barbaz', service.cors_supported_headers)

        # check that adding the same header twice doesn't make bad things
        # happen
        service.add_view('POST', _stub, cors_headers=('X-Header-Foobar'),)
        self.assertEquals(len(service.cors_supported_headers), 2)

        # check that adding a header on a cors disabled method doesn't
        # change anything
        service.add_view('put', _stub,
                         cors_headers=('X-Another-Header',),
                         cors_enabled=False)

        self.assertFalse('X-Another-Header' in service.cors_supported_headers)

    def test_cors_supported_methods(self):
        foo = Service(name='foo', path='/foo', cors_enabled=True)
        foo.add_view('GET', _stub)
        self.assertIn('GET', foo.cors_supported_methods)

        foo.add_view('POST', _stub)
        self.assertIn('POST', foo.cors_supported_methods)

    def test_disabling_cors_for_one_method(self):
        foo = Service(name='foo', path='/foo', cors_enabled=True)
        foo.add_view('GET', _stub)
        self.assertIn('GET', foo.cors_supported_methods)

        foo.add_view('POST', _stub, cors_enabled=False)
        self.assertIn('GET', foo.cors_supported_methods)
        self.assertFalse('POST' in foo.cors_supported_methods)

    def test_cors_supported_origins(self):
        foo = Service(
            name='foo', path='/foo', cors_origins=('mozilla.org',))

        foo.add_view('GET', _stub,
                     cors_origins=('notmyidea.org', 'lolnet.org'))

        self.assertIn('mozilla.org', foo.cors_supported_origins)
        self.assertIn('notmyidea.org', foo.cors_supported_origins)
        self.assertIn('lolnet.org', foo.cors_supported_origins)

    def test_per_method_supported_origins(self):
        foo = Service(
            name='foo', path='/foo', cors_origins=('mozilla.org',))
        foo.add_view('GET', _stub, cors_origins=('lolnet.org',))

        self.assertTrue('mozilla.org' in foo.cors_origins_for('GET'))
        self.assertTrue('lolnet.org' in foo.cors_origins_for('GET'))

        foo.add_view('POST', _stub)
        self.assertFalse('lolnet.org' in foo.cors_origins_for('POST'))

    def test_credential_support_can_be_enabled(self):
        foo = Service(name='foo', path='/foo', cors_credentials=True)
        self.assertTrue(foo.cors_support_credentials())

    def test_credential_support_is_disabled_by_default(self):
        foo = Service(name='foo', path='/foo')
        self.assertFalse(foo.cors_support_credentials())

    def test_per_method_credential_support(self):
        foo = Service(name='foo', path='/foo')
        foo.add_view('GET', _stub, cors_credentials=True)
        foo.add_view('POST', _stub)
        self.assertTrue(foo.cors_support_credentials('GET'))
        self.assertFalse(foo.cors_support_credentials('POST'))

    def test_method_takes_precendence_for_credential_support(self):
        foo = Service(name='foo', path='/foo', cors_credentials=True)
        foo.add_view('GET', _stub, cors_credentials=False)
        self.assertFalse(foo.cors_support_credentials('GET'))

    def test_max_age_can_be_defined(self):
        foo = Service(name='foo', path='/foo', cors_max_age=42)
        self.assertEquals(foo.cors_max_age_for(), 42)

    def test_max_age_can_be_different_dependeing_methods(self):
        foo = Service(name='foo', path='/foo', cors_max_age=42)
        foo.add_view('GET', _stub)
        foo.add_view('POST', _stub, cors_max_age=32)
        foo.add_view('PUT', _stub, cors_max_age=7)

        self.assertEquals(foo.cors_max_age_for('GET'), 42)
        self.assertEquals(foo.cors_max_age_for('POST'), 32)
        self.assertEquals(foo.cors_max_age_for('PUT'), 7)

    def test_cors_policy(self):
        policy = {'origins': ('foo', 'bar', 'baz')}
        foo = Service(name='foo', path='/foo', cors_policy=policy)
        self.assertTrue('foo' in foo.cors_supported_origins)
        self.assertTrue('bar' in foo.cors_supported_origins)
        self.assertTrue('baz' in foo.cors_supported_origins)

    def test_cors_policy_can_be_overwritten(self):
        policy = {'origins': ('foo', 'bar', 'baz')}
        foo = Service(name='foo', path='/foo', cors_origins=(),
                      cors_policy=policy)
        self.assertEquals(len(foo.cors_supported_origins), 0)
