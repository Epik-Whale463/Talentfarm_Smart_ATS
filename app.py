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
from talent_search_service import talent_search_bp
from realtime_service import socketio
import os

def create_app():
    """Application factory pattern for creating Flask app"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Create required directories if they don't exist
    os.makedirs('instance', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('resumes', exist_ok=True)
    os.makedirs('static/uploads', exist_ok=True)
    
    # Validate configuration
    config_validation = Config.validate_config()
    if not config_validation['is_valid']:
        app.logger.warning("Configuration issues detected:")
        if config_validation['missing_vars']:
            app.logger.warning(f"Missing required variables: {', '.join(config_validation['missing_vars'])}")
        if config_validation['invalid_vars']:
            app.logger.warning(f"Invalid/default values detected: {', '.join(config_validation['invalid_vars'])}")
        app.logger.warning("Some features may not work properly. Please check your environment variables.")
    
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
    
    # Initialize vector database sync listeners
    try:
        from vector_sync_listeners import init_vector_sync
        init_vector_sync()
        app.logger.info("Vector database sync listeners initialized")
    except Exception as e:
        app.logger.warning(f"Failed to initialize vector sync listeners: {e}")
    
    # Initialize RAG services
    try:
        from rag_service import rag_service
        from rag_talent_search import rag_talent_search_service
        app.logger.info("RAG services initialized")
    except Exception as e:
        app.logger.warning(f"Failed to initialize RAG services: {e}")
    
    # Register blueprints (modular routes)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(resumes_bp, url_prefix='/api/resumes')
    app.register_blueprint(jobs_bp, url_prefix='/api/jobs')
    app.register_blueprint(interviews_bp, url_prefix='/api/interviews')
    app.register_blueprint(talent_search_bp, url_prefix='/api/talent-search')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    
    # Register GitHub analysis blueprint
    from github_analysis_service import github_analysis_bp
    app.register_blueprint(github_analysis_bp, url_prefix='/api')
    
    # Register health check blueprint
    from health import health_bp
    app.register_blueprint(health_bp, url_prefix='/api/health')
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=False, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)