# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.util import extract_request_data


try:
    import colander
except ImportError:
    pass
else:

    class StrictMappingSchema(colander.MappingSchema):
        @staticmethod
        def schema_type():
            return colander.Mapping(unknown='raise')

    class CorniceSchema(colander.MappingSchema):
        querystring = StrictMappingSchema(
            default=colander.drop
        )
        headers = StrictMappingSchema(
            default=colander.drop
        )
        body = StrictMappingSchema(
            default=colander.drop
        )
        path = StrictMappingSchema(
            default=colander.drop
        )


def validate_colander_schema(schema, request):
    """Validates that the request conforms to the given schema"""
    from colander import Invalid, Sequence, drop, null, Mapping

    if not isinstance(schema, CorniceSchema):
        raise TypeError(
            'schema type is not a CorniceSchema'
        )

    # compile the querystring, headers, body, path into an appstruct
    #  for consumption by colander for validation
    qs, headers, body, path = extract_request_data(request)
    initial_appstruct = {
        'querystring': qs,
        'headers': headers,
        'body': body,
        'path': path,
    }

    try:
        cstruct = schema.serialize(initial_appstruct)
        appstruct = schema.deserialize(cstruct)
    except colander.Invalid as e:
        for component_path, msg in e.asdict().items():
            (location, _, name) = component_path.partition('.')
            request.errors.add(
                location, name, msg
            )
    else:
        request.validated.update(appstruct)
