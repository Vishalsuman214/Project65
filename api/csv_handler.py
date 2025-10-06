from werkzeug.security import generate_password_hash, check_password_hash
import csv
import os
import uuid
import datetime

USERS_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.csv')

def read_users():
    users = []
    if not os.path.exists(USERS_CSV):
        return users
    with open(USERS_CSV, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            users.append(row)
    return users

def write_users(users):
    with open(USERS_CSV, mode='w', newline='', encoding='utf-8') as file:
        fieldnames = ['id', 'email', 'password_hash', 'is_email_confirmed', 'verification_token', 'reset_token', 'reset_token_expiry', 'profile_picture', 'bio', 'email_credentials', 'app_password']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for user in users:
            writer.writerow(user)

def add_user(email, password):
    users = read_users()
    if any(user['email'] == email for user in users):
        return None
    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password)
    new_user = {
        'id': user_id,
        'email': email,
        'password_hash': password_hash,
        'is_email_confirmed': 'True',  # Email verification removed, set to True by default
        'verification_token': '',
        'reset_token': '',
        'reset_token_expiry': '',
        'profile_picture': '',
        'bio': '',
        'email_credentials': '',
        'app_password': ''
    }
    users.append(new_user)
    write_users(users)
    return user_id

def get_user_by_email(email):
    users = read_users()
    for user in users:
        if user['email'] == email:
            return user
    return None

def get_user_by_id(user_id):
    users = read_users()
    for user in users:
        if user['id'] == user_id:
            return user
    return None

def update_user_password(user_id, new_password_hash):
    users = read_users()
    updated = False
    for user in users:
        if user['id'] == user_id:
            user['password_hash'] = new_password_hash
            updated = True
            break
    if updated:
        write_users(users)
    return updated

def update_user_profile_picture(user_id, filename):
    users = read_users()
    updated = False
    for user in users:
        if user['id'] == user_id:
            user['profile_picture'] = filename
            updated = True
            break
    if updated:
        write_users(users)
    return updated

def update_user_bio(user_id, bio):
    users = read_users()
    updated = False
    for user in users:
        if user['id'] == user_id:
            user['bio'] = bio
            updated = True
            break
    if updated:
        write_users(users)
    return updated

def update_user_email_credentials(user_id, email, app_password):
    users = read_users()
    updated = False
    for user in users:
        if user['id'] == user_id:
            user['email_credentials'] = email
            user['app_password'] = app_password
            updated = True
            break
    if updated:
        write_users(users)
    return updated

def update_user_reminder_email(user_id, email):
    users = read_users()
    updated = False
    for user in users:
        if user['id'] == user_id:
            user['reminder_email'] = email
            updated = True
            break
    if updated:
        write_users(users)
    return updated

def update_user_reminder_app_password(user_id, app_password):
    users = read_users()
    updated = False
    for user in users:
        if user['id'] == user_id:
            user['reminder_app_password'] = app_password
            updated = True
            break
    if updated:
        write_users(users)
    return updated

def verify_password(password, password_hash):
    return check_password_hash(password_hash, password)

# Stub functions for removed email verification features
def generate_verification_token(email):
    return str(uuid.uuid4())

def set_verification_token(user_id, token):
    pass

def verify_email(token):
    return True

def generate_reset_token(email):
    return str(uuid.uuid4())

def set_reset_token(user_id, token, expiry):
    users = read_users()
    updated = False
    for user in users:
        if user['id'] == user_id:
            user['reset_token'] = token
            user['reset_token_expiry'] = str(expiry)
            updated = True
            break
    if updated:
        write_users(users)
    return updated

def reset_password(token, new_password):
    users = read_users()
    updated = False
    for user in users:
        if user['reset_token'] == token:
            user['password_hash'] = generate_password_hash(new_password)
            user['reset_token'] = ''
            user['reset_token_expiry'] = ''
            updated = True
            break
    if updated:
        write_users(users)
    return updated

# Reminder functions
def get_all_reminders():
    REMINDERS_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'reminders.csv')
    if not os.path.exists(REMINDERS_CSV):
        return []
    with open(REMINDERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def mark_reminder_completed(reminder_id):
    REMINDERS_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'reminders.csv')
    if not os.path.exists(REMINDERS_CSV):
        return False
    reminders = []
    with open(REMINDERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        reminders = list(reader)

    updated = False
    for reminder in reminders:
        if reminder['id'] == str(reminder_id):
            reminder['is_completed'] = 'True'
            updated = True
            break

    if updated:
        with open(REMINDERS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'user_id', 'title', 'description', 'reminder_time', 'recipient_email', 'is_completed'])
            writer.writeheader()
            writer.writerows(reminders)
        return True
    return False

def add_reminder(user_id, title, description, reminder_time, recipient_email):
    REMINDERS_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'reminders.csv')
    reminder_id = str(uuid.uuid4())
    new_reminder = {
        'id': reminder_id,
        'user_id': user_id,
        'title': title,
        'description': description,
        'reminder_time': reminder_time,
        'recipient_email': recipient_email,
        'is_completed': 'False'
    }
    reminders = []
    if os.path.exists(REMINDERS_CSV):
        with open(REMINDERS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            reminders = list(reader)
    reminders.append(new_reminder)
    with open(REMINDERS_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'user_id', 'title', 'description', 'reminder_time', 'recipient_email', 'is_completed']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reminders)
    return reminder_id

def get_reminders_by_user_id(user_id):
    REMINDERS_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'reminders.csv')
    if not os.path.exists(REMINDERS_CSV):
        return []
    with open(REMINDERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [reminder for reminder in reader if reminder['user_id'] == user_id]

def get_reminder_by_id(reminder_id):
    REMINDERS_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'reminders.csv')
    if not os.path.exists(REMINDERS_CSV):
        return None
    with open(REMINDERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for reminder in reader:
            if reminder['id'] == reminder_id:
                return reminder
    return None

def update_reminder(reminder_id, title=None, description=None, reminder_time=None, recipient_email=None, is_completed=None):
    REMINDERS_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'reminders.csv')
    if not os.path.exists(REMINDERS_CSV):
        return False
    reminders = []
    with open(REMINDERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        reminders = list(reader)

    updated = False
    for reminder in reminders:
        if reminder['id'] == reminder_id:
            if title is not None:
                reminder['title'] = title
            if description is not None:
                reminder['description'] = description
            if reminder_time is not None:
                reminder['reminder_time'] = reminder_time
            if recipient_email is not None:
                reminder['recipient_email'] = recipient_email
            if is_completed is not None:
                reminder['is_completed'] = is_completed
            updated = True
            break

    if updated:
        with open(REMINDERS_CSV, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'user_id', 'title', 'description', 'reminder_time', 'recipient_email', 'is_completed']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reminders)
        return True
    return False

def delete_reminder(reminder_id):
    REMINDERS_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'reminders.csv')
    if not os.path.exists(REMINDERS_CSV):
        return False
    reminders = []
    with open(REMINDERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        reminders = list(reader)

    original_length = len(reminders)
    reminders = [reminder for reminder in reminders if reminder['id'] != reminder_id]

    if len(reminders) < original_length:
        with open(REMINDERS_CSV, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'user_id', 'title', 'description', 'reminder_time', 'recipient_email', 'is_completed']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reminders)
        return True
    return False
