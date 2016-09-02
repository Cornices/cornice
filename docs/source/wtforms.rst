..  _wtforms:

WTForms integration
===================

Using WTForms for JSON validation in Cornice can be achieved through
`cornice.ext.wtforms` extension which specifies **validate_wtforms_schema**
function.

For this function to properly work you have to have WTForms installed and install
`wtforms_json <https://github.com/kvesteri/wtforms-json>` package. You can do 
this through::

    pip install wtforms
    pip install wtforms-json
    
Suppose you want to create a Service that allows you to send JSON data for User
that should be validated through WTForms schema. Our User will also have address
defined, so we can show how to validate nested JSON schemas through WTForms.

Let's start with importing required packages::

    from cornice import Service
    from cornice.ext.wtforms import validate_wtforms_schema
    
    from wtforms import Form, StringField, FormField, IntegerField
    from wtforms.validators import AnyOf, Length, DataRequired, Optional, \
	                               InputRequired

We have to import wtforms_json and initialize it after our WTForms imports::

	import wtforms_json
	wtforms_json.init()
    
Now let's define our WTForms schemas. We'll have two of them: 

* AddressSchema - which will validate our user's address;
* UserSchema - which will validate user data

Here's the code::

	class AddressSchema(Form):
	    country = StringField(validators=[DataRequired()])
	    state = StringField(validators=[Optional()])
	    city = StringField(validators=[DataRequired()])
	    postcode = StringField(validators=[DataRequired()])
	    address = StringField(validators=[DataRequired()])


	class UserSchema(Form):
	    email = StringField(validators=[DataRequired()])
	    password = StringField(validators=[DataRequired(), Length(min=8)])
	    phone = StringField(validators=[Optional()])
	    sex = StringField(validators=[AnyOf(['m', 'f'])]
	    age = IntegerField(validators=[InputRequired()])
	    name = StringField(validators=[DataRequired()])
	    surname = StringField(validators=[DataRequired()])
	    address = FormField(AddressSchema)

This will allow us to pass a request with JSON data like this::

    {
        "email": "foo@bar.com",
        "password": "somesecretpassword",
        "phone": "4350983543",
        "sex": "m",
        "age": 42,
        "name": "John",
        "surname": "Doe",
        "address": {
            "country": "US",
            "state": "Texas",
            "city": "Houston",
            "postcode": "77800",
            "address": "Mirage St. 42"
        }

Let's define User service with POST method::

    USERS = {}
    
    user = Service(name='user', path='/user')
    
    
    @user.post(content-type='application/json',
    	       validators=validate_wtforms_schema(UserSchema))
    def post_user(request):
        """Saves user.
        """
        form = request.form
        user_email = form.data.get('email')
        
        USERS[user_email] = form.data
        
        return True


After successful validation of the request input JSON data, you can access the
WTForms schema through **request.form** and the validated data through
**request.form.data** as you would when using WTForms. For more information on
how to use validated data refer to `WTForms documentation 
<https://wtforms.readthedocs.org/en/latest/>`.

Interpolating with matchdict
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**validate_wtforms_schema** function also has a keyword argument 
*with_matchdict* set as default to *False*. Setting *with_matchdict* to *True* 
allows to update JSON dictionary with values passed through request.matchdict. 
It may be useful when you pass e.g. *id* within your request.matchdict and you 
want to merge keys from it to the JSON dictionary for further processing e.g.
to update your data based upon this key.

Here's a quick example::

    class UserUpdateSchema(UserSchema):
        id = IntegerField(validators=[InputRequired()]
    

    userupdate = Service(name='userupdate', path='/user/{id}')

    
    @userupdate.put(
   	    content-type='application/json',
        validators=validate_wtforms_schema(UserUpdateSchema, with_matchdict=True))
    def update_user(request):
        form = request.form
        user_id = form.data.get('id')
        
        # DO SOMETHING WITH user_id
        ...


That way you can interpolate variable **id** passed through **request.matchdict**
with JSON data sent as PUT method body. **with_matchdict=True** will update
input dictionary passed to the defined schema with key-value pairs from
matchdict.
