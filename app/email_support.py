from flask_mail import Message
from flask import render_template
from threading import Thread
from app import mail, app#, celery

# @celery.task
# def send_async_email(msg_dict):
# 	with app.app_context():
# 		msg = Message()
# 		msg.__dict__.update(msg_dict)
# 		mail.send(msg)

# def send_email(subject, sender, recipients, text_body, html_body):
# 	send_async_email.apply_async(args=[msg_to_dict(subject, 
# 												   sender, 
# 												   recipients, 
# 												   text_body, 
# 												   html_body)])

# def msg_to_dict(subject, sender, recipients, text_body, html_body):
# 	msg = Message(subject, sender=sender, recipients=recipients)
# 	msg.body = text_body
# 	msg.html = html_body
# 	return msg.__dict__

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(app, msg)).start()

def send_password_reset_email(user):
	token = user.get_reset_password_token()
	send_email('[containr] Reset Your Password',
			   sender=app.config['ADMINS'][0],
			   recipients=[user.email],
			   text_body=render_template('email/reset_password.txt',
										 user=user, token=token),
			   html_body=render_template('email/reset_password.html',
										 user=user, token=token))