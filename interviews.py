from flask import Blueprint, request, jsonify
from services.auth import require_auth
from models import db, Interview, Application, User, Job, Resume
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

interviews_bp = Blueprint('interviews', __name__)

@interviews_bp.route('/', methods=['POST'])
@require_auth
def schedule_interview():
    """Schedule a new interview"""
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'Access denied. HR role required.'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['application_id', 'interview_type', 'title', 'scheduled_at']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if application exists and belongs to HR user's jobs
        application = Application.query.get(data['application_id'])
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        if application.job.created_by != user.id:
            return jsonify({'error': 'You can only schedule interviews for your job postings'}), 403
        
        # Parse scheduled datetime
        try:
            scheduled_at = datetime.fromisoformat(data['scheduled_at'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid datetime format for scheduled_at'}), 400
        
        # Create interview
        interview = Interview(
            application_id=data['application_id'],
            interviewer_id=data.get('interviewer_id', user.id),
            interview_type=data['interview_type'],
            title=data['title'],
            description=data.get('description', ''),
            scheduled_at=scheduled_at,
            duration_minutes=data.get('duration_minutes', 60),
            location=data.get('location', ''),
            meeting_link=data.get('meeting_link', ''),
            status='scheduled'
        )
        
        db.session.add(interview)
        
        # Update application status to 'interview_scheduled' if it's still pending
        if application.status == 'pending':
            application.status = 'interview_scheduled'
        
        db.session.commit()
        
        logger.info(f"Interview scheduled by HR {user.id} for application {application.id}")
        
        # Send real-time notification to candidate
        from services.realtime_service import broadcast_interview_scheduled
        candidate_user_id = application.resume.user_id
        interview_data = interview.to_dict()
        interview_data['job_title'] = application.job.title
        interview_data['company'] = application.job.company
        
        broadcast_interview_scheduled(candidate_user_id, interview_data)
        
        return jsonify({
            'success': True,
            'message': 'Interview scheduled successfully',
            'interview': interview.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error scheduling interview: {str(e)}")
        return jsonify({'error': 'Failed to schedule interview'}), 500

@interviews_bp.route('/', methods=['GET'])
@require_auth
def list_interviews():
    """Get interviews based on user role"""
    try:
        user = User.query.get(request.current_user_id)
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get query parameters
        status = request.args.get('status')  # scheduled, completed, cancelled
        interview_type = request.args.get('type')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Base query depending on user role
        if user.role == 'hr':
            # HR sees interviews for their job postings
            query = db.session.query(Interview).join(Application).join(Job).filter(
                Job.created_by == user.id
            )
        elif user.role == 'candidate':
            # Candidates see their own interviews
            query = db.session.query(Interview).join(Application).join(Resume).filter(
                Resume.user_id == user.id
            )
        else:
            return jsonify({'error': 'Invalid user role'}), 403
        
        # Apply filters
        if status:
            query = query.filter(Interview.status == status)
        if interview_type:
            query = query.filter(Interview.interview_type == interview_type)
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from)
                query = query.filter(Interview.scheduled_at >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format'}), 400
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to)
                query = query.filter(Interview.scheduled_at <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format'}), 400
        
        # Order by scheduled date
        query = query.order_by(Interview.scheduled_at)
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        interviews_data = [interview.to_dict() for interview in pagination.items]
        
        return jsonify({
            'success': True,
            'interviews': interviews_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing interviews: {str(e)}")
        return jsonify({'error': 'Failed to load interviews'}), 500

@interviews_bp.route('/<int:interview_id>', methods=['GET'])
@require_auth
def get_interview(interview_id):
    """Get interview details"""
    try:
        user = User.query.get(request.current_user_id)
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        interview = Interview.query.get(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404
        
        # Check permissions
        has_permission = False
        if user.role == 'hr' and interview.application.job.created_by == user.id:
            has_permission = True
        elif user.role == 'candidate' and interview.application.resume.user_id == user.id:
            has_permission = True
        elif interview.interviewer_id == user.id:
            has_permission = True
        
        if not has_permission:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'success': True,
            'interview': interview.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting interview: {str(e)}")
        return jsonify({'error': 'Failed to load interview'}), 500

@interviews_bp.route('/<int:interview_id>', methods=['PUT'])
@require_auth
def update_interview(interview_id):
    """Update interview details"""
    try:
        user = User.query.get(request.current_user_id)
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        interview = Interview.query.get(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404
        
        # Check permissions (HR who created the job or the interviewer)
        has_permission = False
        if user.role == 'hr' and interview.application.job.created_by == user.id:
            has_permission = True
        elif interview.interviewer_id == user.id:
            has_permission = True
        
        if not has_permission:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        # Update allowed fields
        if 'title' in data:
            interview.title = data['title']
        if 'description' in data:
            interview.description = data['description']
        if 'scheduled_at' in data:
            try:
                interview.scheduled_at = datetime.fromisoformat(data['scheduled_at'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid datetime format'}), 400
        if 'duration_minutes' in data:
            interview.duration_minutes = data['duration_minutes']
        if 'location' in data:
            interview.location = data['location']
        if 'meeting_link' in data:
            interview.meeting_link = data['meeting_link']
        if 'status' in data:
            interview.status = data['status']
            if data['status'] == 'completed' and not interview.completed_at:
                interview.completed_at = datetime.utcnow()
        if 'feedback' in data:
            interview.feedback = data['feedback']
        if 'rating' in data:
            interview.rating = data['rating']
        if 'recommendation' in data:
            interview.recommendation = data['recommendation']
        
        interview.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Interview {interview_id} updated by user {user.id}")
        
        # Send real-time notification to candidate if interview was updated
        from services.realtime_service import broadcast_interview_updated
        candidate_user_id = interview.application.resume.user_id
        interview_data = interview.to_dict()
        interview_data['job_title'] = interview.application.job.title
        interview_data['company'] = interview.application.job.company
        
        broadcast_interview_updated(candidate_user_id, interview_data)
        
        return jsonify({
            'success': True,
            'message': 'Interview updated successfully',
            'interview': interview.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating interview: {str(e)}")
        return jsonify({'error': 'Failed to update interview'}), 500

@interviews_bp.route('/<int:interview_id>', methods=['DELETE'])
@require_auth
def cancel_interview(interview_id):
    """Cancel an interview"""
    try:
        user = User.query.get(request.current_user_id)
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        interview = Interview.query.get(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404
        
        # Check permissions (only HR who created the job)
        if user.role != 'hr' or interview.application.job.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        interview.status = 'cancelled'
        interview.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Interview {interview_id} cancelled by HR {user.id}")
        
        # Send real-time notification to candidate
        from services.realtime_service import broadcast_interview_cancelled
        candidate_user_id = interview.application.resume.user_id
        interview_data = interview.to_dict()
        interview_data['job_title'] = interview.application.job.title
        interview_data['company'] = interview.application.job.company
        
        broadcast_interview_cancelled(candidate_user_id, interview_data)
        
        return jsonify({
            'success': True,
            'message': 'Interview cancelled successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cancelling interview: {str(e)}")
        return jsonify({'error': 'Failed to cancel interview'}), 500

@interviews_bp.route('/upcoming', methods=['GET'])
@require_auth
def get_upcoming_interviews():
    """Get upcoming interviews for the current user"""
    try:
        user = User.query.get(request.current_user_id)
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get upcoming interviews (next 7 days)
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=7)
        
        if user.role == 'hr':
            # HR sees upcoming interviews for their job postings
            interviews = db.session.query(Interview).join(Application).join(Job).filter(
                Job.created_by == user.id,
                Interview.scheduled_at >= start_date,
                Interview.scheduled_at <= end_date,
                Interview.status == 'scheduled'
            ).order_by(Interview.scheduled_at).all()
        elif user.role == 'candidate':
            # Candidates see their upcoming interviews
            interviews = db.session.query(Interview).join(Application).join(Resume).filter(
                Resume.user_id == user.id,
                Interview.scheduled_at >= start_date,
                Interview.scheduled_at <= end_date,
                Interview.status == 'scheduled'
            ).order_by(Interview.scheduled_at).all()
        else:
            return jsonify({'error': 'Invalid user role'}), 403
        
        interviews_data = [interview.to_dict() for interview in interviews]
        
        return jsonify({
            'success': True,
            'interviews': interviews_data,
            'count': len(interviews_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting upcoming interviews: {str(e)}")
        return jsonify({'error': 'Failed to load upcoming interviews'}), 500

@interviews_bp.route('/calendar', methods=['GET'])
@require_auth
def get_interview_calendar():
    """Get interview calendar data"""
    try:
        user = User.query.get(request.current_user_id)
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get month/year parameters
        month = request.args.get('month', datetime.utcnow().month, type=int)
        year = request.args.get('year', datetime.utcnow().year, type=int)
        
        # Calculate date range for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        if user.role == 'hr':
            interviews = db.session.query(Interview).join(Application).join(Job).filter(
                Job.created_by == user.id,
                Interview.scheduled_at >= start_date,
                Interview.scheduled_at < end_date
            ).order_by(Interview.scheduled_at).all()
        elif user.role == 'candidate':
            interviews = db.session.query(Interview).join(Application).join(Resume).filter(
                Resume.user_id == user.id,
                Interview.scheduled_at >= start_date,
                Interview.scheduled_at < end_date
            ).order_by(Interview.scheduled_at).all()
        else:
            return jsonify({'error': 'Invalid user role'}), 403
        
        # Group interviews by date
        calendar_data = {}
        for interview in interviews:
            date_key = interview.scheduled_at.date().isoformat()
            if date_key not in calendar_data:
                calendar_data[date_key] = []
            calendar_data[date_key].append(interview.to_dict())
        
        return jsonify({
            'success': True,
            'calendar_data': calendar_data,
            'month': month,
            'year': year
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting interview calendar: {str(e)}")
        return jsonify({'error': 'Failed to load interview calendar'}), 500

@interviews_bp.route('/candidate', methods=['GET'])
@require_auth
def get_candidate_interviews():
    """Get interviews for the authenticated candidate"""
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'candidate':
            return jsonify({'error': 'Access denied. Candidate role required.'}), 403
        
        # Get query parameters
        status = request.args.get('status')  # scheduled, completed, cancelled
        upcoming_only = request.args.get('upcoming_only', 'false').lower() == 'true'
        
        # Base query for candidate's interviews
        query = db.session.query(Interview)\
            .join(Application, Interview.application_id == Application.id)\
            .join(Resume, Application.resume_id == Resume.id)\
            .join(Job, Application.job_id == Job.id)\
            .filter(Resume.user_id == user.id)
        
        # Apply filters
        if status:
            query = query.filter(Interview.status == status)
        
        if upcoming_only:
            query = query.filter(Interview.scheduled_at > datetime.utcnow())
        
        # Order by scheduled date
        interviews = query.order_by(Interview.scheduled_at.desc()).all()
        
        # Prepare interview data with job and application info
        interview_data = []
        for interview in interviews:
            interview_dict = interview.to_dict()
            interview_dict['job_title'] = interview.application.job.title
            interview_dict['company'] = interview.application.job.company
            interview_data.append(interview_dict)
        
        return jsonify({
            'success': True,
            'interviews': interview_data,
            'count': len(interview_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting candidate interviews: {str(e)}")
        return jsonify({'error': 'Failed to load interviews'}), 500

@interviews_bp.route('/candidate/count', methods=['GET'])
@require_auth
def get_candidate_interview_count():
    """Get upcoming interview count for the authenticated candidate"""
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'candidate':
            return jsonify({'error': 'Access denied. Candidate role required.'}), 403
        
        # Count upcoming interviews
        count = db.session.query(Interview)\
            .join(Application, Interview.application_id == Application.id)\
            .join(Resume, Application.resume_id == Resume.id)\
            .filter(
                Resume.user_id == user.id,
                Interview.status == 'scheduled',
                Interview.scheduled_at > datetime.utcnow()
            ).count()
        
        return jsonify({
            'success': True,
            'count': count
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting candidate interview count: {str(e)}")
        return jsonify({'error': 'Failed to load interview count'}), 500

@interviews_bp.route('/candidate/upcoming', methods=['GET'])
@require_auth
def get_candidate_upcoming_interviews():
    """Get upcoming interviews for the authenticated candidate"""
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'candidate':
            return jsonify({'error': 'Access denied. Candidate role required.'}), 403
        
        # Get upcoming interviews (next 30 days)
        end_date = datetime.utcnow() + timedelta(days=30)
        
        interviews = db.session.query(Interview)\
            .join(Application, Interview.application_id == Application.id)\
            .join(Resume, Application.resume_id == Resume.id)\
            .join(Job, Application.job_id == Job.id)\
            .filter(
                Resume.user_id == user.id,
                Interview.status == 'scheduled',
                Interview.scheduled_at > datetime.utcnow(),
                Interview.scheduled_at <= end_date
            ).order_by(Interview.scheduled_at).all()
        
        # Prepare interview data
        interview_data = []
        for interview in interviews:
            interview_dict = interview.to_dict()
            interview_dict['job_title'] = interview.application.job.title
            interview_dict['company'] = interview.application.job.company
            interview_dict['days_until'] = (interview.scheduled_at.date() - datetime.utcnow().date()).days
            interview_data.append(interview_dict)
        
        return jsonify({
            'success': True,
            'interviews': interview_data,
            'count': len(interview_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting upcoming interviews: {str(e)}")
        return jsonify({'error': 'Failed to load upcoming interviews'}), 500
