<<<<<<< HEAD
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from api.mongo_handler import get_all_reminders

def print_reminders():
    reminders = get_all_reminders()
    if not reminders:
        print("No reminders found in database.")
        return
    for reminder in reminders:
        print(f"ID: {reminder['id']}, Title: {reminder['title']}, Completed: {reminder['is_completed']}, Time: {reminder['reminder_time']}")
=======
import csv
import os
from api.csv_handler import REMINDERS_CSV

def print_reminders():
    if not os.path.exists(REMINDERS_CSV):
        print("No reminders CSV file found.")
        return
    with open(REMINDERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            print(f"ID: {row['id']}, Title: {row['title']}, Completed: {row['is_completed']}, Time: {row['reminder_time']}")
>>>>>>> 5b91f90d25f41871fc3f227bf00417e8457cd3d6

if __name__ == "__main__":
    print_reminders()
