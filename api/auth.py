from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash
from flask_mail import Mail, Message
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys

# Add project directory to path for imports when running as script
sys.path.insert(0, 'py-project')

from api.csv_handler import add_user, get_user_by_email, get_user_by_id, verify_password, generate_verification_token, set_verification_token, verify_email, generate_reset_token, set_reset_token, reset_password, update_user_email_credentials

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
    try:
        SYSTEM_SENDER_EMAIL = os.environ.get('SYSTEM_SENDER_EMAIL')
        SYSTEM_APP_PASSWORD = os.environ.get('SYSTEM_APP_PASSWORD')

        msg = MIMEMultipart()
        msg["From"] = SYSTEM_SENDER_EMAIL or "noreply@reminderapp.local"
        msg["To"] = email
        msg["Subject"] = "Password Reset for Reminder App"

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

        msg.attach(MIMEText(body, "plain"))

        if SYSTEM_SENDER_EMAIL and SYSTEM_APP_PASSWORD:
            # Use Gmail SMTP
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(SYSTEM_SENDER_EMAIL, SYSTEM_APP_PASSWORD)
            server.sendmail(SYSTEM_SENDER_EMAIL, email, msg.as_string())
            server.quit()
            print(f"✅ Password reset email sent to {email}")
        else:
            # Fallback for development: log email content to console
            print("⚠️ System email credentials not set, logging email content for development")
            print(f"   SYSTEM_SENDER_EMAIL: {'set' if SYSTEM_SENDER_EMAIL else 'not set'}")
            print(f"   SYSTEM_APP_PASSWORD: {'set' if SYSTEM_APP_PASSWORD else 'not set'}")
            print(f"📧 Password reset email for {email}:")
            print(f"Subject: {msg['Subject']}")
            print(f"Body:\n{body}")
            print(f"Reset Link: {reset_link}")
            print("✅ Password reset email logged (copy the link above to reset password)")

        return True

    except Exception as e:
        print(f"❌ Error sending password reset email to {email}: {e}")
        return False

def send_verification_email_to_credentials(email, app_password):
    try:
        msg = MIMEMultipart()
        msg["From"] = email
        msg["To"] = email
        msg["Subject"] = "Email Credentials Verification"

        body = """
        Hello!

        This is a test email from the Reminder App to verify your email credentials are working correctly.

        If you received this email, your settings are configured properly.

        ---
        This is an automated test email from the Reminder App.
        """

        msg.attach(MIMEText(body, "plain"))

        # Use user provided credentials to send the email
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(email, app_password)
        server.sendmail(email, email, msg.as_string())
        server.quit()

        print(f"✅ Verification email sent to {email}")
        return True

    except Exception as e:
        print(f"❌ Error sending verification email to {email}: {e}")
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

            login_user(user)
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

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    from werkzeug.utils import secure_filename
    import os

    user_data = get_user_by_id(current_user.get_id())

    if request.method == 'POST':
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename != '':
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                # Save file path or filename to user profile in DB or CSV
                update_user_profile_picture(current_user.get_id(), filename)
                flash('Profile picture updated successfully.', 'success')

        # Handle bio update
        bio = request.form.get('bio')
        if bio is not None:
            update_user_bio(current_user.get_id(), bio)
            flash('Bio updated successfully.', 'success')

        # Handle password change
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if current_password and new_password and confirm_password:
            if not user_data or not verify_password(current_password, user_data['password_hash']):
                flash('Current password is incorrect.', 'error')
                return render_template('profile.html', user=user_data)

            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return render_template('profile.html', user=user_data)

            if len(new_password) < 6:
                flash('New password must be at least 6 characters.', 'error')
                return render_template('profile.html', user=user_data)

            if update_user_password(current_user.get_id(), generate_password_hash(new_password)):
                flash('Password updated successfully.', 'success')
            else:
                flash('Failed to update password.', 'error')

        # Handle email credentials update
        reminder_email = request.form.get('email_credentials')
        reminder_app_password = request.form.get('app_password')
        if reminder_email and reminder_app_password:
            update_user_email_credentials(current_user.get_id(), reminder_email, reminder_app_password)
            flash('Email credentials updated successfully.', 'success')

    user_data = get_user_by_id(current_user.get_id())  # Refresh user data after updates
    return render_template('profile.html', user=user_data)

@auth_bp.route('/email-credentials', methods=['GET', 'POST'])
@login_required
def email_credentials():
    from api.csv_handler import update_user_email_credentials
    if request.method == 'POST':
        email = request.form.get('email')
        app_password = request.form.get('app_password')
        if email and app_password:
            if update_user_email_credentials(current_user.get_id(), email, app_password):
                flash('Email credentials updated successfully.', 'success')
            else:
                flash('Failed to update email credentials.', 'error')
    return render_template('email_credentials.html')

@auth_bp.route('/send-verification-email', methods=['POST'])
@login_required
def send_verification_email():
    from api.csv_handler import get_user_by_id
    user_data = get_user_by_id(current_user.get_id())
    if user_data and user_data.get('email_credentials') and user_data.get('app_password'):
        app_password = user_data['app_password']
        try:
            send_verification_email_to_credentials(user_data['email_credentials'], app_password)
            flash('Verification email sent to your email credentials.', 'success')
        except Exception as e:
            flash('Failed to send verification email.', 'error')
    else:
        flash('Please set your email credentials first.', 'error')
    return redirect(url_for('auth.email_credentials'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
