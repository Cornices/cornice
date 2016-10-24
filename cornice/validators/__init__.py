# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from webob.multidict import MultiDict
from cornice.validators._colander import (
    validator as colander_validator,
    body_validator as colander_body_validator)


__all__ = ['colander_validator',
           'colander_body_validator',
           'extract_cstruct',
           'DEFAULT_VALIDATORS',
           'DEFAULT_FILTERS']


DEFAULT_VALIDATORS = []
DEFAULT_FILTERS = []


def extract_cstruct(request):
    if request.content_type == 'application/x-www-form-urlencoded':
        body = request.POST.mixed()

    elif request.content_type and request.content_type != 'application/json':
        body = request.body
    else:
        if request.body:
            try:
                body = request.json_body
            except ValueError as e:
                request.errors.add('body', '', 'Invalid JSON: %s' % e)
                return {}
            else:
                if not hasattr(body, 'items'):
                    request.errors.add('body', '', 'Should be a JSON object')
                    return {}
        else:
            body = {}

    cstruct = {'method': request.method,
               'url': request.url,
               'path': request.path,
               'body': body}

    for sub, attr in (('querystring', 'GET'),
                      ('header', 'headers'),
                      ('cookies', 'cookies')):
        data = getattr(request, attr)
        if isinstance(data, MultiDict):
            data = data.mixed()
        else:
            data = dict(data)
        cstruct[sub] = data

    return cstruct
