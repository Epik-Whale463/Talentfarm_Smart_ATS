# Main Flask Application Entry Point
from flask import Flask, session
from flask_cors import CORS
from config import Config
from models import db
from auth import auth_bp, init_oauth
from resumes import resumes_bp
from jobs import jobs_bp
from interviews import interviews_bp
from dashboard import dashboard_bp
from realtime_service import socketio
import os

def create_app():
    """Application factory pattern for creating Flask app"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Set Flask session secret key for OAuth
    app.secret_key = app.config['SECRET_KEY']
    
    # Configure session to be secure and last longer
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('SESSION_COOKIE_SECURE', False)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Helps with CSRF protection
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour in seconds
    
    # Enable CORS for frontend integration
    CORS(app)
    
    # Initialize database
    db.init_app(app)
    
    # Initialize SocketIO
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Initialize OAuth
    init_oauth(app)
    
    # Register blueprints (modular routes)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(resumes_bp, url_prefix='/api/resumes')
    app.register_blueprint(jobs_bp, url_prefix='/api/jobs')
    app.register_blueprint(interviews_bp, url_prefix='/api/interviews')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
