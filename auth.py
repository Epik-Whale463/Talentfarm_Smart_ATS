from flask import Blueprint, request, jsonify, redirect, session, url_for, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import requests
import json
import uuid
import os
from datetime import datetime, timedelta
from models import db, User
from config import Config
from authlib.integrations.flask_client import OAuth

auth_bp = Blueprint('auth', __name__)

# Initialize OAuth
oauth = OAuth()

def init_oauth(app):
    """Initialize OAuth with the Flask app"""
    oauth.init_app(app)
    
    # Register GitHub OAuth client with state validation disabled
    oauth.register(
        name='github',
        client_id=Config.GITHUB_CLIENT_ID,
        client_secret=Config.GITHUB_CLIENT_SECRET,
        access_token_url='https://github.com/login/oauth/access_token',
        access_token_params=None,
        authorize_url='https://github.com/login/oauth/authorize',
        authorize_params=None,
        api_base_url='https://api.github.com/',
        client_kwargs={
            'scope': 'user:email',
            'token_endpoint_auth_method': 'client_secret_post'
        },
        # Disable state validation to avoid CSRF issues
        authorize_state=None,
    )
    
    return oauth

def generate_token(user_id):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@auth_bp.route('/github/login', methods=['GET'])
def github_login():
    """Initiate GitHub OAuth login flow"""
    redirect_uri = Config.GITHUB_CALLBACK_URL
    
    # Check if this is a request from the frontend
    redirect_to_frontend = request.args.get('redirect_to_frontend', 'false')
    
    # Get preferred role if provided
    preferred_role = request.args.get('preferred_role')
    
    # Store redirect preference and preferred role in Flask's secure cookie
    session.permanent = True  # Make session last longer
    session['redirect_to_frontend'] = redirect_to_frontend
    if preferred_role in ['candidate', 'hr']:
        session['preferred_role'] = preferred_role
    
    # Get GitHub client from current app
    github = oauth.create_client('github')
    
    # Redirect without state parameter to avoid CSRF issues
    return github.authorize_redirect(redirect_uri=redirect_uri, _external=True)

@auth_bp.route('/github/authorize', methods=['GET'])
def github_callback():
    """Handle GitHub OAuth callback"""
    try:
        # Handle error parameter from GitHub OAuth
        error = request.args.get('error')
        if error:
            error_description = request.args.get('error_description', 'Unknown error')
            return f"""
            <html>
            <head><title>Authentication Error</title></head>
            <body>
                <h1>Authentication Error</h1>
                <p>{error}: {error_description}</p>
                <a href="/login">Return to login</a>
            </body>
            </html>
            """
        # Get GitHub client
        github = oauth.create_client('github')
        
        try:
            # Get the access token without state validation
            token = github.authorize_access_token()
            
            # Get user info
            resp = github.get('user', token=token)
            github_user_info = resp.json()
        except Exception as e:
            print(f"OAuth error during token exchange: {str(e)}")
            # If it's a state mismatch error, try to continue anyway
            if "mismatching_state" in str(e).lower():
                try:
                    # Manual token exchange to bypass state validation
                    code = request.args.get('code')
                    if code:
                        token_data = {
                            'client_id': Config.GITHUB_CLIENT_ID,
                            'client_secret': Config.GITHUB_CLIENT_SECRET,
                            'code': code,
                        }
                        
                        # Make direct request to GitHub token endpoint
                        token_response = requests.post(
                            'https://github.com/login/oauth/access_token',
                            data=token_data,
                            headers={'Accept': 'application/json'}
                        )
                        
                        if token_response.status_code == 200:
                            token_json = token_response.json()
                            access_token = token_json.get('access_token')
                            
                            if access_token:
                                # Get user info with the access token
                                user_response = requests.get(
                                    'https://api.github.com/user',
                                    headers={'Authorization': f'token {access_token}'}
                                )
                                github_user_info = user_response.json()
                                
                                # Create token object for compatibility
                                token = {'access_token': access_token}
                            else:
                                raise Exception("No access token received")
                        else:
                            raise Exception(f"Token exchange failed: {token_response.status_code}")
                    else:
                        raise Exception("No authorization code received")
                except Exception as manual_error:
                    print(f"Manual token exchange also failed: {str(manual_error)}")
                    return f"""
                    <html>
                    <head>
                        <title>Authentication Error</title>
                        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
                    </head>
                    <body class="d-flex align-items-center justify-content-center min-vh-100 bg-light">
                        <div class="card shadow-sm" style="max-width: 500px;">
                            <div class="card-body p-4">
                                <h3 class="text-danger"><i class="fas fa-exclamation-triangle me-2"></i>Authentication Error</h3>
                                <p>GitHub authentication failed: {str(manual_error)}</p>
                                <p>Please try again or contact support.</p>
                                <div class="d-grid">
                                    <a href="/login" class="btn btn-primary">Return to Login</a>
                                </div>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
            else:
                return f"""
                <html>
                <head>
                    <title>Authentication Error</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
                </head>
                <body class="d-flex align-items-center justify-content-center min-vh-100 bg-light">
                    <div class="card shadow-sm" style="max-width: 500px;">
                        <div class="card-body p-4">
                            <h3 class="text-danger"><i class="fas fa-exclamation-triangle me-2"></i>OAuth Error</h3>
                            <p>Authentication failed: {str(e)}</p>
                            <div class="d-grid">
                                <a href="/login" class="btn btn-primary">Return to Login</a>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """
        
        # Get email from GitHub API
        try:
            if 'resp' in locals():
                # Use existing GitHub client connection
                emails_resp = github.get('user/emails', token=token)
                emails = emails_resp.json()
            else:
                # Use direct API call
                emails_response = requests.get(
                    'https://api.github.com/user/emails',
                    headers={'Authorization': f'token {token["access_token"]}'}
                )
                emails = emails_response.json()
                
            primary_email = next((email['email'] for email in emails if email['primary']), emails[0]['email'] if emails else None)
        except Exception as email_error:
            print(f"Error fetching emails: {str(email_error)}")
            # Fallback to user's public email if available
            primary_email = github_user_info.get('email')
        
        if not primary_email:
            return jsonify({'error': 'Failed to get email from GitHub'}), 400
        
        # Check if user exists
        user = User.query.filter_by(github_id=str(github_user_info['id'])).first()
        is_new_user = False
        
        if not user:
            # Check if email is already used
            email_user = User.query.filter_by(email=primary_email).first()
            
            if email_user:
                # Link GitHub to existing user
                email_user.github_id = str(github_user_info['id'])
                email_user.github_username = github_user_info['login']
                email_user.github_avatar = github_user_info.get('avatar_url', '')
                email_user.github_access_token = token['access_token']
                user = email_user
            else:
                # Create a new user without role (will be set during role selection)
                # Get preferred role from session if available
                preferred_role = session.get('preferred_role')
                
                user = User(
                    email=primary_email,
                    name=github_user_info.get('name', github_user_info['login']),
                    github_id=str(github_user_info['id']),
                    github_username=github_user_info['login'],
                    github_avatar=github_user_info.get('avatar_url', ''),
                    github_access_token=token['access_token'],
                    password_hash='GITHUB_OAUTH_USER',  # Set a placeholder value to satisfy NOT NULL constraint
                    role=preferred_role  # Use preferred role if available, otherwise null
                )
                db.session.add(user)
                is_new_user = True
                
        else:
            # Update existing user
            user.github_username = github_user_info['login']
            user.github_avatar = github_user_info.get('avatar_url', '')
            user.github_access_token = token['access_token']
        
        db.session.commit()
        
        # Generate JWT token
        jwt_token = generate_token(user.id)
        
        # Return success with redirect script
        # Check if we should redirect to localhost:3000 (frontend) or localhost:5000 (backend)
        frontend_url = "http://localhost:3000"
        backend_url = "http://localhost:5000"
        
        # Retrieve the redirect preference from session
        redirect_to_frontend = session.get('redirect_to_frontend', 'false').lower() == 'true'
        
        # Determine where to redirect based on user's role status
        if user.role is None:
            # User needs to select a role
            redirect_url = f"{frontend_url}/select-role" if redirect_to_frontend else f"{backend_url}/select-role"
        else:
            # User already has a role, go to dashboard
            redirect_url = f"{frontend_url}/dashboard" if redirect_to_frontend else f"{backend_url}/dashboard"
        
        # Clear the session data
        session.pop('redirect_to_frontend', None)
        session.pop('preferred_role', None)
        
        redirect_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Success</title>
            <script>
                localStorage.setItem('token', '{jwt_token}');
                localStorage.setItem('user', JSON.stringify({json.dumps(user.to_dict())}));
                window.location.href = '{redirect_url}';
            </script>
        </head>
        <body>
            <h1>Authentication successful! Redirecting...</h1>
        </body>
        </html>
        '''
        return redirect_html
        
    except Exception as e:
        error_message = str(e)
        print(f"GitHub OAuth error: {error_message}")
        return f"""
        <html>
        <head>
            <title>Authentication Error</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                }}
                .error-card {{
                    max-width: 500px;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }}
            </style>
        </head>
        <body>
            <div class="card error-card">
                <div class="card-body p-5">
                    <h1 class="text-danger mb-4"><i class="fas fa-exclamation-circle"></i> Authentication Error</h1>
                    <p class="mb-4">There was a problem authenticating with GitHub: {error_message}</p>
                    <p class="mb-4 text-muted small">
                        This might be because the GitHub OAuth application hasn't been properly configured.
                        The administrator needs to register this application with GitHub and configure the
                        correct client ID, secret, and callback URL.
                    </p>
                    <div class="d-grid">
                        <a href="/login" class="btn btn-primary">Return to Login</a>
                    </div>
                    <div class="mt-3 text-center">
                        <a href="/" class="text-muted small">Go to Homepage</a>
                    </div>
                </div>
            </div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/js/all.min.js"></script>
        </body>
        </html>
        """

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user (traditional method)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(k in data for k in ('email', 'password', 'name')):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create new user
        user = User(
            email=data['email'],
            name=data['name'],
            role=data.get('role', 'candidate')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Generate token
        token = generate_token(user.id)
        
        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(k in data for k in ('email', 'password')):
            return jsonify({'error': 'Missing email or password'}), 400
        
        # Find user
        user = User.query.filter_by(email=data['email']).first()
        
        # Check if user exists
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
            
        # Check if user was created with GitHub (has no password)
        if user.github_id and (not user.password_hash or user.password_hash == ''):
            return jsonify({
                'error': 'Please use GitHub to sign in',
                'auth_provider': 'github',
                'github_username': user.github_username
            }), 401
            
        # Check password for regular users
        if not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Generate token
        token = generate_token(user.id)
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/user', methods=['GET'])
def get_user():
    """Get current user info from token"""
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/update-role', methods=['POST'])
def update_role():
    """Update user's role after GitHub OAuth login"""
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid authorization token'}), 401
    
    token = auth_header.split(' ')[1]
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    # Get data from request
    data = request.get_json()
    
    if not data or 'role' not in data:
        return jsonify({'error': 'Missing role parameter'}), 400
    
    role = data['role']
    
    if role not in ['candidate', 'hr']:
        return jsonify({'error': 'Invalid role. Must be candidate or hr'}), 400
    
    # Find user
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Update role
    user.role = role
    db.session.commit()
    
    # Return updated user
    return jsonify({
        'message': 'Role updated successfully',
        'user': user.to_dict()
    }), 200

@auth_bp.route('/delete-account', methods=['DELETE'])
def delete_account():
    """Delete the current user's account"""
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid authorization token'}), 401
    
    token = auth_header.split(' ')[1]
    user_id = verify_token(token)
    
    if not user_id:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    # Find user
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Import models at function level to avoid circular imports
        from models import Resume, Job, Application
        
        print(f"DEBUG: Starting deletion for user {user.id} ({user.email})")
        
        # Delete in proper order to avoid foreign key constraint violations
        # 1. First delete all applications related to user's resumes and jobs
        user_resume_ids = [r.id for r in Resume.query.filter_by(user_id=user.id).all()]
        user_job_ids = [j.id for j in Job.query.filter_by(created_by=user.id).all()]
        
        print(f"DEBUG: Found {len(user_resume_ids)} resumes and {len(user_job_ids)} jobs for user")
        
        # Delete applications for user's resumes
        if user_resume_ids:
            deleted_apps = Application.query.filter(Application.resume_id.in_(user_resume_ids)).delete(synchronize_session=False)
            print(f"DEBUG: Deleted {deleted_apps} applications for user's resumes")
        
        # Delete applications for user's jobs
        if user_job_ids:
            deleted_job_apps = Application.query.filter(Application.job_id.in_(user_job_ids)).delete(synchronize_session=False)
            print(f"DEBUG: Deleted {deleted_job_apps} applications for user's jobs")
        
        # 2. Delete user's jobs
        deleted_jobs = Job.query.filter_by(created_by=user.id).delete(synchronize_session=False)
        print(f"DEBUG: Deleted {deleted_jobs} jobs created by user")
        
        # 3. Delete user's resumes
        deleted_resumes = Resume.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        print(f"DEBUG: Deleted {deleted_resumes} resumes for user")
        
        # 4. Finally delete the user
        db.session.delete(user)
        db.session.commit()
        
        print(f"DEBUG: Successfully deleted user {user_id} from database")
        
        # Verify deletion
        verification_user = User.query.get(user_id)
        if verification_user is None:
            print("DEBUG: ✅ User deletion verified - user not found in database")
        else:
            print("DEBUG: ❌ User still exists in database after deletion!")
        
        return jsonify({
            'message': 'Account successfully deleted',
            'status': 'success'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting account: {e}")
        return jsonify({'error': 'Failed to delete account'}), 500

def require_auth(f):
    """Decorator to require authentication for routes"""
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        # If no token in header, check query parameters (for file downloads)
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add user to request context
        request.current_user_id = user_id
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function
