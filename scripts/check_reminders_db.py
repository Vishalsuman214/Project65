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

if __name__ == "__main__":
    print_reminders()
