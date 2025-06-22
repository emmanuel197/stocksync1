import smtplib
import ssl
import os
from dotenv import load_dotenv
from email.mime.text import MIMEText # Import MIMEText

load_dotenv()

# Load details from environment variables
smtp_server = os.environ.get('EMAIL_HOST')
port = int(os.environ.get('EMAIL_PORT', 587))
sender_email = os.environ.get('EMAIL_HOST_USER') # Should be apikey
password = os.environ.get('EMAIL_HOST_PASSWORD') # Your SendGrid API Key
receiver_email = os.environ.get('DEFAULT_FROM_EMAIL') # Use your verified sender email for testing
# Use the actual sender email from .env for the From header
actual_sender_email = os.environ.get('DEFAULT_FROM_EMAIL')

print(f"Using SMTP server: {smtp_server}, Port: {port}, Sender (login): {sender_email}")
print(f"Attempting to send email from: {actual_sender_email} to: {receiver_email}")


# Create a MIMEText message object
message = MIMEText("This is a test email sent from a Python script using SendGrid.")
message['Subject'] = "SendGrid SMTP Connection Test"
message['From'] = actual_sender_email # Set the From header
message['To'] = receiver_email       # Set the To header


# Create a secure SSL context
context = ssl.create_default_context()

server = None

try:
    print("Attempting to connect to SMTP server...")
    server = smtplib.SMTP(smtp_server, port)
    print("Connection established.")

    print("Sending EHLO...")
    server.ehlo()
    print("EHLO sent.")

    print("Starting TLS...")
    server.starttls(context=context)
    print("TLS started.")

    print("Sending EHLO again after TLS...")
    server.ehlo()
    print("EHLO sent again.")

    print(f"Attempting to log in as {sender_email}...")
    server.login(sender_email, password)
    print("Login successful.")

    print(f"Attempting to send email from {actual_sender_email} to {receiver_email}...")
    # Pass the message as a string using as_string()
    server.sendmail(actual_sender_email, receiver_email, message.as_string())
    print("SMTP connection successful and test email sent!")

except Exception as e:
    print(f"Error connecting to SMTP server or sending email: {e}")
finally:
    if server:
        try:
            print("Attempting to quit SMTP server connection...")
            server.quit()
            print("SMTP connection closed.")
        except Exception as quit_e:
            print(f"Error closing SMTP connection: {quit_e}")