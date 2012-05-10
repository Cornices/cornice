# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import simplejson as json
from docutils import core
from docutils.writers.html4css1 import Writer, HTMLTranslator
import docutils

from pyramid import httpexceptions as exc
from pyramid.response import Response


__all__ = ['rst2html', 'rst2node', 'json_renderer']


class _HTMLFragmentTranslator(HTMLTranslator):
    def __init__(self, document):
        HTMLTranslator.__init__(self, document)
        self.head_prefix = ['', '', '', '', '']
        self.body_prefix = []
        self.body_suffix = []
        self.stylesheet = []

    def astext(self):
        return ''.join(self.body)


class _FragmentWriter(Writer):
    translator_class = _HTMLFragmentTranslator

    def apply_template(self):
        subs = self.interpolation_dict()
        return subs['body']


def rst2html(data):
    """Converts a reStructuredText into its HTML
    """
    if not data:
        return ''
    return core.publish_string(data, writer=_FragmentWriter())


class Env(object):
    temp_data = {}
    docname = ''


def rst2node(data):
    """Converts a reStructuredText into its node
    """
    if not data:
        return
    parser = docutils.parsers.rst.Parser()
    document = docutils.utils.new_document('<>')
    document.settings = docutils.frontend.OptionParser().get_default_values()
    document.settings.tab_width = 4
    document.settings.pep_references = False
    document.settings.rfc_references = False
    document.settings.env = Env()
    parser.parse(data, document)
    if len(document.children) == 1:
        return document.children[0]
    else:
        par = docutils.nodes.paragraph()
        for child in document.children:
            par += child
        return par


def json_renderer(helper):
    return _JsonRenderer()


class _JsonRenderer(object):
    def __call__(self, data, context):
        response = context['request'].response
        response.content_type = 'application/json'
        return json.dumps(data, use_decimal=True)


def to_list(obj):
    """Convert an object to a list if it is not already one"""
    if not isinstance(obj, (list, tuple)):
        obj = (obj,)
    return obj


class _JSONError(exc.HTTPError):
    def __init__(self, errors, status=400):
        body = {'status': 'error', 'errors': errors}
        Response.__init__(self, json.dumps(body, use_decimal=True))
        self.status = status
        self.content_type = 'application/json'


def json_error(errors):
    """Returns an HTTPError with the given status and message.

    The HTTP error content type is "application/json"
    """
    return _JSONError(errors, errors.status)


def match_accept_header(func, context, request):
    acceptable = func(request)
    # attach the accepted content types to the request
    request.info['acceptable'] = acceptable
    return request.accept.best_match(acceptable) is not None


def extract_request_data(request):
    """extract the different parts of the data from the request, and return
    them as a list of (querystring, headers, body, path)
    """
    # XXX In the body, we're only handling JSON for now.
    if request.body:
        try:
            body = json.loads(request.body)
        except ValueError, e:
            request.errors.add('body', None, e.message)
            body = {}
    else:
        body = {}

    return request.GET, request.headers, body, request.matchdict
