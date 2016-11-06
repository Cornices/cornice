# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import colander
import collections
import webob.multidict
import inspect
import warnings


def body_validator(request, schema=None, deserializer=None, **kwargs):
    """
    Validate the body against the schema defined on the service.

    The content of the body is deserialized, validated and stored in the
    ``request.validated`` attribute.

    .. note::

        If no schema is defined, this validator does nothing.

    :param request: Current request
    :type request: :class:`~pyramid:pyramid.request.Request`

    :param schema: The Colander schema
    :param deserializer: Optional deserializer, defaults to
        :func:`cornice.validators.extract_cstruct`
    """
    import colander

    if schema is None:
        return

    class RequestSchema(colander.MappingSchema):
        body = _ensure_instantiated(schema)

        def deserialize(self, cstruct=colander.null):
            appstruct = super(RequestSchema, self).deserialize(cstruct)
            return appstruct['body']

    validator(request, RequestSchema(), deserializer, **kwargs)


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

    :param schema: The Colander schema
    :param deserializer: Optional deserializer, defaults to
        :func:`cornice.validators.extract_cstruct`
    """
    import colander
    from cornice.validators import extract_cstruct

    if deserializer is None:
        deserializer = extract_cstruct

    if schema is None:
        return

    schema = _ensure_instantiated(schema)
    cstruct = _none_to_null(deserializer(request))

    try:
        deserialized = schema.deserialize(cstruct)
    except colander.Invalid as e:
        translate = request.localizer.translate
        error_dict = e.asdict(translate=translate)
        for name, msg in error_dict.items():
            location, _, field = name.partition('.')
            request.errors.add(location, field, msg)
    else:
        request.validated.update(deserialized)


def _ensure_instantiated(schema):
    if inspect.isclass(schema):
        warnings.warn(
            "Setting schema to a class is deprecated. "
            " Set schema to an instance instead.",
            DeprecationWarning,
            stacklevel=2)
        schema = schema()
    return schema


def _none_to_null(data):
    """Replace all `None` values with `colander.null` in the given
    structure because `deserialize` expects `colander.null`.
    """
    if data is None:
        return colander.null
    elif not data:
        return data
    elif isinstance(data, webob.multidict.MultiDict):
        new_data = webob.multidict.MultiDict()
        for key in data:
            values = data.getall(key)
            for value in values:
                new_data[key] = _none_to_null(value)
        data = new_data
    elif isinstance(data, collections.Mapping):
        for key in data:
            data[key] = _none_to_null(data[key])
    elif isinstance(data, list):
        data = [_none_to_null(value) for value in data]
    elif isinstance(data, set):
        data = (_none_to_null(value) for value in data)
    return data
