"""Cornice Swagger 2.0 documentor"""

import re
import cornice.ext.swagger_model
import cornice.service
import cornice.util

try:
    from colander import drop, deferred
except:
    deferred, drop = "GET_COLANDER_DROP", "GET_COLANDER_DEFFERED"


def schema_to_parameters(schema, service=None):
    """ Convert Colander Schema object to a Swagger Parameter dict.
    Provide optional Cornice Service to detect if parameter is in Path
    """
    # We want to get all the attributes which aren't specifically
    # for the body, because swagger deserves them a special
    # treatment.
    ret = []

    for location in ("path", "header", "querystring"):
        attributes = schema.get_attributes(location=location)
        if attributes and location != "body":
            for attr in attributes:
                parameter = dict()
                name = attr.name
                paramType = location
                if paramType == "querystring":
                    if service and "{%s}" % name in service.path:
                        paramType = "path"
                    else:
                        paramType = "query"
                parameter["in"] = paramType
                parameter["name"] = name
                if hasattr(attr, "description"):
                    parameter["description"] = getattr(attr, "description")
                missing = getattr(attr, 'missing')
                parameter['required'] = False if (missing == drop or isinstance(missing, deferred)) else True

                type_ = ""
                if hasattr(attr, "typ"):
                    type_ = attr.typ.__class__.__name__

                parameter["type"] = type_

            ret.append(parameter)

    # body
    swag = cornice.ext.swagger_model.SwaggerModel()
    entry = swag.to_swagger(schema.colander_schema)

    if swag.models:
        parameter = dict()
        parameter["in"] = "body"
        parameter["name"] = "body"
        parameter["description"] = schema.__doc__
        parameter["schema"] = entry
        ret.append(parameter)
    return ret, swag.models


# At some point, we may have some operation parameters which we"d
# like to update with a new (only if their names are the same
# and in the same location)
def _update_op_param(operation, new):
    if "name" not in new or "in" not in new:
        return None
    for old in operation["parameters"]:
        if "name" in old and new["name"] == old[
                "name"] and "in" in old and new["in"] == old["in"]:
            old.update(new.copy())
            return True
    # We've made it through the loop without finding a match, so
    # add it
    operation["parameters"].append(new.copy())
    return False


def generate_swagger_spec(services, title, version, **kwargs):
    """Utility to turn cornice web services into a Swagger-readable file.

    See https://helloreverb.com/developers/swagger for more information.
    https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md
    """

    doc = {
        "swagger": "2.0",
        "info": {
            "title": title,
            "version": str(version)
        },
        "paths": {},
        "tags": [],
        "definitions": {},
        "basePath": kwargs.get("base_path", "/")
    }

    # Handle all the non-required args if passed per spec:
    # https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#swagger-object-
    for k, v in list(kwargs.items()):
        doc[k] = v

    # To control uniqueness of our tags, make a dict
    tags_dict = dict()
    definitions = {}

    # sort our services first

    # Loop through all our service endpoint resources
    for service in services:
        # Create a tag obejct to add to our base doc later
        tag_name = service.path.split("/")[1]
        service_tag = dict(name=tag_name)

        path = {"parameters": []}

        # Get path parameters from looking at the path
        service_path = service.path
        parameter = dict()

        # Loop through all our verb operations for this service
        for method, view, args in service.definitions:
            if method == "HEAD" and not kwargs.get("head", True):
                continue

            if cornice.util.is_string(view):
                if 'klass' in args:
                    ob = args['klass']
                    view_ = getattr(ob, view.lower())
                    service_tag["description"] = cornice.util.trim(
                        ob.__doc__ or "")
                    docstring = cornice.util.trim(view_.__doc__ or "")
            else:
                docstring = cornice.util.trim(view.__doc__ or "")
                ob = cornice.util.get_class_that_defined_method(view)
                service_tag["description"] = cornice.util.trim(
                    ob.__doc__ or "")

            operation = {
                "responses": {
                    "default": {
                        "description": "UNDOCUMENTED RESPONSE"}},
                "tags": [tag_name],
                "parameters": []}

            # The Swagger "summary" will come from the docstring
            operation["summary"] = docstring

            # Do we have paramters in the path?
            if "{" in service_path:
                service_path_list = service_path.split("{")
                for part in service_path_list:
                    match = re.search("(.*)\}", part)
                    if match is not None:
                        parameter["name"] = match.group(1)
                        parameter["in"] = "path"
                        parameter["required"] = True
                        parameter["type"] = "string"
                        _update_op_param(operation, parameter)

            # What do we produce?
            if "json" in args["renderer"]:  # allows for "json" or "simplejson"
                operation["produces"] = ["application/json"]
            elif args["renderer"] == "xml":
                operation["produces"] = ["text/xml"]

            # What do we consume?
            if "content_type" in args:
                operation["consumes"] = [args["content_type"]]

            # A Colander Schema can be used to extract parameters.  If present,
            # it always updates discovered path parameters, yet is still
            # updated with @swagger.operation(parameters) if present
            if "schema" in args:
                schema = args["schema"]
                parameters, definition = schema_to_parameters(schema, service)

                if definition:
                    definitions.update(definition)
                for p in parameters:
                    _update_op_param(operation, p)

            # Do some cleanup
            if len(operation["parameters"]) == 0:
                del operation["parameters"]
            path[method.lower()] = operation.copy()
        if len(path["parameters"]) == 0:
            del path["parameters"]
        doc["paths"][service.path] = path
        if tag_name in tags_dict:
            tags_dict[tag_name].update(service_tag)
        else:
            tags_dict[tag_name] = service_tag
    # Extract tags list from our dict
    for k, v in list(tags_dict.items()):
        doc["tags"].append(v)
    doc["definitions"] = definitions
    return doc
