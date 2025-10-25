<<<<<<< HEAD
# TODO: Ensure Email Credentials are Visible and Not Removable
## Tasks
- [x] Modify `/email-credentials` route in `api/auth.py` to fetch and pass current email credentials to the template on GET requests.
- [x] Update `templates/email_credentials.html` to pre-fill form inputs with current values and change app_password input to type "text" for visibility.

# TODO: Fix Email Sending Issues

## Tasks
- [x] Analyze SMTP email sending functions in `api/auth.py` for timeout and authentication issues.
- [x] Increase SMTP connection timeout and add better error handling.
- [x] Implement SendGrid as primary email service with SMTP fallback.
- [x] Test email sending after fixes - app restarted successfully.
=======
# TODO: Fix Deployment Issues

## Tasks
- [x] Change SMTP from SSL (465) to TLS (587) in all email functions
- [x] Switch all email sending to use SendGrid API instead of SMTP
- [x] Update send_reminder_email in email_service.py
- [x] Update send_test_email in email_service.py
- [x] Update send_password_reset_email in email_service.py
- [x] Update send_email_confirmation_otp in email_service.py
- [x] Update send_reset_email in auth.py
- [x] Update send_verification_email_to_credentials in auth.py
- [x] Fix profile picture upload to use /tmp on deployment
- [x] Test fixes on deployment
>>>>>>> 5b91f90d25f41871fc3f227bf00417e8457cd3d6
