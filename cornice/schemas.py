# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid.compat import is_nonstr_iter

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
        querystring = StrictMappingSchema()
        headers = StrictMappingSchema()
        body = StrictMappingSchema()
        path = StrictMappingSchema()

    def simple_cstruct_serialize(val):
        """ cstruct is colander's internal use format which is a
        series of nested dicts, lists, and tuples with only str values
        as the "leaf" values.  If this method will try to recursively
        go through a given value and convert all dict-like objects into
        dicts, convert iterables that aren't dict-like into lists, and
        convert everything else into a string.
        """
        try:
            # try dict-like interpretation
            result = {}
            for k in val.keys():
                result[k] = simple_cstruct_serialize(val[k])
            return result
        except (TypeError, AttributeError):
            if is_nonstr_iter(val):
                # try iterable interpretation
                result = []
                for k in val:
                    result.append(simple_cstruct_serialize(k))
                return result
            else:
                return str(val)


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
        cstruct = simple_cstruct_serialize(initial_appstruct)
        appstruct = schema.deserialize(cstruct)
    except colander.Invalid as e:
        for component_path, msg in e.asdict().items():
            (location, _, name) = component_path.partition('.')
            request.errors.add(
                location, name, msg
            )
    else:
        request.validated.update(appstruct)
