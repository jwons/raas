import zipfile

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, FormField, FieldList
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Optional, Length, Required
from app.models import User, Dataset
from flask_login import current_user, login_user, login_required, logout_user


class PackagesForm(FlaskForm):
    package_name = StringField('package_name')
    pypI_name = StringField('pypI_name')

class Code_btw_Form(FlaskForm):
    code=StringField()

class Cmd_Form(FlaskForm):
    script_name = StringField('Script Name')
    command = StringField('Command')


class InputForm(FlaskForm):
    zip_file = FileField('Zip File Containing Dataset')
    set_file = FileField('or---A set of Data file and scripts', render_kw={'multiple': True})
    name = StringField('Name of the Dataset')
    fix_code = BooleanField('Attempt to automatically fix code')
    extended_lib = BooleanField('Extended Library handling')

    language = SelectField('What language is included in your upload', validators=[Required()],
                           choices=[('R', 'R'), ('Python', 'Python')])
    # command_line = StringField('Run instruction')
    provenance = StringField('Provenance')
    # code_btw = StringField('Line of code to run between package install and  execute')
    command_line = FieldList(FormField(Cmd_Form), min_entries=1)
    code_btw= FieldList(FormField(Code_btw_Form), min_entries=1)
    sample_output = FileField('Sample output that you want to compare with', render_kw={'multiple': True})
    pkg_asked = FieldList(FormField(PackagesForm), min_entries=1)
    submit = SubmitField('Build Docker Image')
    add_pkg = SubmitField("+ add more")
    add_code = SubmitField("+ add more")
    add_cmd = SubmitField("+ add more")

    def validate_zip_file(self, zip_file):
        # make sure there's either a set of scripts or a .zip file upload
        # if (not self.doi.data) and (self.zip_file.data is None) and (self.set_file.data is None):
        if (not self.zip_file.data) and (not self.set_file.data):
            raise ValidationError('Either the 1)a .zip or 2)a set of files '
                                  'containing the dataset is required.')
        if (not self.set_file.data) and (not zipfile.is_zipfile(self.zip_file.data)):
            raise ValidationError('File is not a valid a zip file')

    def validate_name(self, name):
        if name.data == "":
            raise ValidationError('Name cannot be an empty string')
        if " " in name.data or not name.data.islower():
            raise ValidationError('Name is not allowed to contain uppercase letter or space.\nTry: '
                                  + name.data.replace(" ", "").lower())
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
