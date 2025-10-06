from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_mail import Mail
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.executors.asyncio import AsyncIOExecutor

from flask import Flask, jsonify

from api.auth import User, mail
from api.csv_handler import get_user_by_id
from api.email_service import check_and_send_reminders

# Initialize extensions
login_manager = LoginManager()

def create_app():
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))

    # Validate required environment variables
    required_env_vars = ['SECRET_KEY', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER', 'SYSTEM_SENDER_EMAIL', 'SYSTEM_APP_PASSWORD']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        import sys
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}", file=sys.stderr)
        sys.exit(1)

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the error and return JSON response
        import traceback
        traceback.print_exc()
        return jsonify(error=str(e)), 500

    @login_manager.user_loader
    def load_user(user_id):
        user_data = get_user_by_id(user_id)
        if user_data:
            return User(
                id=user_data['id'],
                email=user_data['email'],
                password_hash=user_data['password_hash']
            )
        return None

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

    # Initialize extensions with app
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    mail.init_app(app)

    @app.route('/')
    def home():
        return redirect(url_for('auth.login'))

    @app.route('/cron/reminders')
    def cron_reminders():
        print("🔄 Cron job /cron/reminders triggered")
        check_and_send_reminders(app)
        print("✅ Cron job /cron/reminders completed")
        return 'Reminders checked', 200

    # Register blueprints
    from api.auth import auth_bp
    from api.reminders import reminders_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(reminders_bp)

    # Set up background scheduler for email reminders (only for local development, not Vercel)
    if os.environ.get('VERCEL'):
        print("⚠️ VERCEL environment detected - background scheduler disabled")
    else:
        print("✅ Starting background scheduler for reminders")
        try:
            scheduler = BackgroundScheduler(executors={
                'default': ThreadPoolExecutor(20),
                'processpool': ProcessPoolExecutor(5)
            })

            # Schedule check_and_send_reminders to run every 5 minutes
            scheduler.add_job(
                func=check_and_send_reminders,
                args=[app],
                trigger=IntervalTrigger(minutes=5),
                id='check_reminders',
                name='Check and send due reminders',
                replace_existing=True
            )

            # Start the scheduler
            scheduler.start()
            print("✅ Background scheduler started - will check reminders every 5 minutes")

            # Shut down the scheduler when exiting the app
            import atexit
            atexit.register(lambda: scheduler.shutdown())
        except Exception as e:
            import traceback
            print("❌ Failed to start background scheduler:", e)
            traceback.print_exc()

    return app

# For Vercel deployment
app = create_app()

# For Vercel deployment
app = create_app()
