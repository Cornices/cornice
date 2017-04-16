"""Cornice Swagger 2.0 documentor"""
__author__ = 'jhaury'
__credits__=['jhaury']

import re


##################
#   DECORATORS   #
##################
# Decorate Cornice Service/Resource Classes as Swagger Paths and Pyramid View methods as Swagger Operations
def path(**kwargs):
    """
    This dedorator marks a cornice class as a swagger path so that we can easily
    extract attributes from it.
    It saves the decorator's key-values at the function level so we can later
    extract them later when generate_swagger_spec

    Credits go to flask_restful_swagger
    """
    def inner(f):
        f.__swagger_attr = kwargs
        return f


def operation(**kwargs):
    """
    This dedorator marks a method as a swagger operation so that we can easily
    extract attributes from it.
    It saves the decorator's key-values at the function level so we can later
    extract them later when generate_swagger_spec

    Credits go to flask_restful_swagger
    """
    def inner(f):
        f.__swagger_attr = kwargs
        return f
    return inner


##################
#   CONVERTORS   #
##################
def schema2parameter(schema, service=None):
    """ Convert Colander Schema object to a Swagger Parameter dict.
    Provide optional Cornice Service to detect if parameter is in Path
    """
    # We want to get all the attributes which aren't specifically
    # for the body, because swagger deserves them a special
    # treatment (see after).
    attributes = schema.get_attributes(location=('path', 'querystring', 'header'))

    #for name, values in attributes.items():
    for attr in attributes:
        parameter = dict()
        name = attr.name
        paramType = getattr(attr, 'location')
        if paramType == 'querystring':
            if service and '{%s}' % name in service.path:
                paramType = 'path'
            else:
                paramType = 'query'
        parameter['in'] = paramType
        parameter['name'] = name
        if hasattr(attr, 'description'):
            parameter['description'] = getattr(attr,'description')
        parameter['required'] = getattr(attr,'required')

        # If the type is a primitive one, just put in in the "type"
        # field.
        primitive_values = {'str': 'string'}
        type_ = ''
        if getattr(attr, 'type') in primitive_values:
            type_ = primitive_values[getattr(attr, 'type')]
        else:
            # Otherwise, we trust our Schema type matches a valid Swagger type.
            type_ = getattr(attr, 'type')
        parameter['type'] = type_

        #TODO parse body and make a JSON schema etc to look for
        # Get the parameters for the body.

        return parameter

def multidict2matchdict(request, parameters, validate=True):
    """ Takes multidict of request.params and list of Swagger Parameters then returns something like a matchdict:
    1) Values are None if they weren't in guerystring
    2) Values are lists only if corresponding Parameter's collectionFormat is 'multi', else provides last value

    Multidict is a WebOb structure used by Pyramid:
    https://webob.readthedocs.org/en/latest/#multidict

    Matchdict is a Pyramid structure:
    http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/urldispatch.html#matchdict
    """
    qs = request.params  # querystring multiduct
    match_dict = dict()
    for param in parameters:
        if param['in'] == 'query':
            # Handle "multi" collectionTypes in a special way
            if 'collectionType' in param and param['collectionType'] == 'multi':
                match_dict[param['name']] = qs.getall(param['name'])
            elif param['name'] in qs:
                match_dict[param['name']] = qs[param['name']]
            else:
                match_dict[param['name']] = None
    return match_dict

def col2swag_type(col_type):
    """ Converts a primitive type used by SQLAlchemy Columns, to Swagger types
    """
    col_type = col_type.lower()
    if col_type in ['text', 'string']:
        return {"type": "string"}
    elif col_type in ['float', 'numeric', 'real']:
        return {"type": "number"}
    elif col_type in ['int', 'bigint', 'biginteger', 'smallinteger' ]:
        return {"type": "integer"}
    elif col_type in ['bool', 'boolean']:
        return {"type": 'boolean'}
    elif col_type[-2:] == '[]':
        return {"type": "array", "items": col2swag_type(col_type[:-2])}
    else:
        return {"type": 'string'}

def sqa2swag_model(models):
    """ Interprets SQL Alchemy model and makes a Swagger Response Model
    Code based on dnordberg's code at https://gist.github.com/dnordberg/5661696
    """
    # All DB columns WILL come back, so make them required
    required = []
    json_model = {}
    json_properties = {}
    title = []
    if not isinstance(models, list):
        models = [models]
    for model in models:
        # We may be using a metadata table without the __table__ attribute, so plan accordingly
        if hasattr(model, '__table__'):
            table = model.__table__
        else:
            table = model
        properties = table.columns.items()
        title.append(str(table))
        for propkey, prop in properties:
            try:
                json_properties[propkey] = col2swag_type(str(prop.type))
                required.append(propkey)
            except:
                pass
    json_model["properties"] = json_properties
    json_model['required'] = list(set(required))
    json_model['title'] = str(title)
    return json_model

#TODO make multidict2matchdict for schema objects.

##############################
#  SWAGGER SPEC GENERATORS   #
##############################
def generate_swagger_spec(services, title, version, **kwargs):
    """Utility to turn cornice web services into a Swagger-readable file.

    See https://helloreverb.com/developers/swagger for more information.
    https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md
    """

    doc = {
        'swagger': '2.0',
        'info': {
            'title': title,
            'version': str(version)
        },
        'paths': {},
        'tags': []
    }

    # Handle all the non-required args if passed per spec:
    # https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#swagger-object-
    for k, v in kwargs.iteritems():
        doc[k] = v

    # To control uniqueness of our tags, make a dict
    tags_dict = dict()

    # sort our services first

    # Loop through all our service endpoint resources
    for service in services:
        # Create a tag obejct to add to our base doc later
        tag_name = service.path.split('/')[1]
        service_tag = dict(name=tag_name)

        path = {'parameters': []}
        #if service.description:
        #    api['description'] = service.description

        # Get path parameters from looking at, ya know, the path
        service_path = service.path
        parameter = dict()

        # Do we have parameters in the path?
        if '{' in service_path:
            service_path_list = service_path.split('{')
            for part in service_path_list:
                match = re.search('(.*)\}', part)
                if match is not None:
                    parameter['name'] = match.group(1)
                    parameter['in'] = 'path'
                    parameter['required'] = True
                    # TODO: Make a way to set the type
                    parameter['type'] = 'string'
                    path['parameters'].append(parameter.copy())

        # Loop through all our verb operations for this service
        for method, view, args in service.definitions:
            # Cornice service definitions are provided for all methods, even ones not implemented.
            # We can filter these based on "view"
            if not isinstance(view, str):
                continue

            #Also, match our method and views (HEAD gets greedy with GET)
            if view.split('_')[-1] != method.lower():
                continue


            # Get associated parent class for this operation
            op_klass = args['klass']
            # Set our tag description while we're here
            if op_klass.__doc__ is not None:
                service_tag['description'] = op_klass.__doc__.strip()

            # Get the method associated wtih this operation
            op_method = op_klass.__dict__[view] if view in op_klass.__dict__ else None
            operation = {
                'responses': {'default': {'description': 'UNDOCUMENTED RESPONSE'}},
                'tags': [tag_name],
                'parameters': []
            }

            #  At some point, we may have some operation parameters which we'd like to update with a new_param
            # (only if their names are the same and in the same location)
            def update_op_param(new_param):
                if 'name' not in new_param or 'in' not in new_param:
                    return None
                for old_param in operation['parameters']:
                    if 'name' in old_param and new_param['name'] == old_param['name'] and \
                         'in' in old_param and new_param['in'] == old_param['in']:
                        old_param.update(new_param.copy())
                        return True
                # We've made it through the loop without finding a match, so add it
                operation['parameters'].append(new_param.copy())
                return False



            # Do we have paramters in the path?
            if '{' in service_path:
                service_path_list = service_path.split('{')
                for part in service_path_list:
                    match = re.search('(.*)\}', part)
                    if match is not None:
                        parameter['name'] = match.group(1)
                        parameter['in'] = 'path'
                        parameter['required'] = True
                        parameter['type'] = 'string'
                        update_op_param(parameter)
                        #operation['parameters'].append(parameter.copy())

            # What do we produce?
            if 'json' in args['renderer']:  # allows for 'json' or 'simplejson'
                operation['produces'] = ['application/json']
            elif args['renderer'] == 'xml':
                operation['produces'] = ['text/xml']

            # What do we consume?
            if 'accept' in args:
                operation['consumes'] = [args['accept']]


            # The Swagger 'summary' will come from the docsttring
            operation['summary'] =  op_method.__doc__ if op_method is not None and op_method.__doc__ is not None else view

            # A Colander Schema can be used to extract parameters.  If present, it always updates discovered path
            # parameters, yet is still updated with @swagger.operation(parameters) if present
            if 'schema' in args:
                schema = args['schema']
                parameter = schema2parameter(schema, service)
                update_op_param(parameter)

            # Use our @swagger.operation decorator to gather and override
            # previously collected data as needed
            if op_method is not None and '__swagger_attr' in op_method.__dict__:
                # Different listed swagger objects have different unique keys, so map them here
                op_objects = op_method.__dict__['__swagger_attr']
                # Loop through arguments and their values from our decorator
                for deco_arg, deco_val in op_objects.iteritems():
                    # Update operation components
                    if deco_arg in operation:
                        # Our value will either be a dict or a list of dicts
                        if isinstance(deco_val, list):
                            # Input Parameters require unique "names"
                            if deco_arg == 'parameters':
                                # Here's a list of dicts.  Compare the unique key of each dict.
                                #idx = 0
                                for swagger_item in deco_val:
                                    update_op_param(swagger_item)
                            else:
                                #make a unique list
                                operation[deco_arg] = list(set(operation[deco_arg] + deco_val))
                        else:
                            # Assume we have a dictionary.  Is it it a response?  Strip out the default.
                            if deco_arg == 'responses':
                                operation['responses'].pop('default', None)
                            # If not a response, the dict be updated like normal
                            operation[deco_arg].update(deco_val)
                    else:
                        # Add a new item to our operation object
                        operation[deco_arg] = deco_val

            # Do some cleanup
            if len(operation['parameters']) == 0:
                del operation['parameters']
            path[method.lower()] = operation.copy()
        if len(path['parameters']) == 0:
            del path['parameters']
        doc['paths'][service.path] = path
        if tag_name in tags_dict:
            tags_dict[tag_name].update(service_tag)
        else:
            tags_dict[tag_name] = service_tag
    # Extract tags list from our dict
    for k, v in tags_dict.iteritems():
       doc['tags'].append(v)
    return doc


# TODO: Make a validator which works similarly
def validator(request, parameters):
    """ Cornice validator.  Check Swagger parameters against request (.params, .headers, .body) for:
    1) Presence if required==True
    2) Data type
    3) Excess (more params in request than defined)
    """
    err = request.error
    qs = request.params  # querystring multidict
    headers = request.headers
    body = request.body
    path_dict = request.matchdict

    param_keys = [param['name'] for param in parameters]
    
    # See if we have excess params
    for qs_key in qs.keys():
        if qs_key not in param_keys:
            err.add('query', qs_key, "Undefined parameter")

    # See if we have missing required params
    for param in parameters:
        if param['required'] is True and param['name'] not in qs.keys():
            err.add('query', param['name'], "Missing required parameter")

    # Check data types
    for param in parameters:
        if param['name'] in qs.keys():
            qs_val = qs.getall(param['name'])

            err.add('query', param['name'], "Missing required parameter")


