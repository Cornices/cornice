# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from webob.dec import wsgify
from webob import exc
from pyramid.httpexceptions import HTTPException


class CatchErrors(object):
    def __init__(self, app):
        self.app = app
        if hasattr(app, 'registry'):
            self.registry = app.registry

    @wsgify
    def __call__(self, request):
        try:
            return request.get_response(self.app)
        except (exc.HTTPException, HTTPException), e:
            return e
