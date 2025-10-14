import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.auth_login'
login_manager.login_message_category = 'info'


def create_app(config_class=Config):
    """Application factory for Flask"""
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Import routes and register blueprint
    from app import routes
    app.register_blueprint(routes.bp)   # ✅ 'bp' is the blueprint in routes.py

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
