import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")

    def send_welcome_email(self, to_email: str, username: str, temp_password: str):
        if not self.smtp_user or not self.smtp_pass:
            print(f"SMTP not configured. Skipping email to {to_email}")
            return

        msg = MIMEMultipart()
        msg['From'] = self.smtp_user
        msg['To'] = to_email
        msg['Subject'] = "Welcome to QueryMind AI - Account Created"

        body = f"""
        <html>
        <body>
            <h2>Welcome to QueryMind AI, {username}!</h2>
            <p>Your account has been created by an administrator.</p>
            <p><strong>Username:</strong> {username}</p>
            <p><strong>Temporary Password:</strong> {temp_password}</p>
            <br>
            <p>Please log in and change your password immediately.</p>
            <p>Best regards,<br>The QueryMind Team</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            print(f"Welcome email sent to {to_email}")
        except Exception as e:
            print(f"Failed to send email to {to_email}: {e}")
