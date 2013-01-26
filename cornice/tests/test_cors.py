from pyramid import testing
from webtest import TestApp

from cornice.service import Service
from cornice.tests.support import TestCase, CatchErrors


squirel = Service(path='/squirel', name='squirel', cors_origins=('foobar',))
spam = Service(path='/spam', name='spam', cors_origins=('*',))
eggs = Service(path='/eggs', name='egg', cors_origins=('*'),
               cors_expose_all_headers=False)


@squirel.get(cors_origins=('notmyidea.org',))
def get_squirel(request):
    return "squirels"


@squirel.post(cors_enabled=False, cors_headers=('X-Another-Header'))
def post_squirel(request):
    return "moar squirels (take care)"


@squirel.put(cors_headers=('X-My-Header',))
def put_squirel(request):
    return "squirels!"


@spam.get(cors_credentials=True, cors_headers=('X-My-Header'),
          cors_max_age=42)
def gimme_some_spam_please(request):
    return 'spam'


@spam.post()
def moar_spam(request):
    return 'moar spam'


class TestCORS(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_cors")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

        def tearDown(self):
            testing.tearDown()

    def test_preflight_missing_headers(self):
        # we should have an OPTION method defined.
        # If we just try to reach it, without using correct headers:
        # "Access-Control-Request-Method"or without the "Origin" header,
        # we should get a 400.
        resp = self.app.options('/squirel', status=400)
        self.assertEquals(len(resp.json['errors']), 2)

    def test_preflight_missing_origin(self):

        resp = self.app.options(
            '/squirel',
            headers={'Access-Control-Request-Method': 'GET'},
            status=400)
        self.assertEquals(len(resp.json['errors']), 1)

    def test_preflight_missing_request_method(self):

        resp = self.app.options(
            '/squirel',
            headers={'Origin': 'foobar.org'},
            status=400)

        self.assertEquals(len(resp.json['errors']), 1)

    def test_preflight_incorrect_origin(self):
        # we put "lolnet.org" where only "notmyidea.org" is authorized
        resp = self.app.options(
            '/squirel',
            headers={'Origin': 'lolnet.org',
                     'Access-Control-Request-Method': 'GET'},
            status=400)
        self.assertEquals(len(resp.json['errors']), 1)

    def test_preflight_correct_origin(self):
        resp = self.app.options(
            '/squirel',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'GET'})
        self.assertEquals(
            resp.headers['Access-Control-Allow-Origin'],
            'notmyidea.org')

        allowed_methods = (resp.headers['Access-Control-Allow-Methods']
                           .split(','))

        self.assertNotIn('POST', allowed_methods)
        self.assertIn('GET', allowed_methods)
        self.assertIn('PUT', allowed_methods)
        self.assertIn('HEAD', allowed_methods)

        allowed_headers = (resp.headers['Access-Control-Allow-Headers']
                           .split(','))

        self.assertIn('X-My-Header', allowed_headers)
        self.assertNotIn('X-Another-Header', allowed_headers)

    def test_preflight_deactivated_method(self):
        self.app.options('/squirel',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'POST'},
            status=400)

    def test_preflight_origin_not_allowed_for_method(self):
        self.app.options('/squirel',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'PUT'},
            status=400)

    def test_preflight_credentials_are_supported(self):
        resp = self.app.options('/spam',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'GET'})

        self.assertIn('Access-Control-Allow-Credentials', resp.headers)
        self.assertEquals(resp.headers['Access-Control-Allow-Credentials'],
                          'true')

    def test_preflight_credentials_header_not_included_when_not_needed(self):
        resp = self.app.options('/spam',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'POST'})

        self.assertNotIn('Access-Control-Allow-Credentials', resp.headers)

    def test_preflight_contains_max_age(self):
        resp = self.app.options('/spam',
                headers={'Origin': 'notmyidea.org',
                         'Access-Control-Request-Method': 'GET'})

        self.assertIn('Access-Control-Max-Age', resp.headers)
        self.assertEquals(resp.headers['Access-Control-Max-Age'], '42')

    def test_resp_dont_include_allow_origin(self):
        resp = self.app.get('/squirel')  # omit the Origin header
        self.assertNotIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEquals(resp.json, 'squirels')

    def test_responses_include_an_allow_origin_header(self):
        resp = self.app.get('/squirel', headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEquals(resp.headers['Access-Control-Allow-Origin'],
                          'notmyidea.org')

    def test_credentials_are_included(self):
        resp = self.app.get('/spam', headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Credentials', resp.headers)
        self.assertEquals(resp.headers['Access-Control-Allow-Credentials'],
                          'true')

    def test_headers_are_exposed(self):
        resp = self.app.get('/squirel', headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Expose-Headers', resp.headers)

        headers = resp.headers['Access-Control-Expose-Headers'].split(',')
        self.assertIn('X-My-Header', headers)

    def test_preflight_request_headers_are_included(self):
        resp = self.app.options('/squirel',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'GET',
                     'Access-Control-Request-Headers': 'foo,bar,baz'})

        # per default, they should be authorized, and returned in the list of
        # authorized headers
        headers = resp.headers['Access-Control-Allow-Headers'].split(',')
        self.assertIn('foo', headers)
        self.assertIn('bar', headers)
        self.assertIn('baz', headers)

    def test_preflight_request_headers_isnt_too_permissive(self):
        self.app.options('/eggs',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'GET',
                     'Access-Control-Request-Headers': 'foo,bar,baz'},
            status=400)

    def test_preflight_headers_arent_case_sensitive(self):
        self.app.options('/spam', headers={
            'Origin': 'notmyidea.org',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'x-my-header', })
