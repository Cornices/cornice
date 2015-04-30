# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def validate_wtforms_schema(form_schema, with_matchdict=False):
    """Validates JSON data through WTForms schema.

    For this function to properly work you have to install wtforms_json
    package and add this code::

        import wtforms_json
        wtforms_json.init()

    to the module where you define WTForms schemas, just after WTForms
    imports.

    Here's an example usage::

        @view(
            ...
            validators=( validate_wtforms_schema(MyFormSchema), ),
            ...
        )

    This function also has a keyword argument *with_matchdict* set
    as default to False. Setting *with_matchdict* to True allows
    to update JSON dictionary with values passed through
    request.matchdict. It may be useful when you pass e.g. *id*
    within your request.matchdict and you want to merge keys from
    it to the JSON dictionary for further processing e.g.
    to update SQLAlchemy model.
    """
    def wrapper(request):
        try:
            data = request.json
        except Exception as e:
            request.errors.add('body', 'exception', str(e))
            return

        if with_matchdict:
            data.update(request.matchdict)

        try:
            form_obj = form_schema.from_json(data)
        except Exception as e:
            request.errors.add('form', 'exception', str(e))
            return
        if not form_obj.validate():
            request.errors.add('form', 'validation', form_obj.errors)
            return
        request.form = form_obj
    return wrapper
