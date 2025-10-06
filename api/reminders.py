from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
import csv
from flask_login import login_required, current_user
from datetime import datetime
import io
import sys

# Add project directory to path for imports when running as script
sys.path.insert(0, 'py-project')

from api.csv_handler import add_reminder, get_reminders_by_user_id, get_reminder_by_id, update_reminder

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
        
        try:
            reminder_time = datetime.strptime(reminder_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format')
            return redirect(url_for('reminders.create_reminder'))
        
        try:
            # Create new reminder using CSV
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
    
    # Delete reminder using CSV
    from api.csv_handler import delete_reminder as delete_reminder_csv
    delete_reminder_csv(reminder_id)
    flash('Reminder deleted successfully!')
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
        if file.filename == '':
            flash('No file selected')
            return redirect(url_for('reminders.dashboard'))
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file')
            return redirect(url_for('reminders.dashboard'))
        
        try:
            # Read CSV file
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            
            imported_count = 0
            skipped_count = 0
            
            for row in csv_reader:
                # Validate required fields
                if not row.get('title') or not row.get('reminder_time'):
                    skipped_count += 1
                    continue
                
                # Parse reminder time
                try:
                    reminder_time = datetime.strptime(row['reminder_time'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    skipped_count += 1
                    continue
                
                # Check if reminder already exists (by title and time)
                existing_reminder = None
                user_reminders = get_reminders_by_user_id(current_user.id)
                for user_reminder in user_reminders:
                    if (user_reminder['title'] == row['title'] and 
                        user_reminder['reminder_time'] == reminder_time.strftime('%Y-%m-%d %H:%M:%S')):
                        existing_reminder = user_reminder
                        break
                
                if existing_reminder:
                    # Update existing reminder
                    update_reminder(
                        existing_reminder['id'],
                        row['title'],
                        row.get('description', ''),
                        reminder_time,
                        row.get('recipient_email', '') or None
                    )
                else:
                    # Create new reminder
                    add_reminder(
                        current_user.id,
                        row['title'],
                        row.get('description', ''),
                        reminder_time,
                        row.get('recipient_email', '') or None
                    )
                    imported_count += 1
            
            flash(f'Imported {imported_count} reminders, skipped {skipped_count} due to missing fields.')
            return redirect(url_for('reminders.dashboard'))
        
        except Exception as e:
            flash('An error occurred while importing reminders.')
            return redirect(url_for('reminders.dashboard'))
    
    return render_template('import_reminders.html')
