from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, FloatField, IntegerField, TextAreaField, MultipleFileField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CreateStaffForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    full_name = StringField('Full name', validators=[Optional()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    is_admin = BooleanField('Admin')  # allow creating another admin if needed
    submit = SubmitField('Create Staff')

class CustomerOrderForm(FlaskForm):
    customer_name = StringField('Customer name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired(), Length(min=6, max=30)])
    address = StringField('Address', validators=[Optional()])
    product_name = StringField('Product name', validators=[DataRequired()])
    product_details = TextAreaField('Product details', validators=[Optional()])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    quantity = IntegerField('Quantity', default=1, validators=[DataRequired(), NumberRange(min=1)])
    photos = MultipleFileField('Product photos (you can select multiple)', validators=[Optional()])
    delivery_datetime = StringField('Delivery datetime (YYYY-MM-DD HH:MM)', validators=[Optional()])
    return_datetime = StringField('Return datetime (YYYY-MM-DD HH:MM)', validators=[Optional()])
    amount_advance = FloatField('Advance amount', default=0.0, validators=[Optional()])
    submit = SubmitField('Save Order')
