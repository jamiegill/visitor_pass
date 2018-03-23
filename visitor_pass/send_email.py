import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from . import app

def send_email(html_email_contents, email_subject, email_dest):

	# enable/disable email functionality globally

	global_email_enabled = "enable"

	if global_email_enabled == "disable":
		pass
	elif global_email_enabled == "enable":

		from_email = app.config["SMTP_ADDRESS"]
		to_email = email_dest

		msg = MIMEMultipart('alternative')
		msg['Subject'] = email_subject
		msg['From'] = from_email
		msg['To'] = to_email
		msg['Reply-To'] = from_email

		with open ('./visitor_pass/templates/email_base.html', 'r') as email_base:
			html_base = email_base.read()


		html = html_base + html_email_contents

		mail = smtplib.SMTP(app.config["SMTP_SERVER"])

		html_email = MIMEText(html, 'html')
		msg.attach(html_email)

		open_image = open('./visitor_pass/static/graphics/VPassPortalTrans.png', 'rb')
		msgImage = MIMEImage(open_image.read())
		open_image.close()
		# image1 is referenced in the actual HTML code (ie. html_base)
		msgImage.add_header('Content-ID', '<image1>')

		msg.attach(msgImage)

		mail.ehlo()
		mail.starttls()
		mail.login(app.config["SMTP_ADDRESS"],app.config["SMTP_PASSWORD"])
		mail.sendmail(from_email,to_email,msg.as_string())
		mail.close()

def email_use_pass(building_name, user_name, pass_unit, pass_num, pass_license_plate, pass_plate_expire, email_dest):

	email_subject = "VPass Portal - Visitor Pass Currently In Use"

	with open ('./visitor_pass/templates/email_use_pass.html', 'r') as email_use_pass:
		html_email_contents = email_use_pass.read().format(building_name=building_name,
															user_name=user_name,
															pass_unit=pass_unit,
															pass_num=pass_num,
															pass_license_plate=pass_license_plate,
															pass_plate_expire=pass_plate_expire)
		
	send_email(html_email_contents, email_subject, email_dest)

def email_end_pass(building_name, user_name, pass_unit, pass_num, pass_license_plate, pass_plate_expire, email_dest):

	email_subject = "VPass Portal - Visitor Pass Expired"

	with open ('./visitor_pass/templates/email_end_pass.html', 'r') as email_end_pass:
		html_email_contents = email_end_pass.read().format(building_name=building_name,
															user_name=user_name,
															pass_unit=pass_unit,
															pass_num=pass_num,
															pass_license_plate=pass_license_plate,
															pass_plate_expire=pass_plate_expire)
		
	send_email(html_email_contents, email_subject, email_dest)

def email_address_add(building_name, user_name, user_email, user_password):

	email_subject = "Welcome to VPass Portal, {}".format(user_name)

	with open ('./visitor_pass/templates/email_address_add.html', 'r') as email_address_add:
		html_email_contents = email_address_add.read().format(building_name=building_name,
																user_email=user_email,
																user_name=user_name,
																user_password=user_password,
																)
	send_email(html_email_contents, email_subject, user_email)