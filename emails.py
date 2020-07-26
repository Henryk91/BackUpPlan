from flask_mail import Mail, Message

mail = None

def configure_mail(app):
    # EMAIL SETTINGS
    global mail
    app.config.update(
        MAIL_SERVER = 'smtp.gmail.com',
        MAIL_PORT = 587,
        MAIL_USE_SSL = True,
        MAIL_USERNAME = 'heinrichk91@gmail.com',
        MAIL_PASSWORD = 'fbbrmcbbkvcgtrun',
        DEFAULT_MAIL_SENDER = 'heinrichk91@gmail.com',
        SECRET_KEY = 'abcdefd_thats_a_charming_secret_key',
    )
    mail=Mail(app)

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender = sender, recipients = recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)