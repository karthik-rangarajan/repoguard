from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import datetime
import smtplib

class EmailNotifierException(Exception):
    def __init__(self, error):
        self.error = error

    def __str__(self):
        return repr(self.error)

class EmailNotifier:
    def __init__(self, email_from, email_to, subject, text, connection_string='localhost', login_to_smtp=False,
                 smtp_username = None, smtp_password = None, use_tls = None):
        self.email_from = email_from
        self.email_to = email_to
        self.connection_string = connection_string
        self.mime_message = MIMEMultipart()
        self.prepare_message_headers(subject)
        self.create_mime_message(text)
        self.login_to_smtp = login_to_smtp
        if self.login_to_smtp:
            self.username = smtp_username
            self.password = smtp_password
            self.use_tls = use_tls

    @staticmethod
    def create_notification(from_addr, to_addr, text, connection_string='localhost', login_to_smtp=False,
                            smtp_username = None, smtp_password = None, use_tls = None):
        subject = "[repoguard] possibly vulnerable changes - %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        return EmailNotifier(from_addr, to_addr, subject, text, connection_string, login_to_smtp,
                             smtp_username, smtp_password, use_tls)

    def prepare_message_headers(self, subject):
        self.subject = subject
        self.mime_message["Subject"] = subject
        self.mime_message["From"] = self.email_from
        self.mime_message["To"] = self.email_to

    def create_mime_message(self, text):
        self.text = text
        self.mime_message.attach(MIMEText(text.encode("utf-8"), "plain"))

    def send_if_fine(self):
        if self.email_from and self.email_to and self.mime_message:
            self.smtp_send()
        else:
            raise EmailNotifierException("Mails should have FROM, TO headers and a message as well!")

    def smtp_send(self):
        try:
            smtp = smtplib.SMTP(self.connection_string)
            if self.login_to_smtp:
                if self.use_tls:
                    smtp.starttls()
                smtp.login(self.username, self.password)
            smtp.sendmail(self.email_from, self.email_to, self.mime_message.as_string())
            smtp.quit()
        except smtplib.SMTPException, e:
            raise EmailNotifierException(e)


