import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables from .env in current directory
load_dotenv()  # by default it looks for a .env file in cwd

# Read environment variables
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
PASSWORD_EMAIL = os.getenv("PASSWORD_EMAIL")
EMAIL_SERVER = os.getenv("EMAIL_SERVER", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 465))

# Basic checks so we fail early with a helpful message
if not SENDER_EMAIL or not PASSWORD_EMAIL:
    raise RuntimeError("Missing SENDER_EMAIL or SENDER_PASSWORD in environment (.env).")

def send_otp(subject: str, receiver_email: str, otp: int):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver_email
    msg["Bcc"] = SENDER_EMAIL  # use 'Bcc' key with proper case

    msg.set_content(f"Your OTP is: {otp}")

    # Connect to the server and send the email
    try:
        with smtplib.SMTP_SSL(EMAIL_SERVER, EMAIL_PORT) as server:
            server.login(SENDER_EMAIL, PASSWORD_EMAIL)
            server.send_message(msg)  # safer than sendmail + as_string
    except smtplib.SMTPException as e:
        # You may want to log this instead of printing in production
        print(f"Failed to send email: {e}")
        raise

if __name__ == "__main__":
    send_otp(subject="Otp Verification", receiver_email="aloogobi0@gmail.com", otp=6969)
