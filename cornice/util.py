# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Cornice (Sagrada)
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
from webob import exc
import simplejson as json
from docutils import core
from docutils.writers.html4css1 import Writer, HTMLTranslator
import docutils


__all__ = ['rst2html']


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


def code2exception(code, detail):
    """Transforms a code + detail into a WebOb exception"""
    if code == 400:
        return exc.HTTPBadRequest(detail)
    if code == 401:
        return exc.HTTPUnauthorized(detail)
    if code == 402:
        return exc.HTTPPaymentRequired(detail)
    if code == 403:
        return exc.HTTPForbidden(detail)
    if code == 404:
        return exc.HTTPNotFound(detail)
    if code == 405:
        return exc.HTTPMethodNotAllowed(detail)
    if code == 406:
        return exc.HTTPNotAcceptable(detail)
    if code == 407:
        return exc.HTTPProxyAuthenticationRequired(detail)
    if code == 408:
        return exc.HTTPRequestTimeout(detail)
    if code == 409:
        return exc.HTTPConflict(detail)
    if code == 410:
        return exc.HTTPGone(detail)
    if code == 411:
        return exc.HTTPLengthRequired(detail)
    if code == 412:
        return exc.HTTPPreconditionFailed(detail)
    if code == 413:
        return exc.HTTPRequestEntityTooLarge(detail)
    if code == 414:
        return exc.HTTPRequestURITooLong(detail)
    if code == 415:
        return exc.HTTPUnsupportedMediaType(detail)
    if code == 416:
        return exc.HTTPRequestRangeNotSatisfiable(detail)
    if code == 417:
        return exc.HTTPExpectationFailed(detail)
    if code == 500:
        return exc.HTTPInternalServerError(detail)
    if code == 501:
        return exc.HTTPNotImplemented(detail)
    if code == 502:
        return exc.HTTPBadGateway(detail)
    if code == 503:
        return exc.HTTPServiceUnavailable(detail)
    if code == 504:
        return exc.HTTPGatewayTimeout(detail)
    if code == 505:
        return exc.HTTPVersionNotSupported(detail)

    raise NotImplementedError(code)
