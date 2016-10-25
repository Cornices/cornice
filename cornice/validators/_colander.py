# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


def body_validator(request, schema=None, deserializer=None, **kwargs):
    """
    Validate the body against the schema defined on the service.

    The content of the body is deserialized, validated and stored in the
    ``request.validated`` attribute.

    .. note::

        If no schema is defined, this validator does nothing.

    :param request: Current request
    :type request: :class:`~pyramid:pyramid.request.Request`

    :param schema: The Colander schema class
    :param deserializer: Optional deserializer, defaults to
        :func:`cornice.validators.extract_cstruct`
    """
    import colander

    if schema is not None:
        class RequestSchema(colander.MappingSchema):
            body = schema()

            def deserialize(self, cstruct=colander.null):
                appstruct = super(RequestSchema, self).deserialize(cstruct)
                return appstruct['body']
        schema = RequestSchema
    return validator(request, schema, deserializer, **kwargs)


def validator(request, schema=None, deserializer=None, **kwargs):
    """
    Validate the full request against the schema defined on the service.

    Each attribute of the request is deserialized, validated and stored in the
    ``request.validated`` attribute
    (eg. body in ``request.validated['body']``).

    .. note::

        If no schema is defined, this validator does nothing.

    :param request: Current request
    :type request: :class:`~pyramid:pyramid.request.Request`

    :param schema: The Colander schema class
    :param deserializer: Optional deserializer, defaults to
        :func:`cornice.validators.extract_cstruct`
    """
    import colander
    from cornice.validators import extract_cstruct

    if deserializer is None:
        deserializer = extract_cstruct

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
