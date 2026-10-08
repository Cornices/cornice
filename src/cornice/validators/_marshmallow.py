# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import inspect
from contextvars import ContextVar

from cornice.validators._marshmallow_compat import EXCLUDE, set_schema_context


cornice_request: ContextVar = ContextVar("cornice_request")


def _generate_marshmallow_validator(location):
    """
    Generate a marshmallow validator for data from the given location.

    :param location: The location in the request to find the data to be
        validated, such as "body" or "querystring".
    :type location: str
    :return: Returns a callable that will validate the request at the given
        location.
    :rtype: callable
    """

    def _validator(request, schema=None, deserializer=None, **kwargs):
        """
        Validate the location against the schema defined on the service.

        The content of the location is deserialized, validated and stored in
        the ``request.validated`` attribute.

        Keyword arguments to be included when initialising the marshmallow
        schema can be passed as a dict in ``kwargs['schema_kwargs']`` variable.

        .. note::

            If no schema is defined, this validator does nothing.

        :param request: Current request
        :type request: :class:`~pyramid:pyramid.request.Request`

        :param schema: The marshmallow schema
        :param deserializer: Optional deserializer, defaults to
            :func:`cornice.validators.extract_cstruct`
        """
        import marshmallow
        import marshmallow.schema

        if schema is None:
            return

        # see if the user wants to set any keyword arguments for their schema
        schema_kwargs = kwargs.get("schema_kwargs", {})
        schema = _instantiate_schema(schema, **schema_kwargs)

        class ValidatedField(marshmallow.fields.Field):
            def _deserialize(self, value, attr, data, **kwargs):
                cornice_request.set(request)
                set_schema_context(schema, "request", request)
                deserialized = schema.load(value)
                return deserialized

        class Meta(object):
            unknown = EXCLUDE

        class RequestSchemaMeta(marshmallow.schema.SchemaMeta):
            """
            A metaclass that will inject a location class attribute into
            RequestSchema.
            """

            def __new__(cls, name, bases, class_attrs):
                """
                Instantiate the RequestSchema class.

                :param name: The name of the class we are instantiating. Will
                    be "RequestSchema".
                :type name: str
                :param bases: The class's superclasses.
                :type bases: tuple
                :param dct: The class's class attributes.
                :type dct: dict
                """

                class_attrs[location] = ValidatedField(required=True, data_key=location)
                class_attrs["Meta"] = Meta
                return type(name, bases, class_attrs)

        class RequestSchema(marshmallow.Schema, metaclass=RequestSchemaMeta):  # noqa
            """A schema to validate the request's location attributes."""

            pass

        validator(request, RequestSchema, deserializer, **kwargs)
        request.validated = request.validated.get(location, {})

    return _validator


body_validator = _generate_marshmallow_validator("body")
headers_validator = _generate_marshmallow_validator("header")
path_validator = _generate_marshmallow_validator("path")
querystring_validator = _generate_marshmallow_validator("querystring")


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

    :param schema: The marshmallow schema
    :param deserializer: Optional deserializer, defaults to
        :func:`cornice.validators.extract_cstruct`
    """
    import marshmallow

    from cornice.validators import extract_cstruct

    if deserializer is None:
        deserializer = extract_cstruct

    if schema is None:
        return

    schema = _instantiate_schema(schema)
    cornice_request.set(request)
    set_schema_context(schema, "request", request)

    cstruct = deserializer(request)
    try:
        deserialized = schema.load(cstruct)
    except marshmallow.ValidationError as err:
        normalized_errors = err.messages
        for location, details in normalized_errors.items():
            location = location if location != "_schema" else ""
            if hasattr(details, "items"):
                for subfield, msg in details.items():
                    request.errors.add(location, subfield, msg)
            else:
                request.errors.add(location, location, details)
    else:
        request.validated.update(deserialized)


def _instantiate_schema(schema, **kwargs):
    """
    Returns an object of the given marshmallow schema.

    :param schema: The marshmallow schema class with which the request should
        be validated
    :param kwargs: The keyword arguments that will be provided to the
        marshmallow schema's constructor
    :return: The object of the marshmallow schema
    """
    if not inspect.isclass(schema):
        raise ValueError("You need to pass Marshmallow class instead of schema instance")
    return schema(**kwargs)
