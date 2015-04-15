# Overview
To create a full swagger spec, this module will maximize extracting documentation data from functional code, while allowing users to directly specify parts of the Swagger Spec.  This documentation serves as a "how-to".  Readers are encouraged to look at the source for more detailed documentation if needed.

This module creates a [Swagger 2.0 compliant spec](https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md).

Throughout this documentation, `code-styled text` indicates a sort of "proper noun" matching the official names used in related documentation (Swagger Spec, Cornice, Pyramid, Colander and SQLAlchemy primarily).  

**Outline**

1. Docstrings
2. Swagger Module
  1. Decorators
    1. @path
    2. @operation
  2. Converters
    1. Colander for input parameters
    2. SQLAlchemy for output responses


# Description Docstrings

- `cornice.@resource()`-decorated classes in your view file should have docstrings (triple-quoted strings immediately after your class declaration)
    * This docstring becomes the description for the respective endpoint group.
    * Each endpoint group is a collection of Swagger Paths which start with the same URL base (the text between the first two `/` characters in your URL after the true URL base).   
- `cornice.@view()`-decorated methods with your decorated Cornice Resource classes should have docstrings to document the individual HTTP method descriptions

*Note*
The Swagger UI groups together endpoints which share the same `tag`.  The swagger module auto-tags all endpoints based on their path beginning.  Technically, a Swagger Spec stores a `basePath` in the [root document object](https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#fixed-fields).  However, as a well-formed REST URI begins with a RESTful object with which to be interacted, this object (between the first slashes) will be used to tag similar paths into a group.   

*Warning*
﻿If you implement multiple `@resource`-decorated classes beginning with the same first URL segment in the `path` argument, it may become ambiguous which docstring will be displayed in Swagger UI. Only put a docstring on one such class to remove ambiguity.


#Swagger Module
`swagger.py` contains two decorators which allow a hook to add or overwrite any Swagger Spec objects:

1. `@path()`
2. `@operation()`

Next, this swagger module contains several converters to ease converting between commonly used Python objects within the Pyramid universe:

1. Multidict - a Pyramid datastructure
2. Matchdict - a WebOb datastructure.  WebOb is used by the Pyramid core.
3. Colander Schema - A validation Schema often passed to Cornice's @view() decorator
4. SQLAlchemy Models - Often desirable to return rows of a DB as a response object

Lastly, `swagger.py` uses `generate_swagger_spec(services, title, version, **kwargs)` to make the actual Swagger Spec JSON.  The arguments are:

1. `services` - a list of Pyramid Services.  Note that Cornice Resources are really Services under the hood.
2. `title` and `version` are both required Swagger Spec details for the [Info Object](https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#info-object).  
3. `kwargs` can be made of anything else which would go into the base [Swagger Object](https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#swagger-object).  

*Note*
If you want to add to the `Info Object`, simply pass in as an `info` argument with the additional details.  The `Info Object` populated by the `title` and `version` args provided earlier will simply be updated. 

An example of a Pyramid Service which itself scans other Cornice Resources and Services to generate a `swagger.json` Spec:

```python
from pyramid.view import view_config
from cornice import service
from swagger import generate_swagger_spec
# This OrderedDict import is for Extra Credit below
from collections import OrderedDict

@view_config(route_name='swagger_json', renderer='json')
def swagger_json(request):
    info = {'title': 'Joe's API', 'version': '0.1', 'contact': {
            'name': 'Joe Smith',
            'email': 'joe.cool@swagger.com'}
            }
    
    # Pretend our API is served on our host with a prefix, such as an API version number or a username
    base_path = '/jcool'
    security_definition = {
        "authId": {
            "type": "apiKey",
            "name": "ID-Token",
            "in": "header"
        }
    }

    # Get our list of services
    services = service.get_services()
    swagger_spec = generate_swagger_spec(services, info['title'], info['version'], info=info, basePath=base_path)

    # Extra Credit: We want to put paths in a special order with /cool endpoints first, and OrderedPaths act just like a dict as far ase the JSON parser is concerned.
    paths_dict = swagger_spec['paths']
    ordered_paths = OrderedDict()
    first_items = ['/tokens', '/tokens/{authId}']
    for item in first_items:
        ordered_paths[item] = paths_dict[item]
    # Now add all the other paths
    ordered_paths.update(sorted(paths_dict.items(), key=lambda t: t[0]))
    # Replace our paths with the ordered ones
    swagger_spec['paths'] = ordered_paths
    return swagger_spec
```

## Decorators
When creating the Swagger Spec JSON, `swagger.py` will overwrite _any_ auto-generated parts with data provided directly to a decorator.  Any `kwargs` parameters do a decorator functions the same as to the `generate_swagger_document`: they get unpacked by the builtin Cornice JSON renderer (ultimately, `json.dumps()`).  

There are two, and they correspond to a Swagger spec objects: a Swagger `Path Objects` contains `Operation Objects`:
- `@path` [adds path-level details](https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#paths-object)
- `@operation` [adds operation-level details](https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object)

### @path
Reaslistically, the only interesting object for `@path` would be `Parameter Objects` used by all child `Operation Objects`.   Skip to the `@operations` for an example of how it all works.

### @operation
One can define their `Operation Object` completely inline within the decorator, though it may be useful to define one's `Parameters Object` and `Response Object` dicts in separate files to allow for possible use:
```python

import parameters  # Suppose you put your parameter lists in parameters.py
    @swagger.operation(
        parameters=parameters.myCoolParamsList
        responses={
            '200': {"description": "Records of Historical Cools",
                "schema": {
                    "title": "Historical Cools",
                    "properties": {
                        "date_epoch": {"type": "integer"},
                        "temperature": {"type": "integer"},
                        "scale": {"type": "string"}
                    }
                }
            }
        }
    )
    def get(self):
        ...
```    

As you can see, `parameters` is set to a Python list `Parameter Objects`, which matches what the Swagger Spec's `Operation Object` requires.  Similarly, `reponses` is set to a nested dict of `Response Objects`.


## Converters
Ideally, we'd maximaize how much documentation comes from functional code.  As we're already using Cornice, we can leverage its operators internally to `generate_swagger_spec()`.   This only gets us so far, and currently only leverages the `@resource` decorator as it identifies services and provides some path info from which to gleen `path` parameters and a description.   For example, this code...
```python
@resource(collection_path='/tokens', path='/tokens/{authId}', description='quick token description')
class Token(object):
    """Authenticate by POSTing here"""
    def __init__(self, request):
        self.request = request

    # This method implements the POST /tokens http call.
    @swagger.operation(parameters=[{'name': 'X-OpenAM-Username', 'in': 'header', 'description': 'LDAP Username',
                                    'type': 'string'},
                                   {'name': 'X-OpenAM-Password', 'in': 'header', 'description': 'LDAP Password',
                                    'type': 'string', 'format': 'password'}],
                       responses=token_post)
    def collection_post(self):
        """Get authKey here and use as X-Identity-Token for future calls"""
        ...
    @swagger.operation(responses=token_delete)
    def delete(self):
        """Log out of system by deleting a token from your previous authId"""
        ...
```
... will lead to this Swagger `Path Object` snippet:
```
	"paths": {
		"/tokens": {
			"post": {
				"tags": ["tokens"],
				"summary": "Get authKey here and use as X-Identity-Token for future calls",
				"responses":  # token_post dict would go here,
				"parameters": [{
					"in": "header",
					"type": "string",
					"description": "LDAP Username",
					"name": "X-OpenAM-Username"
				},
				{
					"in": "header",
					"type": "string",
					"description": "LDAP Password",
					"name": "X-OpenAM-Password",
					"format": "password"
				}],
				"produces": ["application/json"]
			}
		},
	    "/tokens/{authId}": {
			"parameters": [{
				"required": true,
				"type": "string",
				"name": "authId",
				"in": "path"
			}],
			"delete": {
				"tags": ["tokens"],
				"summary": "Log out of system by deleting a token from your previous authId",
				"responses":  # contents of token_delete - hopefully a nested dict!
				...
				
				
```
### Colander
Since Cornice recommends Colander for validation, there are some handy converters to convert Colander `Schemas Nodes` to Swagger `Parameter Objects`.   

First off, `multidict2matchdict(request, parameters)` can convert the `multidict` object found in `request.params`, and uses an existing Swagger parameters list to return a `matchdict`.  A `matchdict` is simply a dict which returns `None` if the passed key is not present.  This can be handy if you're not using a true validator like Colander, but want to leverage whatever `Parameter Objects` you may have hand-defined to allow your main code to check for the existence of, say, a query string parameter by simply seing if the resulting `matchdict` value is not `None`.  See `swagger.py` code comments for more.

If you have defined Cornice `Schema` objects (comprised of `Schema Nodes`), you can pass it to `schema2parameters` which then converts the `Schema` to a list of `Swagger Parameters`.    Since  `Schema Nodes` take in a Colander type as an argument (`Tuple`, `Boolean`, etc) the Swagger `Parameter Object` "type" can be derived.  This function is used by `generate_swagger_spec` to scan for Colander Schmas being decorated onto an `Operation` with the Cornice `@view(schema=MyCoolSchema` decorator, and the create `Parameter Objects`

If you've grown to love using `matchdicts` (above), then `schema2matchdict()` can save you some time too.  However, by using Colander Schemas, you get the built-in benefit of using `self.request.validated` in your main code, and that provides a cleaned up set of parameters.  Which it doesn't act like a `matchdict`, it _does_ guarantee that any "required" parameters (a Colander schema _without_ `missing=drop`) are present, so no need to check for them!


### SQLAlchemy
It's common to use a database in a REST API, and it's not unlikely your reponses will be some kind of JSON dump of a database table.  If your tables are such that you'd like to dump all the columns for a queried set of rows, then all of your `Column` definitions within your SQLAlchemy `models` can be parsed to learn about what the response will look like.  

`col2swag_type()` converts a primitive type used by SQLAlchemy Columns, to Swagger types.  It's not really a converter one would use directly very often.  But `sqa2swag_model()` is helpful to convert a SQLAlchemy model into a Swagger Response Model.  Note that the `models` argument can be a list.  This is used if your query joins several tables.  If your code returns a subset of columns, you'll need to manually document your `Response Object`.



The best practice SQLAlchemy Models and Colander Schemas will be documented in child pages below, but an overview will be provided here along with 
