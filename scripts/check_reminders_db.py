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

if __name__ == "__main__":
    print_reminders()
