from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
import csv
from flask_login import login_required, current_user
from datetime import datetime
import io
import sys

# Add project directory to path for imports when running as script
sys.path.insert(0, 'py-project')

from api.mongo_handler import add_reminder, get_reminders_by_user_id, get_reminder_by_id, update_reminder

reminders_bp = Blueprint('reminders', __name__)

@reminders_bp.route('/dashboard')
@login_required
def dashboard():
    # Get user's reminders with error handling
    try:
        reminders = get_reminders_by_user_id(str(current_user.id))
    except Exception as e:
        print(f"Error fetching reminders for user {current_user.id}: {e}")
        reminders = []
    return render_template('dashboard.html', reminders=reminders)

@reminders_bp.route('/create_reminder', methods=['GET', 'POST'])
@login_required
def create_reminder():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        reminder_time_str = request.form.get('reminder_time')
        recipient_email = request.form.get('recipient_email', '').strip() or None
        attachment = request.files.get('attachment')

        # Validate required fields
        if not title or not reminder_time_str:
            flash('Title and reminder time are required.')
            return redirect(url_for('reminders.create_reminder'))

        try:
            reminder_time = datetime.strptime(reminder_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format')
            return redirect(url_for('reminders.create_reminder'))

        # Check if reminder time is in the future
        if reminder_time <= datetime.now():
            flash('Reminder time must be in the future.')
            return redirect(url_for('reminders.create_reminder'))

        try:
            # Create new reminder using MongoDB
            add_reminder(str(current_user.id), title, description, reminder_time, recipient_email)
            flash('Reminder created successfully!')
        except Exception as e:
            print(f"Error creating reminder for user {current_user.id}: {e}")
            flash('An error occurred while creating the reminder.')

        return redirect(url_for('reminders.dashboard'))

    return render_template('create_reminder.html')

@reminders_bp.route('/edit_reminder/<reminder_id>', methods=['GET', 'POST'])
@login_required
def edit_reminder(reminder_id):
    reminder = get_reminder_by_id(reminder_id)
    
    # Check if reminder exists and belongs to current user
    if not reminder or reminder['user_id'] != current_user.id:
        flash('You cannot edit this reminder')
        return redirect(url_for('reminders.dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        reminder_time_str = request.form.get('reminder_time')
        recipient_email = request.form.get('recipient_email', '').strip() or None
        attachment = request.files.get('attachment')
        
        try:
            reminder_time = datetime.strptime(reminder_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format')
            return redirect(url_for('reminders.edit_reminder', reminder_id=reminder_id))
        
        # Update reminder using CSV
        update_reminder(reminder_id, title, description, reminder_time, recipient_email, attachment)
        flash('Reminder updated successfully!')
        return redirect(url_for('reminders.dashboard'))
    
    reminder_time = datetime.strptime(reminder['reminder_time'], '%Y-%m-%d %H:%M:%S')
    return render_template('edit_reminder.html', reminder=reminder, reminder_time=reminder_time)

@reminders_bp.route('/delete_reminder/<reminder_id>')
@login_required
def delete_reminder(reminder_id):
    reminder = get_reminder_by_id(reminder_id)

    # Check if reminder exists and belongs to current user
    if not reminder or reminder['user_id'] != current_user.id:
        flash('You cannot delete this reminder')
        return redirect(url_for('reminders.dashboard'))

    # Soft delete reminder
    from api.mongo_handler import soft_delete_reminder
    soft_delete_reminder(reminder_id)
    flash('Reminder moved to recycle bin successfully!')
    return redirect(url_for('reminders.dashboard'))

@reminders_bp.route('/export_reminders')
@login_required
def export_reminders():
    try:
        # Convert current_user.id to string for consistency
        user_id_str = str(current_user.id)
        # Get user's reminders
        reminders = get_reminders_by_user_id(user_id_str)
        
        # Create CSV data in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['id', 'user_id', 'title', 'description', 'reminder_time', 'created_at', 'is_completed', 'recipient_email'])
        
        # Write data with validation and defaults
        for reminder in reminders:
            writer.writerow([
                reminder.get('id', ''),
                reminder.get('user_id', ''),
                reminder.get('title', ''),
                reminder.get('description') or '',
                reminder.get('reminder_time', ''),
                reminder.get('created_at', ''),
                'Yes' if str(reminder.get('is_completed', '')).lower() == 'true' else 'No',
                reminder.get('recipient_email', '') or ''
            ])
        
        # Prepare file for download
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'reminders_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        print(f"Error exporting reminders for user {current_user.id}: {e}")
        flash('An error occurred while exporting reminders.')
        return redirect(url_for('reminders.dashboard'))

@reminders_bp.route('/import_reminders', methods=['GET', 'POST'])
@login_required
def import_reminders():
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file selected')
            return redirect(url_for('reminders.dashboard'))

        file = request.files['csv_file']
        if file.filename == '' or file.filename is None:
            flash('No file selected')
            return redirect(url_for('reminders.dashboard'))

        if not file.filename.lower().endswith('.csv'):
            flash('Please upload a CSV file')
            return redirect(url_for('reminders.dashboard'))

        try:
            # Read CSV file correctly
            content = file.read().decode('utf-8')
            stream = io.StringIO(content, newline=None)
            csv_reader = csv.DictReader(stream)

            imported_count = 0
            updated_count = 0
            skipped_count = 0

            # Get existing reminders for the user to check for duplicates
            user_reminders = get_reminders_by_user_id(str(current_user.id))

            for row in csv_reader:
                # Validate required fields like create_reminder does
                title = row.get('title', '').strip()
                reminder_time_str = row.get('reminder_time', '').strip()

                if not title or not reminder_time_str:
                    print(f"Skipping row - missing required fields: title='{title}', reminder_time='{reminder_time_str}'")
                    skipped_count += 1
                    continue

                try:
                    reminder_time = datetime.strptime(reminder_time_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print(f"Skipping row - invalid date format '{reminder_time_str}'")
                    skipped_count += 1
                    continue

                # Check if reminder time is in the future like create_reminder does
                if reminder_time <= datetime.now():
                    print(f"Skipping row - reminder time '{reminder_time}' is not in the future")
                    skipped_count += 1
                    continue

                # Check if reminder already exists (by title and time)
                existing_reminder = None
                for user_reminder in user_reminders:
                    if (user_reminder['title'] == title and
                        user_reminder['reminder_time'] == reminder_time.strftime('%Y-%m-%d %H:%M:%S')):
                        existing_reminder = user_reminder
                        break

                description = row.get('description', '').strip()
                recipient_email = row.get('recipient_email', '').strip() or None

                if existing_reminder:
                    # Update existing reminder
                    print(f"Updating existing reminder: {title}")
                    update_reminder(
                        existing_reminder['id'],
                        title,
                        description,
                        reminder_time,
                        recipient_email
                    )
                    updated_count += 1
                else:
                    # Create new reminder
                    print(f"Creating new reminder: {title}")
                    add_reminder(
                        str(current_user.id),
                        title,
                        description,
                        reminder_time,
                        recipient_email
                    )
                    imported_count += 1

            flash(f'Imported {imported_count} new reminders, updated {updated_count} existing reminders, skipped {skipped_count} due to errors.')
            return redirect(url_for('reminders.dashboard'))

        except UnicodeDecodeError as e:
            print(f"Unicode decode error: {e}")
            flash('Error reading CSV file. Please ensure it is encoded in UTF-8.')
            return redirect(url_for('reminders.dashboard'))
        except Exception as e:
            print(f"Error importing reminders: {e}")
            flash('An error occurred while importing reminders.')
            return redirect(url_for('reminders.dashboard'))

    return render_template('import_reminders.html')

@reminders_bp.route('/delete_all_reminders', methods=['POST'])
@login_required
def delete_all_reminders():
    try:
        from api.mongo_handler import delete_all_reminders_by_user
        deleted_count = delete_all_reminders_by_user(str(current_user.id))
        flash(f'Successfully moved {deleted_count} reminders to recycle bin.')
    except Exception as e:
        print(f"Error deleting all reminders for user {current_user.id}: {e}")
        flash('An error occurred while deleting reminders.')
    return redirect(url_for('reminders.dashboard'))

@reminders_bp.route('/recycle_bin')
@login_required
def recycle_bin():
    try:
        from api.mongo_handler import get_deleted_reminders_by_user
        deleted_reminders = get_deleted_reminders_by_user(str(current_user.id))
    except Exception as e:
        print(f"Error fetching deleted reminders for user {current_user.id}: {e}")
        deleted_reminders = []
    return render_template('recycle_bin.html', deleted_reminders=deleted_reminders)

@reminders_bp.route('/restore_reminder/<reminder_id>')
@login_required
def restore_reminder(reminder_id):
    reminder = get_reminder_by_id(reminder_id)

    # Check if reminder exists and belongs to current user
    if not reminder or reminder['user_id'] != current_user.id:
        flash('You cannot restore this reminder')
        return redirect(url_for('reminders.recycle_bin'))

    from api.mongo_handler import restore_reminder
    restore_reminder(reminder_id)
    flash('Reminder restored successfully!')
    return redirect(url_for('reminders.recycle_bin'))

@reminders_bp.route('/permanently_delete_reminder/<reminder_id>')
@login_required
def permanently_delete_reminder(reminder_id):
    reminder = get_reminder_by_id(reminder_id)

    # Check if reminder exists and belongs to current user
    if not reminder or reminder['user_id'] != current_user.id:
        flash('You cannot delete this reminder')
        return redirect(url_for('reminders.recycle_bin'))

    from api.mongo_handler import permanently_delete_reminder
    permanently_delete_reminder(reminder_id)
    flash('Reminder permanently deleted!')
    return redirect(url_for('reminders.recycle_bin'))

@reminders_bp.route('/empty_recycle_bin', methods=['POST'])
@login_required
def empty_recycle_bin():
    try:
        from api.mongo_handler import permanently_delete_all_deleted_reminders
        deleted_count = permanently_delete_all_deleted_reminders(str(current_user.id))
        flash(f'Permanently deleted {deleted_count} reminders from recycle bin.')
    except Exception as e:
        print(f"Error emptying recycle bin for user {current_user.id}: {e}")
        flash('An error occurred while emptying recycle bin.')
    return redirect(url_for('reminders.recycle_bin'))
