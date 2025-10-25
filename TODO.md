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
