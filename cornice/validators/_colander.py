# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import colander


def body_validator(request, **kwargs):
    schema = kwargs.get('schema')
    if schema:
        class RequestSchema(colander.MappingSchema):
            body = schema()

            def deserialize(self, cstruct=colander.null):
                appstruct = super(RequestSchema, self).deserialize(cstruct)
                return appstruct['body']
        kwargs['schema'] = RequestSchema
    return validator(request, **kwargs)


def validator(request, deserializer=None, **kw):
    from cornice.validators import extract_cstruct

    if deserializer is None:
        deserializer = extract_cstruct

    schema = kw.get('schema')

    if schema is None:
        raise TypeError('This validator cannot work without a schema')

    schema = schema()
    cstruct = deserializer(request)
    try:
        deserialized = schema.deserialize(cstruct)
        request.validated.update(deserialized)
    except colander.Invalid as e:
        translate = request.localizer.translate
        error_dict = e.asdict(translate=translate)
        for name, msg in error_dict.items():
            prefixed = name.split('.', 1)

            if len(prefixed) == 1:
                location = name
                field = ''
            else:
                location = prefixed[0]
                field = prefixed[1]

            request.errors.add(location, field, error_dict[name])
