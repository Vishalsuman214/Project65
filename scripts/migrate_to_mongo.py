import csv
import os
import sys
from datetime import datetime
from pymongo import MongoClient

# Add project directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.mongo_handler import users_collection, reminders_collection

def migrate_users():
    users_csv = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.csv')
    if not os.path.exists(users_csv):
        print("Users CSV file not found, skipping user migration.")
        return

    with open(users_csv, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Convert string booleans to actual booleans
            row['is_email_confirmed'] = row['is_email_confirmed'].lower() == 'true'
            users_collection.insert_one(row)
    print("Users migrated successfully.")

def migrate_reminders():
    reminders_csv = os.path.join(os.path.dirname(__file__), '..', 'data', 'reminders.csv')
    if not os.path.exists(reminders_csv):
        print("Reminders CSV file not found, skipping reminder migration.")
        return

    with open(reminders_csv, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Convert string booleans to actual booleans
            row['is_completed'] = row['is_completed'].lower() == 'true'
            # Convert reminder_time from string to datetime object
            if 'reminder_time' in row and row['reminder_time']:
                try:
                    row['reminder_time'] = datetime.strptime(row['reminder_time'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print(f"Warning: Invalid reminder_time format for reminder {row.get('id', 'unknown')}: {row['reminder_time']}")
            reminders_collection.insert_one(row)
    print("Reminders migrated successfully.")

if __name__ == "__main__":
    print("Starting migration from CSV to MongoDB...")
    migrate_users()
    migrate_reminders()
    print("Migration completed.")
