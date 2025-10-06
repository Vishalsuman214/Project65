import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from api.csv_handler import add_user, generate_verification_token, set_verification_token

# Add a test user
email = 'test@example.com'
password = 'password123'
token = generate_verification_token(email)
user_id = add_user(email, password, token)
set_verification_token(email, token)

print(f"Test user added: {email}, ID: {user_id}, Token: {token}")
print(f"Verification URL: http://localhost:5000/verify?token={token}")
