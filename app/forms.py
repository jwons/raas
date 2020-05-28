from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Optional
from app.models import User, Dataset
from flask_login import current_user, login_user, login_required, logout_user


class ContainrForm(FlaskForm):
	doi = StringField('Harvard Dataverse DOI', validators=[Optional()])
	zip_file = FileField('Zip File Containing Dataset (if no DOI entered)')
	json_file = FileField("JSON file containing special package installation instructions (Optional)")
	name = StringField('Name of the Dataset', validators=[DataRequired()])
	fix_code = BooleanField('Attempt to automatically fix code')
	# clean_code = BooleanField('Attempt to automatically clean code')
	submit = SubmitField('Build Docker Image')
	def validate_zip_file(self, zip_file):
	    # make sure there's either a DOI or a .zip file upload
	    if (not self.doi.data) and (self.zip_file.data is None):
	        raise ValidationError('Either the dataset DOI or a .zip containing the dataset is required.')

	def validate_name(self, name):
		dataset = Dataset.query.filter_by(user_id=current_user.id, name=name.data).first()
		if dataset is not None:
			raise ValidationError('You already have a dataset with that name. Please choose a different name.')

class LoginForm(FlaskForm):
	username = StringField('Username', validators=[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])
	remember_me = BooleanField('Remember Me')
	submit = SubmitField('Sign In')

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Request Password Reset')

class RegistrationForm(FlaskForm):
	username = StringField('Username', validators=[DataRequired()])
	email = StringField('Email', validators=[DataRequired(), Email()])
	password = PasswordField('Password', validators=[DataRequired()])
	password2 = PasswordField(
		'Confirm Password', validators=[DataRequired(), EqualTo('password')])
	submit = SubmitField('Register')

	def validate_username(self, username):
		user = User.query.filter_by(username=username.data).first()
		if user is not None:
			raise ValidationError('That username is taken. Please use a different username.')

	def validate_email(self, email):
		user = User.query.filter_by(email=email.data).first()
		if user is not None:
			raise ValidationError('An account was found with that email address. Please use a different email address.')