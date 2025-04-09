import os
from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
socketio = SocketIO()
login_manager = LoginManager()

def create_app(test_config=None):
    """Application factory pattern for Flask app"""
    app = Flask(__name__, instance_relative_config=True)
    
    # Configure the app
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        LINKEDIN_CLIENT_ID=os.environ.get('LINKEDIN_CLIENT_ID'),
        LINKEDIN_CLIENT_SECRET=os.environ.get('LINKEDIN_CLIENT_SECRET'),
        LINKEDIN_REDIRECT_URI=os.environ.get('LINKEDIN_REDIRECT_URI'),
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Initialize extensions with app
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Register blueprints
    from app.routes import main_bp, auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    
    # Setup login manager
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)
    
    login_manager.login_view = 'auth.login'
    
    return app
