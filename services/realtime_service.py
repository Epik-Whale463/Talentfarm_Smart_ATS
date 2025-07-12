# Real-time Service for WebSocket Communication and Live Data Updates
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from functools import wraps
import jwt
from datetime import datetime, timedelta
import json
from models import db, User, Resume, Job, Application
from config import Config

# Initialize SocketIO
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

# Store active connections
active_connections = {}

def require_socket_auth(f):
    """Decorator for socket authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Try to get token from different sources
        token = None
        
        # 1. Check query parameters
        token = request.args.get('token')
        
        # 2. Check auth data if available
        if not token and hasattr(request, 'auth') and request.auth:
            token = request.auth.get('token')
            
        # 3. Check if token is passed in the event data
        if not token and args and len(args) > 0 and isinstance(args[0], dict):
            token = args[0].get('token')
        
        if not token:
            print(f"No token found in socket request for {f.__name__}")
            print(f"Request args: {dict(request.args)}")
            print(f"Request auth: {getattr(request, 'auth', None)}")
            print(f"Event args: {args}")
            emit('error', {'message': 'Authentication required'})
            return
        
        try:
            payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(payload['user_id'])
            if not current_user:
                emit('error', {'message': 'Invalid token'})
                return
            
            kwargs['current_user'] = current_user
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            print(f"Token expired for socket request to {f.__name__}")
            emit('error', {'message': 'Token expired'})
        except jwt.InvalidTokenError as e:
            print(f"Invalid token for socket request to {f.__name__}: {str(e)}")
            emit('error', {'message': 'Invalid token'})
        except Exception as e:
            print(f"Authentication error in {f.__name__}: {str(e)}")
            emit('error', {'message': 'Authentication failed'})
    
    return decorated

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to real-time service'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")
    if request.sid in active_connections:
        del active_connections[request.sid]

@socketio.on('join_user_room')
@require_socket_auth
def handle_join_user_room(data=None, **kwargs):
    """Join user-specific room for real-time updates"""
    try:
        current_user = kwargs.get('current_user')
        if not current_user:
            emit('error', {'message': 'Authentication failed'})
            return
            
        room = f"user_{current_user.id}"
        join_room(room)
        active_connections[request.sid] = {
            'user_id': current_user.id,
            'room': room,
            'connected_at': datetime.utcnow()
        }
        
        # Send initial dashboard data
        dashboard_data = get_dashboard_data(current_user.id)
        emit('dashboard_update', dashboard_data)
        emit('joined_room', {'room': room, 'message': 'Successfully joined real-time updates'})
    except Exception as e:
        print(f"Error in handle_join_user_room: {str(e)}")
        emit('error', {'message': 'Failed to join user room'})

@socketio.on('request_dashboard_update')
@require_socket_auth
def handle_dashboard_update_request(data=None, **kwargs):
    """Handle manual dashboard update request"""
    try:
        current_user = kwargs.get('current_user')
        if not current_user:
            emit('error', {'message': 'Authentication failed'})
            return
            
        dashboard_data = get_dashboard_data(current_user.id)
        emit('dashboard_update', dashboard_data)
    except Exception as e:
        print(f"Error in handle_dashboard_update_request: {str(e)}")
        emit('error', {'message': 'Failed to update dashboard'})

def get_dashboard_data(user_id):
    """Get comprehensive dashboard data for a user"""
    try:
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}
        
        # Get user's resumes
        resumes = Resume.query.filter_by(user_id=user_id).all()
        resume_data = []
        for resume in resumes:
            resume_dict = resume.to_dict()
            # Add application count for each resume
            app_count = Application.query.filter_by(resume_id=resume.id).count()
            resume_dict['application_count'] = app_count
            resume_data.append(resume_dict)
        
        # Get user's applications
        applications = db.session.query(Application)\
            .join(Resume, Application.resume_id == Resume.id)\
            .filter(Resume.user_id == user_id)\
            .all()
        
        # Calculate application statistics
        total_applications = len(applications)
        application_statuses = {}
        match_scores = []
        
        for app in applications:
            status = app.status or 'pending'
            application_statuses[status] = application_statuses.get(status, 0) + 1
            if app.match_score:
                match_scores.append(app.match_score)
        
        avg_match_score = sum(match_scores) / len(match_scores) if match_scores else 0
        
        # Get recent applications (last 10)
        recent_applications = db.session.query(Application)\
            .join(Resume, Application.resume_id == Resume.id)\
            .join(Job, Application.job_id == Job.id)\
            .filter(Resume.user_id == user_id)\
            .order_by(Application.created_at.desc())\
            .limit(10).all()
        
        recent_app_data = []
        for app in recent_applications:
            recent_app_data.append({
                'id': app.id,
                'job_title': app.job.title,
                'company': app.job.company,
                'status': app.status or 'pending',
                'match_score': app.match_score,
                'applied_at': app.created_at.isoformat() if app.created_at else None
            })
        
        # Get total available jobs
        total_jobs = Job.query.count()
        
        # Get jobs user might be interested in (based on skills matching)
        recommended_jobs = get_recommended_jobs(user_id, limit=5)
        
        # Calculate profile completion
        profile_completion = calculate_profile_completion(user)
        
        return {
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role
            },
            'statistics': {
                'resume_count': len(resumes),
                'application_count': total_applications,
                'job_count': total_jobs,
                'avg_match_score': round(avg_match_score, 1),
                'profile_completion': profile_completion
            },
            'application_statuses': application_statuses,
            'recent_resumes': [r for r in resume_data[:5]],
            'recent_applications': recent_app_data,
            'recommended_jobs': recommended_jobs,
            'last_updated': datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        print(f"Error getting dashboard data: {e}")
        return {'error': str(e)}

def get_recommended_jobs(user_id, limit=5):
    """Get recommended jobs for a user based on their skills and experience"""
    try:
        # Get user's latest resume for skill matching
        latest_resume = Resume.query.filter_by(user_id=user_id)\
            .order_by(Resume.created_at.desc()).first()
        
        if not latest_resume or not latest_resume.parsed_data:
            # Return random jobs if no resume data
            jobs = Job.query.order_by(Job.created_at.desc()).limit(limit).all()
        else:
            # Simple keyword matching for skills
            parsed_data = json.loads(latest_resume.parsed_data) if isinstance(latest_resume.parsed_data, str) else latest_resume.parsed_data
            user_skills = parsed_data.get('skills', [])
            
            if user_skills:
                # Find jobs that match user skills
                jobs = Job.query.filter(
                    db.or_(*[Job.requirements.ilike(f'%{skill}%') for skill in user_skills[:5]])
                ).limit(limit).all()
            else:
                jobs = Job.query.order_by(Job.created_at.desc()).limit(limit).all()
        
        return [job.to_dict() for job in jobs]
    
    except Exception as e:
        print(f"Error getting recommended jobs: {e}")
        return []

def calculate_profile_completion(user):
    """Calculate user profile completion percentage"""
    completion = 0
    total_fields = 6
    
    if user.name: completion += 1
    if user.email: completion += 1
    if user.role: completion += 1
    
    # Check if user has at least one resume
    if Resume.query.filter_by(user_id=user.id).first():
        completion += 1
    
    # Check if user has applied to jobs
    if db.session.query(Application).join(Resume).filter(Resume.user_id == user.id).first():
        completion += 1
    
    # Check if user has complete resume data
    latest_resume = Resume.query.filter_by(user_id=user.id)\
        .order_by(Resume.created_at.desc()).first()
    if latest_resume and latest_resume.parsed_data:
        completion += 1
    
    return round((completion / total_fields) * 100)

def broadcast_dashboard_update(user_id, event_type='general_update', data=None):
    """Broadcast dashboard update to specific user"""
    room = f"user_{user_id}"
    dashboard_data = get_dashboard_data(user_id)
    
    if data:
        dashboard_data['event'] = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    socketio.emit('dashboard_update', dashboard_data, room=room)

def broadcast_new_job(job_data):
    """Broadcast new job to all connected users"""
    socketio.emit('new_job_posted', {
        'job': job_data,
        'timestamp': datetime.utcnow().isoformat()
    }, broadcast=True)

def broadcast_application_status_change(user_id, application_data):
    """Broadcast application status change to user"""
    room = f"user_{user_id}"
    socketio.emit('application_status_changed', {
        'application': application_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)

def broadcast_interview_scheduled(candidate_user_id, interview_data):
    """Broadcast interview scheduled notification to candidate"""
    room = f"user_{candidate_user_id}"
    socketio.emit('interview_scheduled', {
        'interview': interview_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)

def broadcast_interview_updated(candidate_user_id, interview_data):
    """Broadcast interview update notification to candidate"""
    room = f"user_{candidate_user_id}"
    socketio.emit('interview_updated', {
        'interview': interview_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)

def broadcast_interview_cancelled(candidate_user_id, interview_data):
    """Broadcast interview cancellation notification to candidate"""
    room = f"user_{candidate_user_id}"
    socketio.emit('interview_cancelled', {
        'interview': interview_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)

# Real-time job statistics
@socketio.on('request_job_stats')
def handle_job_stats_request():
    """Handle job statistics request"""
    try:
        total_jobs = Job.query.count()
        recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()
        
        # Job categories count
        categories = db.session.query(Job.category, db.func.count(Job.id))\
            .group_by(Job.category)\
            .all()
        
        category_stats = [{'category': cat, 'count': count} for cat, count in categories]
        
        # Jobs by location
        locations = db.session.query(Job.location, db.func.count(Job.id))\
            .group_by(Job.location)\
            .limit(10)\
            .all()
        
        location_stats = [{'location': loc, 'count': count} for loc, count in locations]
        
        emit('job_stats_update', {
            'total_jobs': total_jobs,
            'recent_jobs': [job.to_dict() for job in recent_jobs],
            'category_stats': category_stats,
            'location_stats': location_stats,
            'last_updated': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        emit('error', {'message': f'Failed to get job stats: {str(e)}'})

def get_active_connections_count():
    """Get count of active WebSocket connections"""
    return len(active_connections)

def get_user_connection_info(user_id):
    """Get connection info for a specific user"""
    for sid, conn_info in active_connections.items():
        if conn_info['user_id'] == user_id:
            return conn_info
    return None
