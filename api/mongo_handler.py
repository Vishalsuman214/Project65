from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
import os
import uuid
import datetime

# MongoDB connection
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['reminder_app']
users_collection = db['users']
reminders_collection = db['reminders']

def read_users():
    return list(users_collection.find())

def write_users(users):
    # This function is not needed in MongoDB, but kept for compatibility
    pass

def add_user(email, password):
    if users_collection.find_one({'email': email}):
        return None
    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password)
    new_user = {
        'id': user_id,
        'email': email,
        'password_hash': password_hash,
        'is_email_confirmed': True,  # Email verification removed, set to True by default
        'verification_token': '',
        'reset_token': '',
        'reset_token_expiry': '',
        'profile_picture': '',
        'bio': '',
        'email_credentials': '',
        'app_password': ''
    }
    users_collection.insert_one(new_user)
    return user_id

def get_user_by_email(email):
    return users_collection.find_one({'email': email})

def get_user_by_id(user_id):
    return users_collection.find_one({'id': user_id})

def update_user_password(user_id, new_password_hash):
    result = users_collection.update_one(
        {'id': user_id},
        {'$set': {'password_hash': new_password_hash}}
    )
    return result.modified_count > 0

def update_user_profile_picture(user_id, filename):
    result = users_collection.update_one(
        {'id': user_id},
        {'$set': {'profile_picture': filename}}
    )
    return result.modified_count > 0

def update_user_bio(user_id, bio):
    result = users_collection.update_one(
        {'id': user_id},
        {'$set': {'bio': bio}}
    )
    return result.modified_count > 0

def update_user_email_credentials(user_id, email, app_password):
    result = users_collection.update_one(
        {'id': user_id},
        {'$set': {'email_credentials': email, 'app_password': app_password}}
    )
    return result.modified_count > 0

def update_user_reminder_email(user_id, email):
    result = users_collection.update_one(
        {'id': user_id},
        {'$set': {'reminder_email': email}}
    )
    return result.modified_count > 0

def update_user_reminder_app_password(user_id, app_password):
    result = users_collection.update_one(
        {'id': user_id},
        {'$set': {'reminder_app_password': app_password}}
    )
    return result.modified_count > 0

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
    result = users_collection.update_one(
        {'id': user_id},
        {'$set': {'reset_token': token, 'reset_token_expiry': str(expiry)}}
    )
    return result.modified_count > 0

def reset_password(token, new_password):
    result = users_collection.update_one(
        {'reset_token': token},
        {'$set': {'password_hash': generate_password_hash(new_password), 'reset_token': '', 'reset_token_expiry': ''}}
    )
    return result.modified_count > 0

# Reminder functions
def get_all_reminders():
    return list(reminders_collection.find())

def mark_reminder_completed(reminder_id, completed=True):
    result = reminders_collection.update_one(
        {'id': str(reminder_id)},
        {'$set': {'is_completed': completed}}
    )
    return result.modified_count > 0

def add_reminder(user_id, title, description, reminder_time, recipient_email):
    reminder_id = str(uuid.uuid4())
    new_reminder = {
        'id': reminder_id,
        'user_id': user_id,
        'title': title,
        'description': description,
        'reminder_time': reminder_time.strftime('%Y-%m-%d %H:%M:%S'),
        'recipient_email': recipient_email,
        'is_completed': False
    }
    reminders_collection.insert_one(new_reminder)
    return reminder_id

def get_reminders_by_user_id(user_id):
    return list(reminders_collection.find({'user_id': user_id}))

def get_reminder_by_id(reminder_id):
    return reminders_collection.find_one({'id': reminder_id})

def update_reminder(reminder_id, title=None, description=None, reminder_time=None, recipient_email=None, is_completed=None):
    update_fields = {}
    if title is not None:
        update_fields['title'] = title
    if description is not None:
        update_fields['description'] = description
    if reminder_time is not None:
        update_fields['reminder_time'] = reminder_time.strftime('%Y-%m-%d %H:%M:%S')
    if recipient_email is not None:
        update_fields['recipient_email'] = recipient_email
    if is_completed is not None:
        update_fields['is_completed'] = is_completed

    if update_fields:
        result = reminders_collection.update_one(
            {'id': reminder_id},
            {'$set': update_fields}
        )
        return result.modified_count > 0
    return False

def delete_reminder(reminder_id):
    result = reminders_collection.delete_one({'id': reminder_id})
    return result.deleted_count > 0

def delete_all_reminders_by_user(user_id):
    # Soft delete all reminders by marking them as deleted
    result = reminders_collection.update_many(
        {'user_id': user_id, 'is_deleted': {'$ne': True}},
        {'$set': {'is_deleted': True, 'deleted_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}
    )
    return result.modified_count

def soft_delete_reminder(reminder_id):
    result = reminders_collection.update_one(
        {'id': reminder_id},
        {'$set': {'is_deleted': True, 'deleted_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}
    )
    return result.modified_count > 0

def restore_reminder(reminder_id):
    result = reminders_collection.update_one(
        {'id': reminder_id},
        {'$unset': {'is_deleted': '', 'deleted_at': ''}}
    )
    return result.modified_count > 0

def get_deleted_reminders_by_user(user_id):
    return list(reminders_collection.find({'user_id': user_id, 'is_deleted': True}))

def permanently_delete_reminder(reminder_id):
    result = reminders_collection.delete_one({'id': reminder_id})
    return result.deleted_count > 0

def permanently_delete_all_deleted_reminders(user_id):
    result = reminders_collection.delete_many({'user_id': user_id, 'is_deleted': True})
    return result.deleted_count
