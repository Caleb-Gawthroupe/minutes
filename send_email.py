"""
Simple Python Email Sender
Uses Gmail SMTP to send emails.

Setup:
  1. Enable 2-Factor Authentication on your Google account
  2. Generate an App Password: Google Account > Security > App Passwords
  3. Use your Gmail address and the App Password below (not your regular password)
"""
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

CIVIC_EMAIL = os.getenv("CIVIC_EMAIL")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")


def send_email(
    sender_email: str,
    sender_password: str,
    recipient_email: str,
    subject: str,
    body: str,
    html_body: str = None,
) -> bool:
    """
    Send an email via Gmail SMTP.

    Args:
        sender_email:    Your Gmail address (e.g. you@gmail.com)
        sender_password: Your Gmail App Password (16-char, no spaces)
        recipient_email: Recipient's email address
        subject:         Email subject line
        body:            Plain-text body
        html_body:       Optional HTML body (displayed if supported by client)

    Returns:
        True on success, False on failure.
    """
    # Build the message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email

    # Attach plain text first, then HTML (client prefers the last part)
    msg.attach(MIMEText(body, "plain"))
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"✅ Email sent successfully to {recipient_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed. Check your email and App Password.")
    except smtplib.SMTPRecipientsRefused:
        print(f"❌ Recipient address rejected: {recipient_email}")
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return False


# ── Example usage ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    SENDER    = CIVIC_EMAIL          # Your Gmail address
    PASSWORD  = EMAIL_APP_PASSWORD   # 16-char App Password (with spaces is fine)
    RECIPIENT = CIVIC_EMAIL    # Who receives the email

    SUBJECT = "Hello from Python!"

    PLAIN_BODY = """\
Hi there,

This email was sent using Python's smtplib — no third-party packages required!

Cheers
"""

    HTML_BODY = """\
<html>
  <body>
    <p>Hi there,</p>
    <p>This email was sent using <b>Python's smtplib</b> — no third-party packages required!</p>
    <p>Cheers</p>
  </body>
</html>
"""

    send_email(SENDER, PASSWORD, RECIPIENT, SUBJECT, PLAIN_BODY, HTML_BODY)