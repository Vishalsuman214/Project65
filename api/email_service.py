import os
import sys
from datetime import datetime
import concurrent.futures
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add project directory to path for imports when running as script
sys.path.insert(0, 'py-project')

from api.mongo_handler import get_all_reminders, mark_reminder_completed, get_user_by_id

# Email configuration (should be moved to environment variables in production)
# No default credentials, user must set their own
DEFAULT_SENDER_EMAIL = None
DEFAULT_APP_PASSWORD = None

# System email credentials for auth notifications (password reset, confirmations)
# Load from environment variables inside functions for dynamic updates

def send_reminder_email(receiver_email, reminder_title, reminder_description, reminder_time, user_id=None):
    """Send a reminder email to the specified recipient using SMTP"""
    try:
        # Get user-specific credentials
        if user_id:
            user = get_user_by_id(user_id)
            sender_email = user.get('email_credentials') if user else None
            sender_password = user.get('app_password') if user else None
        else:
            sender_email = None
            sender_password = None

        # Check if credentials are set
        if not sender_email or not sender_password:
            print(f"❌ Email credentials not set for user {user_id}. Please set email credentials in settings.")
            return False

        # SMTP server settings (default to Gmail)
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))

        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = f"Reminder: {reminder_title}"

        body = f"""
        Hello!

        This is a reminder for: {reminder_title}

        Description: {reminder_description or 'No description provided'}

        Scheduled Time: {reminder_time.strftime('%Y-%m-%d %H:%M')}

        ---
        This is an automated reminder from the Reminder App.
        """
        msg.attach(MIMEText(body, 'plain'))

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)

        # Attempt to quit the server, but don't fail if it doesn't work
        try:
            server.quit()
        except Exception as quit_error:
            print(f"⚠️ Warning: Failed to quit SMTP server gracefully: {quit_error}")

        print(f"✅ Email sent successfully to {receiver_email}")
        return True

    except Exception as e:
        print(f"❌ Error sending email to {receiver_email}: {e}")
        return False

def send_test_email(sender_email, sender_password, test_recipient_email):
    """Send a test email to verify credentials using SMTP"""
    try:
        # SMTP server settings (default to Gmail)
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))

        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = test_recipient_email
        msg['Subject'] = "Test Email from Reminder App"

        body = """
        Hello!

        This is a test email from the Reminder App to verify your email credentials are working correctly.

        If you received this email, your settings are configured properly.

        ---
        This is an automated test email from the Reminder App.
        """
        msg.attach(MIMEText(body, 'plain'))

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, test_recipient_email, text)

        # Attempt to quit the server, but don't fail if it doesn't work
        try:
            server.quit()
        except Exception as quit_error:
            print(f"⚠️ Warning: Failed to quit SMTP server gracefully: {quit_error}")

        print(f"✅ Test email sent successfully to {test_recipient_email}")
        return True

    except Exception as e:
        print(f"❌ Error sending test email to {test_recipient_email}: {e}")
        return False

def check_and_send_reminders(app):
    """Check for reminders that are due and send emails"""
    with app.app_context():
        current_time = datetime.now()
        print(f"🔄 Checking reminders at {current_time}")

        # Get all reminders
        all_reminders = get_all_reminders()
        print(f"📋 Found {len(all_reminders)} total reminders")

        # Collect reminders to send
        reminders_to_send = []
        for reminder in all_reminders:
            print(f"🔍 Checking reminder '{reminder['title']}' - Completed: {reminder['is_completed']}")

            # Skip completed reminders
            if reminder['is_completed'] == True or str(reminder['is_completed']).lower() == 'true':
                continue

            # Parse reminder time
            try:
                if isinstance(reminder['reminder_time'], str):
                    reminder_time = datetime.strptime(reminder['reminder_time'], '%Y-%m-%d %H:%M:%S')
                elif isinstance(reminder['reminder_time'], datetime):
                    reminder_time = reminder['reminder_time']
                else:
                    print(f"   ❌ Invalid reminder time type: {type(reminder['reminder_time'])}")
                    continue
                print(f"   Reminder time: {reminder_time}, Current time: {current_time}")
            except ValueError:
                print(f"   ❌ Invalid reminder time format: {reminder['reminder_time']}")
                continue

            # Check if reminder is due
            if reminder_time <= current_time:
                print(f"   ✅ Reminder is due")
                user = get_user_by_id(str(reminder['user_id']))
                if user:
                    # Check if user has set email credentials
                    if not user.get('email_credentials') or not user.get('app_password'):
                        print(f"⚠️  Skipping reminder '{reminder['title']}' - user {reminder['user_id']} has not set email credentials")
                        continue

                    # Mark reminder as completed immediately to prevent duplicate sends
                    if not mark_reminder_completed(reminder['id']):
                        print(f"   ❌ Failed to mark reminder '{reminder['title']}' as completed, skipping")
                        continue

                    # Use custom recipient email if provided, otherwise use user's email
                    recipient_email = reminder.get('recipient_email', '') or user['email']
                    print(f"   📧 Will send to {recipient_email}")

                    reminders_to_send.append((reminder, recipient_email, reminder_time, user))
                else:
                    print(f"   ❌ User {reminder['user_id']} not found")
                    # Add error handling to avoid crash
                    continue
            else:
                print(f"   ⏰ Reminder not yet due")

        # Send emails in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(send_reminder_and_mark, reminder, recipient_email, reminder_time, user)
                for reminder, recipient_email, reminder_time, user in reminders_to_send
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"❌ Error in sending reminder: {e}")

def send_reminder_and_mark(reminder, recipient_email, reminder_time, user):
    """Send reminder email and mark as completed"""
    success = send_reminder_email(
        recipient_email,
        reminder['title'],
        reminder['description'],
        reminder_time,
        reminder['user_id']
    )

    if success:
        # Reminder is already marked as completed before sending, so just log
        print(f"✅ Reminder '{reminder['title']}' sent to {recipient_email} and marked as completed")
    else:
        # If sending failed, mark reminder as not completed again to allow retry
        mark_reminder_completed(reminder['id'], False)
        print(f"❌ Failed to send reminder '{reminder['title']}' to {recipient_email}, marked as not completed for retry")

def send_password_reset_email(user_email, reset_token, user_name):
    """Send password reset email with link using SMTP"""
    try:
        SYSTEM_SENDER_EMAIL = os.environ.get('SYSTEM_SENDER_EMAIL') or "noreply@reminderapp.local"
        SYSTEM_SENDER_PASSWORD = os.environ.get('SYSTEM_SENDER_PASSWORD')

        # SMTP server settings (default to Gmail)
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))

        base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
        reset_link = f"{base_url.rstrip('/')}/reset-password?token={reset_token}"
        body = f"""
        Hello {user_name},

        You requested a password reset for your Reminder App account.

        Click the link below to reset your password:
        {reset_link}

        This link will expire in 1 hour.

        If you didn't request this, please ignore this email.

        ---
        This is an automated email from the Reminder App.
        """

        if SYSTEM_SENDER_PASSWORD:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = SYSTEM_SENDER_EMAIL
            msg['To'] = user_email
            msg['Subject'] = "Password Reset for Reminder App"
            msg.attach(MIMEText(body, 'plain'))

            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(SYSTEM_SENDER_EMAIL, SYSTEM_SENDER_PASSWORD)
            text = msg.as_string()
            server.sendmail(SYSTEM_SENDER_EMAIL, user_email, text)

            # Attempt to quit the server, but don't fail if it doesn't work
            try:
                server.quit()
            except Exception as quit_error:
                print(f"⚠️ Warning: Failed to quit SMTP server gracefully: {quit_error}")

            print(f"✅ Password reset email sent to {user_email}")
        else:
            # Fallback for development: log email content to console
            print("⚠️ SYSTEM_SENDER_PASSWORD not set, logging email content for development")
            print(f"📧 Password reset email for {user_email}:")
            print(f"Subject: Password Reset for Reminder App")
            print(f"Body:\n{body}")
            print(f"Reset Link: {reset_link}")
            print("✅ Password reset email logged (copy the link above to reset password)")

        return True

    except Exception as e:
        print(f"❌ Error sending password reset email to {user_email}: {e}")
        return False

def send_email_confirmation_otp(user_email, otp, user_name):
    """Send email confirmation OTP using SMTP"""
    try:
        SYSTEM_SENDER_EMAIL = os.environ.get('SYSTEM_SENDER_EMAIL') or "noreply@reminderapp.local"
        SYSTEM_SENDER_PASSWORD = os.environ.get('SYSTEM_SENDER_PASSWORD')

        # SMTP server settings (default to Gmail)
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))

        body = f"""
        Hello {user_name},

        Your OTP for email confirmation is: {otp}

        This code expires in 5 minutes.

        ---
        This is an automated email from the Reminder App.
        """

        if SYSTEM_SENDER_PASSWORD:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = SYSTEM_SENDER_EMAIL
            msg['To'] = user_email
            msg['Subject'] = "Email Confirmation Code for Reminder App"
            msg.attach(MIMEText(body, 'plain'))

            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(SYSTEM_SENDER_EMAIL, SYSTEM_SENDER_PASSWORD)
            text = msg.as_string()
            server.sendmail(SYSTEM_SENDER_EMAIL, user_email, text)

            # Attempt to quit the server, but don't fail if it doesn't work
            try:
                server.quit()
            except Exception as quit_error:
                print(f"⚠️ Warning: Failed to quit SMTP server gracefully: {quit_error}")

            print(f"✅ OTP email sent to {user_email}")
        else:
            # Fallback for development: log email content to console
            print("⚠️ SYSTEM_SENDER_PASSWORD not set, logging email content for development")
            print(f"📧 OTP email for {user_email}:")
            print(f"Subject: Email Confirmation Code for Reminder App")
            print(f"Body:\n{body}")
            print("✅ OTP email logged (use the OTP above for confirmation)")

        return True

    except Exception as e:
        print(f"❌ Error sending OTP email to {user_email}: {e}")
        return False
