from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash
from flask_mail import Mail, Message
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SendGridMail, Email, To, Content

# Add project directory to path for imports when running as script
sys.path.insert(0, 'py-project')

from api.mongo_handler import add_user, get_user_by_email, get_user_by_id, verify_password, generate_verification_token, set_verification_token, verify_email, generate_reset_token, set_reset_token, reset_password, update_user_email_credentials, update_user_profile_picture, update_user_bio, update_user_password

# System email credentials (loaded inside functions for dynamic updates)

auth_bp = Blueprint('auth', __name__)

mail = Mail()

def send_verification_email(email, token):
    domain = os.environ.get('VERCEL_URL', os.environ.get('DOMAIN', 'http://localhost:5000'))
    if domain.startswith('http://localhost'):
        pass  # keep as is
    else:
        domain = f"https://{domain}"  # Vercel uses https
    verify_url = f"{domain}/verify?token={token}"
    msg = Message('Verify Your Email', sender=current_app.config['MAIL_DEFAULT_SENDER'], recipients=[email])
    msg.body = f'Click the link to verify your email: {verify_url}'
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"❌ Failed to send verification email to {email}: {e}")
        return False

def send_reset_email(email, token, user_name='User'):
    """Send password reset email using SendGrid"""
    try:
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        SYSTEM_SENDER_EMAIL = os.environ.get('SYSTEM_SENDER_EMAIL') or "noreply@reminderapp.local"

        base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
        reset_link = f"{base_url.rstrip('/')}/reset-password?token={token}"
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

        if sendgrid_api_key:
            # Use SendGrid for sending email
            sg = SendGridAPIClient(sendgrid_api_key)
            from_email = Email(SYSTEM_SENDER_EMAIL)
            to_email = To(email)
            subject = "Password Reset for Reminder App"
            content = Content("text/plain", body)
            mail = SendGridMail(from_email, to_email, subject, content)

            response = sg.send(mail)
            if response.status_code == 202:
                print(f"✅ Password reset email sent to {email} via SendGrid")
                return True
            else:
                print(f"❌ SendGrid error: {response.status_code} - {response.body}")
                return False
        else:
            # Fallback to SMTP if SendGrid not configured
            SYSTEM_SENDER_PASSWORD = os.environ.get('SYSTEM_SENDER_PASSWORD')
            smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.environ.get('SMTP_PORT', '587'))

            if SYSTEM_SENDER_PASSWORD:
                # Create message
                msg = MIMEMultipart()
                msg['From'] = SYSTEM_SENDER_EMAIL
                msg['To'] = email
                msg['Subject'] = "Password Reset for Reminder App"
                msg.attach(MIMEText(body, 'plain'))

                # Send email with increased timeout
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                server.starttls()
                server.login(SYSTEM_SENDER_EMAIL, SYSTEM_SENDER_PASSWORD)
                text = msg.as_string()
                server.sendmail(SYSTEM_SENDER_EMAIL, email, text)
                server.quit()

                print(f"✅ Password reset email sent to {email} via SMTP")
            else:
                # Fallback for development: log email content to console
                print("⚠️ Neither SendGrid API key nor SMTP password set, logging email content for development")
                print(f"📧 Password reset email for {email}:")
                print(f"Subject: Password Reset for Reminder App")
                print(f"Body:\n{body}")
                print(f"Reset Link: {reset_link}")
                print("✅ Password reset email logged (copy the link above to reset password)")

        return True

    except Exception as e:
        print(f"❌ Error sending password reset email to {email}: {e}")
        return False

def send_verification_email_to_credentials(email, app_password):
    """Send verification email using SendGrid or fallback to SMTP"""
    try:
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')

        print(f"🔄 Attempting to send verification email to {email}")

        body = f"""
        Hello!

        This is a test email from the Reminder App to verify your email credentials are working correctly.

        Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        If you received this email, your settings are configured properly and reminders will be sent successfully.

        ---
        This is an automated test email from the Reminder App.
        """

        if sendgrid_api_key:
            # Use SendGrid for sending email
            print("📧 Using SendGrid for test email")
            sg = SendGridAPIClient(sendgrid_api_key)
            from_email = Email(email)  # Use user's email as sender for verification
            to_email = To(email)
            subject = "Email Credentials Verification - Reminder App"
            content = Content("text/plain", body)
            mail = SendGridMail(from_email, to_email, subject, content)

            response = sg.send(mail)
            if response.status_code == 202:
                print(f"✅ Verification email sent successfully to {email} via SendGrid")
                return True
            else:
                print(f"❌ SendGrid error: {response.status_code} - {response.body}")
                return False
        else:
            # Fallback to SMTP
            smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.environ.get('SMTP_PORT', '587'))

            print(f"📧 SMTP Server: {smtp_server}:{smtp_port}")

            # Create message
            msg = MIMEMultipart()
            msg['From'] = email
            msg['To'] = email
            msg['Subject'] = "Email Credentials Verification - Reminder App"
            msg.attach(MIMEText(body, 'plain'))

            # Send email with increased timeout
            print("🔗 Connecting to SMTP server...")
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)  # Reduced timeout for faster feedback
            server.starttls()
            print("🔐 Logging in...")
            server.login(email, app_password)
            print("📤 Sending email...")
            text = msg.as_string()
            server.sendmail(email, email, text)

            # Attempt to quit the server, but don't fail if it doesn't work
            try:
                server.quit()
                print("🔌 SMTP connection closed successfully")
            except Exception as quit_error:
                print(f"⚠️ Warning: Failed to quit SMTP server gracefully: {quit_error}")

            print(f"✅ Verification email sent successfully to {email} via SMTP")
            return True

    except smtplib.SMTPConnectError as e:
        print(f"❌ SMTP Connection Error: {e}")
        return False
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP Authentication Error: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error sending verification email to {email}: {e}")
        return False

class User:
    def __init__(self, id, email, password_hash):
        self.id = id
        self.email = email
        self.password_hash = password_hash
    
    def get_id(self):
        return str(self.id)
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user already exists
        user_data = get_user_by_email(email)
        if user_data:
            flash('Email address already exists', 'error')
            return redirect(url_for('auth.signup'))

        # Create new user
        user_id = add_user(email, password)

        flash('Account created successfully! You can now log in.', 'success')

        return redirect(url_for('auth.login'))

    return render_template('signup.html')



@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user_data = get_user_by_email(email)
        if user_data:
            token = generate_reset_token(email)
            from datetime import datetime, timedelta
            expiry = datetime.now() + timedelta(hours=1)
            set_reset_token(user_data['id'], token, expiry)
            try:
                send_reset_email(email, token, user_data.get('name', 'User'))
                flash('If the email exists, a reset link has been sent.', 'info')
            except Exception as e:
                flash('Password reset unsuccessful - email not sent.', 'error')
        else:
            flash('If the email exists, a reset link has been sent.', 'info')  # Don't reveal if email exists
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user_data = get_user_by_email(email)

        if user_data and verify_password(password, user_data['password_hash']):
            user = User(
                id=user_data['id'],
                email=user_data['email'],
                password_hash=user_data['password_hash']
            )

            login_user(user, remember=True)  # Enable remember me for persistent sessions
            return redirect(url_for('reminders.dashboard'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html')



@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_route():
    token = request.args.get('token') or request.form.get('token')
    if not token:
        flash('Invalid reset link', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('reset_password.html', token=token)

        if reset_password(token, password):
            flash('Password reset successfully. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid or expired reset token.', 'error')
            return render_template('reset_password.html', token=token)

    return render_template('reset_password.html', token=token)



@auth_bp.route('/email-credentials', methods=['GET', 'POST'])
@login_required
def email_credentials():
    from api.mongo_handler import update_user_email_credentials, get_user_by_id
    user_data = get_user_by_id(current_user.get_id())
    current_email = user_data.get('email_credentials', '') if user_data else ''
    current_app_password = user_data.get('app_password', '') if user_data else ''
    if request.method == 'POST':
        email = request.form.get('email')
        app_password = request.form.get('app_password')
        if email and app_password:
            if update_user_email_credentials(current_user.get_id(), email, app_password):
                flash('Email credentials updated successfully.', 'success')
                current_email = email
                current_app_password = app_password
            else:
                flash('Failed to update email credentials.', 'error')
    return render_template('email_credentials.html', current_email=current_email, current_app_password=current_app_password)

@auth_bp.route('/send-verification-email', methods=['POST'])
@login_required
def send_verification_email():
    from api.mongo_handler import get_user_by_id
    user_data = get_user_by_id(current_user.get_id())
    if user_data and user_data.get('email_credentials') and user_data.get('app_password'):
        app_password = user_data['app_password']
        try:
            result = send_verification_email_to_credentials(user_data['email_credentials'], app_password)
            if result:
                flash('Verification email sent successfully! Check your email.', 'success')
            else:
                flash('Failed to send verification email. Please check your credentials.', 'error')
        except Exception as e:
            print(f"Error sending verification email: {e}")
            flash('Failed to send verification email. Please check your credentials.', 'error')
    else:
        flash('Please set your email credentials first.', 'error')
    return redirect(url_for('auth.email_credentials'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
