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
