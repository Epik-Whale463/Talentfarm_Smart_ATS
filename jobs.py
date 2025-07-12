from flask import Blueprint, request, jsonify, abort, current_app
from services.auth import require_auth
from models import db, Job, User, Resume, Application
import json
from datetime import datetime, timedelta
from sqlalchemy import func, desc, or_, and_
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/', methods=['GET'])
@require_auth
def list_jobs():
    """
    Get active job listings with role-based views:
    - Candidates see all active jobs
    - HR users see a summary of jobs with application stats
    """
    try:
        # Get authenticated user
        user = User.query.get(request.current_user_id)
        if not user:
            return jsonify({'jobs': [], 'message': 'Authentication required'}), 401
        
        # Get pagination and filter parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        category = request.args.get('category')
        location = request.args.get('location')
        search = request.args.get('search')
        salary_min = request.args.get('salary_min', type=int)
        salary_max = request.args.get('salary_max', type=int)
        job_type = request.args.get('type')  # employment_type filter
        
        # Base query
        query = Job.query.filter_by(is_active=True)
        
        # Apply filters
        if category:
            query = query.filter(Job.category == category)
        if location:
            query = query.filter(Job.location.ilike(f'%{location}%'))
        if salary_min:
            query = query.filter(Job.salary_max >= salary_min)
        if salary_max:
            query = query.filter(Job.salary_min <= salary_max)
        if job_type:
            query = query.filter(Job.employment_type == job_type)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Job.title.ilike(search_term),
                    Job.company.ilike(search_term),
                    Job.description.ilike(search_term),
                    Job.location.ilike(search_term)
                )
            )
        
        # Apply role-specific logic
        if user.role == 'hr':
            # For HR users, only show jobs they created
            query = query.filter(Job.created_by == user.id)
        
        # Paginate results
        jobs_paginated = query.order_by(desc(Job.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get job data with role-specific information
        job_data = []
        for job in jobs_paginated.items:
            job_dict = job.to_dict()
            
            # For HR users, add application statistics
            if user.role == 'hr':
                # Get application counts by status
                status_counts = db.session.query(
                    Application.status, 
                    func.count(Application.id)
                ).filter(
                    Application.job_id == job.id
                ).group_by(
                    Application.status
                ).all()
                
                # Format stats for easy frontend consumption
                job_dict['application_stats'] = {
                    'total': sum(count for _, count in status_counts),
                    'statuses': {status: count for status, count in status_counts}
                }
            
            # For candidates, check if they've already applied
            elif user.role == 'candidate':
                # Check if candidate has applied to this job
                user_resumes = [r.id for r in user.resumes]
                if user_resumes:
                    has_applied = Application.query.filter(
                        Application.job_id == job.id,
                        Application.resume_id.in_(user_resumes)
                    ).first() is not None
                    
                    job_dict['has_applied'] = has_applied
            
            job_data.append(job_dict)
        
        # Get available categories, locations, and job types for filters
        categories = [c[0] for c in db.session.query(Job.category).distinct().all() if c[0]]
        locations = [l[0] for l in db.session.query(Job.location).distinct().all() if l[0]]
        job_types = [t[0] for t in db.session.query(Job.employment_type).distinct().all() if t[0]]
        
        return jsonify({
            'jobs': job_data,
            'filters': {
                'categories': categories,
                'locations': locations, 
                'job_types': job_types
            },
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': jobs_paginated.total,
                'pages': jobs_paginated.pages,
                'has_next': jobs_paginated.has_next,
                'has_prev': jobs_paginated.has_prev
            }
        }), 200
    except Exception as e:
        logger.error(f"Error in list_jobs: {str(e)}")
        return jsonify({'message': 'Error retrieving jobs'}), 500

@jobs_bp.route('/', methods=['POST'])
@require_auth
def create_job():
    """Create a new job posting (HR/Recruiter only)"""
    try:
        # Verify user is HR/recruiter
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({
                'success': False,
                'message': 'Only HR/recruiter users can post jobs'
            }), 403
            
        # Validate request data
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
            
        # Check required fields
        required_fields = ['title', 'company', 'location', 'description', 'requirements', 'type', 'category']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}',
                'fields': missing_fields
            }), 400
        
        # Process requirements from string to list
        requirements = data['requirements']
        if isinstance(requirements, str):
            # Try splitting by newlines first
            requirements = [r.strip() for r in requirements.replace('\r', '').split('\n') if r.strip()]
            # If no newlines found, try splitting by commas
            if not requirements:
                requirements = [r.strip() for r in data['requirements'].split(',') if r.strip()]
        
        # Process salary information
        salary_min = None
        if data.get('min_salary'):
            try:
                salary_min = int(data['min_salary'])
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Minimum salary must be a number'
                }), 400
                
        salary_max = None
        if data.get('max_salary'):
            try:
                salary_max = int(data['max_salary'])
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Maximum salary must be a number'
                }), 400
        
        # Validate salary range if both provided
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            return jsonify({
                'success': False,
                'message': 'Minimum salary cannot be greater than maximum salary'
            }), 400
            
        # Create new job listing
        job = Job(
            title=data['title'],
            company=data['company'],
            location=data['location'],
            description=data['description'],
            requirements=requirements,
            employment_type=data['type'],
            category=data['category'],
            salary_min=salary_min,
            salary_max=salary_max,
            created_by=user.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        # Save to database
        db.session.add(job)
        db.session.commit()
        
        # Auto-sync to vector database
        try:
            from services.rag_service import RAGTalentService
            rag_service = RAGTalentService()
            sync_success = rag_service.auto_sync_job(job, 'create')
            if sync_success:
                logger.info(f"Job {job.id} synced to vector database")
            else:
                logger.warning(f"Failed to sync job {job.id} to vector database")
        except Exception as sync_error:
            logger.error(f"Vector database sync error: {sync_error}")
        
        # Notify the frontend about success
        try:
            from services.realtime_service import broadcast_dashboard_update
            broadcast_dashboard_update(
                user.id,
                'job_posted',
                {
                    'job_id': job.id,
                    'title': job.title,
                    'company': job.company
                }
            )
        except Exception as broadcast_error:
            logger.warning(f"Failed to broadcast job creation: {broadcast_error}")
        
        return jsonify({
            'success': True,
            'message': 'Job posted successfully',
            'job': job.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error in create_job: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred while creating the job'
        }), 500

@jobs_bp.route('/dashboard', methods=['GET'])
@require_auth
def get_job_dashboard():
    """
    Get comprehensive dashboard data for HR/Recruiter users.
    This includes job listings with application statistics.
    """
    try:
        # Verify user is HR/Recruiter
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({
                'success': False,
                'message': 'Only HR users can access this dashboard'
            }), 403
            
        # Get filter parameters
        status_filter = request.args.get('status')
        date_range = request.args.get('date_range')
        category = request.args.get('category')
        
        # Base query - jobs created by this HR user
        jobs_query = Job.query.filter_by(created_by=user.id)
        
        # Apply filters
        if status_filter == 'active':
            jobs_query = jobs_query.filter_by(is_active=True)
        elif status_filter == 'inactive':
            jobs_query = jobs_query.filter_by(is_active=False)
            
        if category:
            jobs_query = jobs_query.filter_by(category=category)
            
        # Apply date range filter if provided
        if date_range:
            # Parse date range (e.g., "7d", "30d", "90d")
            try:
                days = int(date_range[:-1])
                from_date = datetime.utcnow() - timedelta(days=days)
                jobs_query = jobs_query.filter(Job.created_at >= from_date)
            except (ValueError, IndexError):
                pass  # Ignore invalid date range
                
        # Get all jobs
        jobs = jobs_query.order_by(desc(Job.created_at)).all()
        
        # Enhanced job data with application statistics
        enhanced_jobs = []
        
        for job in jobs:
            job_dict = job.to_dict()
            
            # Get application counts
            application_counts = db.session.query(
                func.count(Application.id)
            ).filter(
                Application.job_id == job.id
            ).first()
            
            total_applications = application_counts[0] if application_counts else 0
            
            # Get application status breakdown
            status_breakdown = db.session.query(
                Application.status,
                func.count(Application.id)
            ).filter(
                Application.job_id == job.id
            ).group_by(
                Application.status
            ).all()
            
            status_counts = {
                status: count for status, count in status_breakdown
            }
            
            # Get average match score
            avg_match = db.session.query(
                func.avg(Application.match_score)
            ).filter(
                Application.job_id == job.id
            ).scalar()
            
            # Add statistics to job data
            job_dict['stats'] = {
                'total_applications': total_applications,
                'status_counts': status_counts,
                'avg_match_score': round(float(avg_match or 0), 2),
                'days_active': (datetime.utcnow() - job.created_at).days
            }
            
            enhanced_jobs.append(job_dict)
        
        # Overall dashboard statistics
        total_jobs = len(enhanced_jobs)
        active_jobs = sum(1 for job in enhanced_jobs if job['is_active'])
        total_applications = sum(job['stats']['total_applications'] for job in enhanced_jobs)
        
        # Get recent applications
        recent_applications = db.session.query(
            Application, Job, Resume, User
        ).join(
            Job, Application.job_id == Job.id
        ).join(
            Resume, Application.resume_id == Resume.id
        ).join(
            User, Resume.user_id == User.id
        ).filter(
            Job.created_by == user.id
        ).order_by(
            desc(Application.created_at)
        ).limit(5).all()
        
        recent_apps_data = [{
            'id': app.id,
            'candidate_name': user.name,
            'candidate_email': user.email,
            'job_title': job.title,
            'job_id': job.id,
            'applied_at': app.created_at.isoformat(),
            'status': app.status,
            'match_score': app.match_score
        } for app, job, resume, user in recent_applications]
            
        return jsonify({
            'success': True,
            'jobs': enhanced_jobs,
            'stats': {
                'total_jobs': total_jobs,
                'active_jobs': active_jobs,
                'total_applications': total_applications,
                'recent_applications': recent_apps_data,
                'application_rate': round(total_applications / total_jobs, 2) if total_jobs > 0 else 0
            },
            'categories': list(set(job['category'] for job in enhanced_jobs if job.get('category')))
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_job_dashboard: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Error retrieving dashboard data'
        }), 500

@jobs_bp.route('/<int:job_id>', methods=['GET'])
@require_auth
def get_job(job_id):
    """
    Get detailed job information by ID with role-specific data:
    - Candidates see job details and application status if they've applied
    - HR users see job details with application statistics
    """
    try:
        # Get the job
        job = Job.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'message': 'Job not found'
            }), 404
        
        # Get the authenticated user
        user = User.query.get(request.current_user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401
            
        # Get basic job data
        job_data = job.to_dict()
        
        # Add role-specific data
        if user.role == 'hr':
            # Only allow HR users to see their own jobs or check ownership
            if job.created_by != user.id:
                return jsonify({
                    'success': False,
                    'message': 'You do not have permission to view this job'
                }), 403
                
            # Add application statistics for HR users
            app_stats = db.session.query(
                Application.status,
                func.count(Application.id)
            ).filter(
                Application.job_id == job.id
            ).group_by(
                Application.status
            ).all()
            
            # Format application statistics
            job_data['application_stats'] = {
                status: count for status, count in app_stats
            }
            
            # Get high match score applications
            top_applications = db.session.query(
                Application, Resume, User
            ).join(
                Resume, Application.resume_id == Resume.id
            ).join(
                User, Resume.user_id == User.id
            ).filter(
                Application.job_id == job.id,
                Application.match_score >= 0.7
            ).order_by(
                desc(Application.match_score)
            ).limit(5).all()
            
            # Format top applications
            job_data['top_candidates'] = [{
                'id': app.id,
                'name': user.name,
                'match_score': app.match_score,
                'status': app.status,
                'applied_at': app.created_at.isoformat() if app.created_at else None
            } for app, resume, user in top_applications]
            
        elif user.role == 'candidate':
            # For candidates, check if they've applied to this job
            user_resumes = [resume.id for resume in user.resumes]
            if user_resumes:
                application = Application.query.filter(
                    Application.job_id == job.id,
                    Application.resume_id.in_(user_resumes)
                ).first()
                
                if application:
                    # Add application information for the candidate
                    job_data['application'] = {
                        'id': application.id,
                        'status': application.status,
                        'match_score': application.match_score,
                        'applied_at': application.created_at.isoformat() if application.created_at else None,
                        'resume_id': application.resume_id
                    }
                
            # Add similar jobs recommendations for candidates
            similar_jobs = Job.query.filter(
                Job.id != job.id,
                Job.is_active == True,
                or_(
                    Job.category == job.category,
                    Job.employment_type == job.employment_type
                )
            ).order_by(
                desc(Job.created_at)
            ).limit(3).all()
            
            job_data['similar_jobs'] = [j.to_dict() for j in similar_jobs]
            
        return jsonify({
            'success': True,
            'job': job_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_job: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Error retrieving job details'
        }), 500

@jobs_bp.route('/<int:job_id>', methods=['PUT'])
@require_auth
def update_job(job_id):
    """
    Update a job listing with validation and change tracking.
    Only HR users who created the job can update it.
    """
    try:
        # Verify user is HR
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({
                'success': False,
                'message': 'Only HR/recruiter users can update jobs'
            }), 403
        
        # Find the job
        job = Job.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'message': 'Job not found'
            }), 404
        
        # Verify ownership
        if job.created_by != user.id:
            return jsonify({
                'success': False,
                'message': 'You can only update jobs that you created'
            }), 403
        
        # Get update data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No update data provided'
            }), 400
            
        # Track changes for notification
        changes = []
        
        # Process fields with validation
        if 'title' in data and data['title']:
            old_title = job.title
            job.title = data['title']
            changes.append('title')
        
        if 'company' in data and data['company']:
            old_company = job.company
            job.company = data['company']
            changes.append('company')
        
        if 'description' in data and data['description']:
            job.description = data['description']
            changes.append('description')
        
        if 'location' in data and data['location']:
            job.location = data['location']
            changes.append('location')
        
        # Process requirements field specially if it exists
        if 'requirements' in data:
            requirements = data['requirements']
            
            # Convert string requirements to list if needed
            if isinstance(requirements, str):
                # Try splitting by newlines first
                requirements = [r.strip() for r in requirements.replace('\r', '').split('\n') if r.strip()]
                # If no newlines found, try splitting by commas
                if not requirements:
                    requirements = [r.strip() for r in data['requirements'].split(',') if r.strip()]
            
            job.requirements = requirements
            changes.append('requirements')
        
        # Process salary fields with validation
        if 'min_salary' in data:
            try:
                if data['min_salary'] is None:
                    job.salary_min = None
                else:
                    job.salary_min = int(data['min_salary'])
                changes.append('salary_min')
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Minimum salary must be a number'
                }), 400
        
        if 'max_salary' in data:
            try:
                if data['max_salary'] is None:
                    job.salary_max = None
                else:
                    job.salary_max = int(data['max_salary'])
                changes.append('salary_max')
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Maximum salary must be a number'
                }), 400
        
        # Validate salary range if both are provided
        if job.salary_min is not None and job.salary_max is not None and job.salary_min > job.salary_max:
            return jsonify({
                'success': False,
                'message': 'Minimum salary cannot be greater than maximum salary'
            }), 400
        
        # Update type/category
        if 'type' in data and data['type']:
            job.employment_type = data['type']
            changes.append('employment_type')
            
        if 'category' in data and data['category']:
            job.category = data['category']
            changes.append('category')
            
        # Update active status
        if 'is_active' in data:
            job.is_active = bool(data['is_active'])
            changes.append('active status')
        
        # Set updated timestamp
        job.updated_at = datetime.utcnow()
        
        # Save changes to database
        db.session.commit()
        
        # Auto-sync update to vector database
        try:
            from services.rag_service import RAGTalentService
            rag_service = RAGTalentService()
            sync_success = rag_service.auto_sync_job(job, 'update')
            if sync_success:
                logger.info(f"Job {job.id} updated in vector database")
            else:
                logger.warning(f"Failed to update job {job.id} in vector database")
        except Exception as sync_error:
            logger.error(f"Vector database sync error during job update: {sync_error}")
        
        # Notify about update
        try:
            from services.realtime_service import broadcast_dashboard_update
            
            # Notify HR user about successful update
            broadcast_dashboard_update(
                user.id,
                'job_updated',
                {
                    'job_id': job.id,
                    'title': job.title,
                    'changes': changes
                }
            )
            
            # If job status changed to inactive, notify candidates who applied
            if 'is_active' in data and not job.is_active:
                # Find all candidates who applied to this job
                applications = Application.query.filter_by(job_id=job.id).all()
                
                # Get unique user IDs from applications
                applicant_ids = set()
                for app in applications:
                    if app.resume and app.resume.user_id:
                        applicant_ids.add(app.resume.user_id)
                
                # Notify each candidate
                for applicant_id in applicant_ids:
                    broadcast_dashboard_update(
                        applicant_id,
                        'job_status_changed',
                        {
                            'job_id': job.id,
                            'job_title': job.title,
                            'is_active': job.is_active
                        }
                    )
                    
        except Exception as broadcast_error:
            logger.warning(f"Failed to broadcast job update: {broadcast_error}")
        
        return jsonify({
            'success': True,
            'message': 'Job updated successfully',
            'changes': changes,
            'job': job.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in update_job: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred while updating the job'
        }), 500

@jobs_bp.route('/<int:job_id>', methods=['DELETE'])
@require_auth
def delete_job(job_id):
    """
    Delete a job listing with proper cascade handling and notifications.
    Provides option for soft delete instead of hard delete.
    """
    try:
        # Verify user is HR
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({
                'success': False,
                'message': 'Only HR/recruiter users can delete jobs'
            }), 403
        
        # Find the job
        job = Job.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'message': 'Job not found'
            }), 404
        
        # Verify ownership
        if job.created_by != user.id:
            return jsonify({
                'success': False,
                'message': 'You can only delete jobs that you created'
            }), 403
        
        # Get deletion parameters
        soft_delete = request.args.get('soft_delete', 'true').lower() == 'true'
        
        # Check if job has applications
        has_applications = db.session.query(Application.query.filter_by(job_id=job.id).exists()).scalar()
        
        # Store information for notification
        job_title = job.title
        job_company = job.company
        
        if soft_delete or has_applications:
            # Soft delete - just mark as inactive
            job.is_active = False
            job.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Auto-sync update to vector database (soft delete)
            try:
                from services.rag_service import RAGTalentService
                rag_service = RAGTalentService()
                sync_success = rag_service.auto_sync_job(job, 'update')
                if sync_success:
                    logger.info(f"Job {job.id} soft-deleted in vector database")
                else:
                    logger.warning(f"Failed to soft-delete job {job.id} in vector database")
            except Exception as sync_error:
                logger.error(f"Vector database sync error during job soft-delete: {sync_error}")
            
            deletion_type = "deactivated"
        else:
            # Hard delete - remove from database
            
            # Auto-sync deletion to vector database first
            try:
                from services.rag_service import RAGTalentService
                rag_service = RAGTalentService()
                sync_success = rag_service.auto_sync_job(job, 'delete')
                if sync_success:
                    logger.info(f"Job {job.id} removed from vector database")
                else:
                    logger.warning(f"Failed to remove job {job.id} from vector database")
            except Exception as sync_error:
                logger.error(f"Vector database sync error during job deletion: {sync_error}")
            
            # Find all applications for this job
            applications = Application.query.filter_by(job_id=job.id).all()
            
            # Delete all applications first
            for application in applications:
                db.session.delete(application)
            
            # Then delete the job
            db.session.delete(job)
            db.session.commit()
            
            deletion_type = "permanently deleted"
        
        # Notify about deletion
        try:
            from services.realtime_service import broadcast_dashboard_update
            
            # Notify HR user about successful deletion
            broadcast_dashboard_update(
                user.id,
                'job_deleted',
                {
                    'job_id': job_id,
                    'title': job_title,
                    'deletion_type': deletion_type
                }
            )
            
            if soft_delete or has_applications:
                # Find all candidates who applied to this job
                applications = Application.query.filter_by(job_id=job.id).all()
                
                # Get unique user IDs from applications
                applicant_ids = set()
                for app in applications:
                    if app.resume and app.resume.user_id:
                        applicant_ids.add(app.resume.user_id)
                
                # Notify each candidate
                for applicant_id in applicant_ids:
                    broadcast_dashboard_update(
                        applicant_id,
                        'job_removed',
                        {
                            'job_id': job_id,
                            'job_title': job_title,
                            'company': job_company
                        }
                    )
                    
        except Exception as broadcast_error:
            logger.warning(f"Failed to broadcast job deletion: {broadcast_error}")
        
        return jsonify({
            'success': True,
            'message': f'Job {deletion_type} successfully',
            'deletion_type': deletion_type
        }), 200
        
    except Exception as e:
        logger.error(f"Error in delete_job: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred while deleting the job'
        }), 500

@jobs_bp.route('/<int:job_id>/apply', methods=['POST'])
@require_auth
def apply_to_job(job_id):
    """
    Apply to a job with a resume and optional cover letter.
    Automatically calculates match score based on resume skills and job requirements.
    """
    try:
        # Verify user is a candidate
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'candidate':
            return jsonify({
                'success': False,
                'message': 'Only candidates can apply to jobs'
            }, 403)
        
        # Check if job exists and is active
        job = Job.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'message': 'Job not found'
            }), 404
            
        if not job.is_active:
            return jsonify({
                'success': False,
                'message': 'This job is no longer accepting applications'
            }), 400
        
        # Validate application data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No application data provided'
            }), 400
            
        resume_id = data.get('resume_id')
        if not resume_id:
            return jsonify({
                'success': False,
                'message': 'Resume ID is required'
            }), 400
        
        # Get optional cover letter
        cover_letter = data.get('cover_letter', '')
        
        # Verify resume belongs to the user
        resume = Resume.query.filter_by(
            id=resume_id, 
            user_id=user.id
        ).first()
        
        if not resume:
            return jsonify({
                'success': False,
                'message': 'Invalid resume selected'
            }), 404
        
        # Check if user has already applied to this job with this resume
        existing_application = Application.query.filter_by(
            resume_id=resume_id,
            job_id=job_id
        ).first()
        
        if existing_application:
            return jsonify({
                'success': False,
                'message': 'You have already applied to this job with this resume'
            }), 400
        
        # Calculate match score using AI analysis of resume vs job requirements
        match_score = 0.0
        matched_skills = []
        missing_skills = []
        
        if resume.parsed_data and job.requirements:
            try:
                # Parse resume data
                if isinstance(resume.parsed_data, str):
                    parsed_data = json.loads(resume.parsed_data)
                else:
                    parsed_data = resume.parsed_data
                    
                # Extract skills from resume
                user_skills = parsed_data.get('skills', [])
                if not user_skills:
                    # Try alternate locations in parsed data
                    user_skills = parsed_data.get('technical_skills', []) or \
                                  parsed_data.get('skill_set', []) or \
                                  []
                
                # Convert to lowercase for better matching
                user_skills_lower = [skill.lower() for skill in user_skills]
                
                # Extract requirements from job
                job_requirements = job.requirements or []
                job_reqs_lower = [req.lower() for req in job_requirements]
                
                if user_skills and job_requirements:
                    # Advanced skill matching algorithm
                    for req in job_reqs_lower:
                        req_matched = False
                        
                        # Check for exact matches or if skill is part of a compound skill
                        for skill in user_skills_lower:
                            if req in skill or skill in req:
                                matched_skills.append(req)
                                req_matched = True
                                break
                                
                        if not req_matched:
                            missing_skills.append(req)
                    
                    # Calculate score as percentage of matched requirements
                    if job_reqs_lower:
                        match_score = len(matched_skills) / len(job_reqs_lower)
                    
                    # Adjust match score based on experience if available
                    if job.employment_type == 'senior' and parsed_data.get('years_of_experience', 0) < 5:
                        match_score *= 0.8  # Reduce score for senior roles with less experience
                    
                    # Scale to 0-1 range
                    match_score = min(max(match_score, 0), 1)
                    
            except Exception as e:
                logger.error(f"Error calculating match score: {str(e)}", exc_info=True)
        
        # Create application
        application = Application(
            resume_id=resume_id,
            job_id=job_id,
            cover_letter=cover_letter,
            match_score=match_score,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        db.session.add(application)
        db.session.commit()
        
        # Notify both the candidate and the job creator (HR)
        try:
            from services.realtime_service import broadcast_dashboard_update
            
            # Notify candidate
            broadcast_dashboard_update(
                user.id, 
                'application_submitted',
                {
                    'application_id': application.id,
                    'job_title': job.title,
                    'company': job.company,
                    'match_score': match_score,
                    'matched_skills': matched_skills,
                    'missing_skills': missing_skills
                }
            )
            
            # Notify HR
            broadcast_dashboard_update(
                job.created_by, 
                'application_received',
                {
                    'application_id': application.id,
                    'job_title': job.title,
                    'candidate_name': user.name,
                    'match_score': match_score
                }
            )
        except Exception as broadcast_error:
            logger.warning(f"Failed to broadcast application update: {broadcast_error}")
        
        return jsonify({
            'success': True,
            'message': 'Application submitted successfully',
            'application': {
                'id': application.id,
                'job_title': job.title,
                'company': job.company,
                'status': application.status,
                'match_score': match_score,
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'applied_at': application.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error in apply_to_job: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred while submitting your application'
        }), 500

@jobs_bp.route('/applications', methods=['GET'])
@require_auth
def list_user_applications():
    """Get all applications for the current user"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Get applications for resumes owned by the user
        applications_query = db.session.query(Application)\
            .join(Resume, Application.resume_id == Resume.id)\
            .filter(Resume.user_id == request.current_user_id)\
            .order_by(Application.created_at.desc())
        
        applications_paginated = applications_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        application_data = []
        for app in applications_paginated.items:
            app_dict = app.to_dict()
            # Add job and resume details
            if app.job:
                app_dict['job'] = app.job.to_dict()
            if app.resume:
                app_dict['resume'] = app.resume.to_dict()
            application_data.append(app_dict)
        
        return jsonify({
            'applications': application_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': applications_paginated.total,
                'pages': applications_paginated.pages,
                'has_next': applications_paginated.has_next,
                'has_prev': applications_paginated.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('/applications/stats/me', methods=['GET'])
@require_auth
def get_candidate_application_stats():
    """Get application statistics for the current user"""
    try:
        # Get applications for resumes owned by the user
        applications = db.session.query(Application)\
            .join(Resume, Application.resume_id == Resume.id)\
            .filter(Resume.user_id == request.current_user_id)\
            .all()
        
        # Calculate statistics
        total_applications = len(applications)
        status_counts = {}
        match_scores = []
        
        for app in applications:
            # Count by status
            status = app.status or 'pending'
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Collect match scores
            if app.match_score:
                match_scores.append(app.match_score)
        
        # Calculate average match score
        avg_match_score = sum(match_scores) / len(match_scores) if match_scores else 0
        
        # Get recent applications with job details
        recent_applications = db.session.query(Application)\
            .join(Resume, Application.resume_id == Resume.id)\
            .join(Job, Application.job_id == Job.id)\
            .filter(Resume.user_id == request.current_user_id)\
            .order_by(Application.created_at.desc())\
            .limit(5).all()
        
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
        
        return jsonify({
            'total_applications': total_applications,
            'status_counts': status_counts,
            'avg_match_score': round(avg_match_score, 1),
            'recent_applications': recent_app_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('/applications/<int:application_id>/withdraw', methods=['DELETE'])
@require_auth
def withdraw_application(application_id):
    """Withdraw/delete an application"""
    try:
        # Find application that belongs to user's resume
        application = db.session.query(Application)\
            .join(Resume, Application.resume_id == Resume.id)\
            .filter(
                Application.id == application_id,
                Resume.user_id == request.current_user_id
            ).first()
        
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        # Check if application can be withdrawn
        if application.status in ['accepted', 'rejected']:
            return jsonify({'error': 'Cannot withdraw application that has been processed'}), 400
        
        job_title = application.job.title if application.job else 'Unknown'
        
        db.session.delete(application)
        db.session.commit()
        
        # Broadcast real-time update to user
        try:
            from services.realtime_service import broadcast_dashboard_update
            broadcast_dashboard_update(
                request.current_user_id, 
                'application_withdrawn',
                {
                    'application_id': application_id,
                    'job_title': job_title
                }
            )
        except Exception as broadcast_error:
            print(f"Failed to broadcast withdrawal update: {broadcast_error}")
        
        return jsonify({'message': 'Application withdrawn successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('/statistics', methods=['GET'])
def get_job_statistics():
    """Get general job statistics for dashboard"""
    try:
        # Total active jobs
        total_jobs = Job.query.filter_by(is_active=True).count()
        
        # Jobs by category
        categories = db.session.query(Job.category, db.func.count(Job.id))\
            .filter(Job.is_active == True)\
            .group_by(Job.category)\
            .all()
        
        category_stats = [{'category': cat or 'other', 'count': count} for cat, count in categories]
        
        # Jobs by location (top 10)
        locations = db.session.query(Job.location, db.func.count(Job.id))\
            .filter(Job.is_active == True, Job.location.isnot(None))\
            .group_by(Job.location)\
            .order_by(db.func.count(Job.id).desc())\
            .limit(10).all()
        
        location_stats = [{'location': loc, 'count': count} for loc, count in locations]
        
        # Recent jobs (last 10)
        recent_jobs = Job.query.filter_by(is_active=True)\
            .order_by(Job.created_at.desc())\
            .limit(10).all()
        
        return jsonify({
            'total_jobs': total_jobs,
            'category_statistics': category_stats,
            'location_statistics': location_stats,
            'recent_jobs': [job.to_dict() for job in recent_jobs],
            'last_updated': db.session.query(db.func.max(Job.created_at)).scalar().isoformat() if total_jobs > 0 else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('/hr/applications', methods=['GET'])
@require_auth
def list_hr_applications():
    """
    Get all applications for jobs posted by the HR user with
    comprehensive filtering, sorting, and detailed candidate information.
    """
    try:
        # Verify user is HR/recruiter
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({
                'success': False,
                'message': 'Only HR/recruiter users can access applications'
            }), 403
            
        # Get pagination and filter parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Filters
        job_id = request.args.get('job_id')
        status = request.args.get('status')
        search = request.args.get('search')
        min_match_score = request.args.get('min_match_score', type=float)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Sorting
        sort_by = request.args.get('sort_by', 'created_at')  # Options: created_at, match_score, status
        sort_order = request.args.get('sort_order', 'desc')  # Options: asc, desc
        
        # Start with applications for jobs created by this HR user
        query = db.session.query(
            Application, Job, Resume, User
        ).join(
            Job, Application.job_id == Job.id
        ).join(
            Resume, Application.resume_id == Resume.id
        ).join(
            User, Resume.user_id == User.id
        ).filter(
            Job.created_by == user.id
        )
        
        # Apply filters
        if job_id:
            query = query.filter(Application.job_id == job_id)
            
        if status:
            query = query.filter(Application.status == status)
            
        if min_match_score is not None:
            query = query.filter(Application.match_score >= min_match_score)
            
        if date_from:
            try:
                from_date = datetime.fromisoformat(date_from)
                query = query.filter(Application.created_at >= from_date)
            except ValueError:
                pass  # Ignore invalid date format
                
        if date_to:
            try:
                to_date = datetime.fromisoformat(date_to)
                # Add a day to include the entire end date
                to_date = to_date + timedelta(days=1)
                query = query.filter(Application.created_at <= to_date)
            except ValueError:
                pass  # Ignore invalid date format
                
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.name.ilike(search_term),
                    User.email.ilike(search_term),
                    Job.title.ilike(search_term),
                    Resume.filename.ilike(search_term)
                )
            )
        
        # Apply sorting
        if sort_by == 'match_score':
            if sort_order == 'asc':
                query = query.order_by(Application.match_score)
            else:
                query = query.order_by(desc(Application.match_score))
        elif sort_by == 'status':
            if sort_order == 'asc':
                query = query.order_by(Application.status)
            else:
                query = query.order_by(desc(Application.status))
        else:  # Default: created_at
            if sort_order == 'asc':
                query = query.order_by(Application.created_at)
            else:
                query = query.order_by(desc(Application.created_at))
        
        # Paginate results
        paginated_query = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format the application data with detailed information
        application_data = []
        
        for app, job, resume, candidate in paginated_query.items:
            # Extract key skills from resume if available
            key_skills = []
            if resume.parsed_data:
                try:
                    parsed_data = json.loads(resume.parsed_data) if isinstance(resume.parsed_data, str) else resume.parsed_data
                    key_skills = parsed_data.get('skills', [])[:5]  # Get top 5 skills
                except Exception:
                    pass
            
            application_data.append({
                'id': app.id,
                'status': app.status,
                'match_score': app.match_score,
                'applied_at': app.created_at.isoformat() if app.created_at else None,
                'has_cover_letter': bool(app.cover_letter),
                'job': {
                    'id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'employment_type': job.employment_type
                },
                'candidate': {
                    'id': candidate.id,
                    'name': candidate.name,
                    'email': candidate.email,
                    'key_skills': key_skills
                },
                'resume': {
                    'id': resume.id,
                    'filename': resume.filename,
                    'file_url': f"/api/resumes/{resume.id}/download"
                }
            })
        
        # Get filter options for the dropdown menus
        job_options = db.session.query(
            Job.id, Job.title, Job.company
        ).filter(
            Job.created_by == user.id
        ).order_by(
            Job.title
        ).all()
        
        status_options = db.session.query(
            Application.status
        ).distinct().all()
        
        return jsonify({
            'success': True,
            'applications': application_data,
            'filter_options': {
                'jobs': [{'id': j.id, 'title': j.title, 'company': j.company} for j in job_options],
                'statuses': [s[0] for s in status_options if s[0]]
            },
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_query.total,
                'pages': paginated_query.pages,
                'has_next': paginated_query.has_next,
                'has_prev': paginated_query.has_prev
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in list_hr_applications: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Error retrieving applications'
        }), 500

@jobs_bp.route('/applications/all', methods=['GET'])
@require_auth
def get_all_applications():
    """Get all applications across all jobs for HR users, with advanced filtering"""
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'Access denied. HR role required.'}), 403
        
        # Get pagination and filter parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        status = request.args.get('status')
        job_id = request.args.get('job_id', type=int)
        search = request.args.get('search')
        sort_by = request.args.get('sort_by', 'applied_at')
        order = request.args.get('order', 'desc')
        
        # Base query - only applications for jobs created by this HR user
        query = db.session.query(Application).join(Job).filter(Job.created_by == user.id)
        
        # Apply filters
        if status:
            query = query.filter(Application.status == status)
        if job_id:
            query = query.filter(Application.job_id == job_id)
        if search:
            search_term = f"%{search}%"
            query = query.join(Resume).join(User).filter(
                or_(
                    User.github_username.ilike(search_term),
                    User.email.ilike(search_term),
                    Resume.filename.ilike(search_term),
                    Job.title.ilike(search_term),
                    Job.company.ilike(search_term)
                )
            )
        
        # Apply sorting
        if sort_by == 'applied_at':
            if order == 'desc':
                query = query.order_by(desc(Application.created_at))
            else:
                query = query.order_by(Application.created_at)
        elif sort_by == 'status':
            if order == 'desc':
                query = query.order_by(desc(Application.status))
            else:
                query = query.order_by(Application.status)
        elif sort_by == 'job_title':
            if order == 'desc':
                query = query.order_by(desc(Job.title))
            else:
                query = query.order_by(Job.title)
        
        # Paginate results
        applications_paginated = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format application data
        applications_data = []
        for application in applications_paginated.items:
            app_data = {
                'id': application.id,
                'job_id': application.job_id,
                'job_title': application.job.title,
                'job_company': application.job.company,
                'job_location': application.job.location,
                'resume_id': application.resume_id,
                'resume_filename': application.resume.filename if application.resume else None,
                'applicant': {
                    'id': application.resume.user_id if application.resume else None,
                    'name': application.resume.user.name if application.resume and application.resume.user else 'Unknown',
                    'username': application.resume.user.github_username if application.resume and application.resume.user else None,
                    'email': application.resume.user.email if application.resume and application.resume.user else None
                },
                # Add fields that the frontend expects
                'candidate_name': application.resume.user.name if application.resume and application.resume.user else 'Unknown',
                'candidate_email': application.resume.user.email if application.resume and application.resume.user else '',
                'status': application.status,
                'applied_at': application.created_at.isoformat() if application.created_at else None,
                'updated_at': application.updated_at.isoformat() if application.updated_at else None
            }
            applications_data.append(app_data)
        
        # Get summary statistics
        total_applications = query.count()
        status_counts = db.session.query(
            Application.status, 
            func.count(Application.id)
        ).join(Job).filter(
            Job.created_by == user.id
        ).group_by(Application.status).all()
        
        return jsonify({
            'success': True,
            'applications': applications_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': applications_paginated.total,
                'pages': applications_paginated.pages,
                'has_next': applications_paginated.has_next,
                'has_prev': applications_paginated.has_prev
            },
            'summary': {
                'total_applications': total_applications,
                'status_breakdown': {status: count for status, count in status_counts}
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting all applications: {e}")
        return jsonify({'error': 'Failed to get applications'}), 500

@jobs_bp.route('/applications/<int:application_id>', methods=['GET'])
@require_auth
def get_application_details(application_id):
    """Get detailed information about a specific application"""
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'Access denied. HR role required.'}), 403
        
        # Get the application - make sure it's for a job created by this HR user
        application = db.session.query(Application).join(Job).filter(
            Application.id == application_id,
            Job.created_by == user.id
        ).first()
        
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        # Get detailed application data
        application_data = {
            'id': application.id,
            'job_id': application.job_id,
            'job_title': application.job.title,
            'job_company': application.job.company,
            'job_location': application.job.location,
            'job_description': application.job.description,
            'job_requirements': application.job.requirements,
            'resume_id': application.resume_id,
            'resume_filename': application.resume.filename if application.resume else None,
            'status': application.status,
            'cover_letter': application.cover_letter,
            'match_score': application.match_score,
            'applied_at': application.created_at.isoformat() if application.created_at else None,
            'created_at': application.created_at.isoformat() if application.created_at else None,
            'updated_at': application.updated_at.isoformat() if application.updated_at else None,
            'candidate': {
                'id': application.resume.user_id if application.resume else None,
                'name': application.resume.user.name if application.resume and application.resume.user else 'Unknown',
                'email': application.resume.user.email if application.resume and application.resume.user else '',
                'github_username': application.resume.user.github_username if application.resume and application.resume.user else None
            },
            'job': {
                'title': application.job.title,
                'company': application.job.company,
                'location': application.job.location,
                'description': application.job.description
            },
            'resume': {
                'id': application.resume.id if application.resume else None,
                'filename': application.resume.filename if application.resume else None,
                'name': application.resume.name if application.resume else application.resume.user.name if application.resume and application.resume.user else 'Unknown',
                'email': application.resume.email if application.resume else application.resume.user.email if application.resume and application.resume.user else '',
                'phone': application.resume.phone if application.resume else None,
                'skills': application.resume.skills if application.resume else [],
                'experience': application.resume.experience if application.resume else [],
                'education': application.resume.education if application.resume else []
            }
        }
        
        return jsonify({
            'success': True,
            'application': application_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting application details: {e}", exc_info=True)
        return jsonify({'error': 'Failed to get application details'}), 500

# Job Matching Analysis Endpoints
@jobs_bp.route('/applications/<int:application_id>/match-analysis', methods=['GET'])
@require_auth
def get_application_match_analysis(application_id):
    """Get detailed match analysis for a specific application"""
    try:
        # Get the application
        application = Application.query.get(application_id)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        # Check if user owns this application
        user = User.query.get(request.current_user_id)
        if application.resume.user_id != user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Import the job matching service
        from services.job_matching_service import JobMatchingService
        
        # Get resume and job data
        resume_data = application.resume.to_dict()
        job_data = application.job.to_dict()
        
        # Initialize the matching service
        matching_service = JobMatchingService(api_key=current_app.config['GROQ_API_KEY'])
        
        # Perform the analysis
        analysis = matching_service.analyze_job_match(resume_data, job_data)
        
        # Store the analysis in the application record
        application.match_score = analysis.get('overall_match_score', 0) / 100.0
        application.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Add application metadata to the response
        analysis['application_id'] = application.id
        analysis['application_status'] = application.status
        analysis['application_date'] = application.created_at.isoformat()
        analysis['resume_filename'] = application.resume.filename
        
        return jsonify({
            'success': True,
            'analysis': analysis
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting match analysis: {str(e)}")
        return jsonify({'error': 'Failed to generate match analysis'}), 500

@jobs_bp.route('/applications/<int:application_id>/skill-gap-analysis', methods=['GET'])
@require_auth
def get_skill_gap_analysis(application_id):
    """Get detailed skill gap analysis for a specific application"""
    try:
        # Get the application
        application = Application.query.get(application_id)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        # Check if user owns this application
        user = User.query.get(request.current_user_id)
        if application.resume.user_id != user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Import the job matching service
        from services.job_matching_service import JobMatchingService
        
        # Get resume and job data
        resume_data = application.resume.to_dict()
        job_data = application.job.to_dict()
        
        # Initialize the matching service
        matching_service = JobMatchingService(api_key=current_app.config['GROQ_API_KEY'])
        
        # Perform the skill gap analysis
        skill_gap = matching_service.get_skill_gap_analysis(resume_data, job_data)
        
        return jsonify({
            'success': True,
            'skill_gap_analysis': skill_gap,
            'application_id': application.id,
            'job_title': application.job.title,
            'company': application.job.company
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting skill gap analysis: {str(e)}")
        return jsonify({'error': 'Failed to generate skill gap analysis'}), 500

@jobs_bp.route('/<int:job_id>/match-with-resume/<int:resume_id>', methods=['GET'])
@require_auth
def match_job_with_resume(job_id, resume_id):
    """Get match analysis between a specific job and resume (before applying)"""
    try:
        # Get job and resume
        job = Job.query.get(job_id)
        resume = Resume.query.get(resume_id)
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Check if user owns this resume
        user = User.query.get(request.current_user_id)
        if resume.user_id != user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Import the job matching service
        from services.job_matching_service import JobMatchingService
        
        # Get data
        resume_data = resume.to_dict()
        job_data = job.to_dict()
        
        # Initialize the matching service
        matching_service = JobMatchingService(api_key=current_app.config['GROQ_API_KEY'])
        
        # Perform the analysis
        analysis = matching_service.analyze_job_match(resume_data, job_data)
        
        # Add metadata
        analysis['job_id'] = job.id
        analysis['resume_id'] = resume.id
        analysis['preview'] = True  # This is a preview, not an actual application
        
        return jsonify({
            'success': True,
            'analysis': analysis
        }), 200
        
    except Exception as e:
        logger.error(f"Error matching job with resume: {str(e)}")
        return jsonify({'error': 'Failed to generate match analysis'}), 500

@jobs_bp.route('/best-matches/user-resumes', methods=['GET'])
@require_auth
def get_best_job_matches():
    """Get best job matches for all user's resumes"""
    try:
        user = User.query.get(request.current_user_id)
        
        # Get user's resumes
        resumes = Resume.query.filter_by(user_id=user.id).all()
        if not resumes:
            return jsonify({'matches': [], 'message': 'No resumes uploaded yet'}), 200
        
        # Get active jobs
        jobs = Job.query.filter_by(is_active=True).limit(50).all()  # Limit for performance
        if not jobs:
            return jsonify({'matches': [], 'message': 'No active jobs available'}), 200
        
        # Import the job matching service
        from services.job_matching_service import JobMatchingService
        matching_service = JobMatchingService(api_key=current_app.config['GROQ_API_KEY'])
          # Analyze matches for each resume
        all_matches = []
        
        for resume in resumes:
            resume_data = resume.to_dict()
            
            # Analyze against top jobs (limit for performance)
            for job in jobs[:20]:  # Analyze top 20 jobs per resume
                job_data = job.to_dict()
                
                try:
                    analysis = matching_service.analyze_job_match(resume_data, job_data)
                    
                    # Add metadata
                    match_data = {
                        'resume_id': resume.id,
                        'resume_filename': resume.filename,
                        'job_id': job.id,
                        'job_title': job.title,
                        'company': job.company,
                        'location': job.location,
                        'employment_type': job.employment_type,
                        'match_score': analysis.get('overall_match_score', 0),
                        'fit_assessment': analysis.get('fit_assessment', 'Unknown'),
                        'summary': analysis.get('summary', ''),
                        'top_matching_skills': analysis.get('matching_skills', [])[:5],
                        'critical_missing_skills': analysis.get('missing_skills', [])[:3]
                    }
                    
                    # Only include matches above 30%
                    if match_data['match_score'] >= 30:
                        all_matches.append(match_data)
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze match for resume {resume.id} and job {job.id}: {str(e)}")
                    continue
        
        # Sort by match score
        all_matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Group by resume for better organization
        matches_by_resume = {}
        for match in all_matches[:50]:  # Return top 50 matches
            resume_id = match['resume_id']
            if resume_id not in matches_by_resume:
                matches_by_resume[resume_id] = {
                    'resume_id': resume_id,
                    'resume_filename': match['resume_filename'],
                    'matches': []
                }
            matches_by_resume[resume_id]['matches'].append(match)
        
        # Limit matches per resume
        for resume_matches in matches_by_resume.values():
            resume_matches['matches'] = resume_matches['matches'][:10]  # Top 10 per resume
        
        return jsonify({
            'success': True,
            'matches_by_resume': list(matches_by_resume.values()),
            'total_matches': len(all_matches),
            'resumes_analyzed': len(resumes),
            'jobs_analyzed': len(jobs)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting best job matches: {str(e)}")
        return jsonify({'error': 'Failed to analyze job matches'}), 500

@jobs_bp.route('/applications/me/with-analysis', methods=['GET'])
@require_auth
def get_my_applications_with_analysis():
    """Get user's applications with match analysis data"""
    try:
        user = User.query.get(request.current_user_id)
        
        # Get user's applications with related data
        applications = db.session.query(Application)\
            .join(Resume)\
            .join(Job)\
            .filter(Resume.user_id == user.id)\
            .order_by(desc(Application.created_at))\
            .all()
        
        applications_data = []
        
        for app in applications:
            app_data = {
                'id': app.id,
                'status': app.status,
                'created_at': app.created_at.isoformat(),
                'updated_at': app.updated_at.isoformat(),
                'cover_letter': app.cover_letter,
                'match_score': app.match_score * 100 if app.match_score else None,
                'job': {
                    'id': app.job.id,
                    'title': app.job.title,
                    'company': app.job.company,
                    'location': app.job.location,
                    'employment_type': app.job.employment_type,
                    'category': app.job.category,
                    'salary_min': app.job.salary_min,
                    'salary_max': app.job.salary_max
                },
                'resume': {
                    'id': app.resume.id,
                    'filename': app.resume.filename,
                    'name': app.resume.name
                },
                'has_analysis': app.match_score is not None
            }
            
            applications_data.append(app_data)
        
        return jsonify({
            'success': True,
            'applications': applications_data,
            'total': len(applications_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting applications with analysis: {str(e)}")
        return jsonify({'error': 'Failed to load applications'}), 500

@jobs_bp.route('/hr', methods=['GET'])
@require_auth
def get_hr_jobs():
    """Get jobs created by the HR user with pagination and filters"""
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'Access denied. HR role required.'}), 403
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status', 'active')  # active, inactive, all
        date_range = request.args.get('date_range', '30d')  # 7d, 30d, 90d, all
        
        # Base query for jobs created by this HR user
        query = Job.query.filter_by(created_by=user.id)
        
        # Apply status filter
        if status == 'active':
            query = query.filter_by(is_active=True)
        elif status == 'inactive':
            query = query.filter_by(is_active=False)
        # 'all' doesn't add any filter
        
        # Apply date range filter
        if date_range != 'all':
            days_map = {'7d': 7, '30d': 30, '90d': 90}
            days = days_map.get(date_range, 30)
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Job.created_at >= cutoff_date)
        
        # Order by newest first
        query = query.order_by(desc(Job.created_at))
        
        # Paginate
        jobs_pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        jobs_data = []
        for job in jobs_pagination.items:
            # Get application count and recent applications
            applications_count = Application.query.filter_by(job_id=job.id).count()
            pending_count = Application.query.filter_by(job_id=job.id, status='pending').count()
            
            job_dict = job.to_dict()
            job_dict['applications_count'] = applications_count
            job_dict['pending_applications'] = pending_count
            jobs_data.append(job_dict)
        
        return jsonify({
            'success': True,
            'jobs': jobs_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': jobs_pagination.total,
                'pages': jobs_pagination.pages,
                'has_next': jobs_pagination.has_next,
                'has_prev': jobs_pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting HR jobs: {str(e)}")
        return jsonify({'error': 'Failed to load jobs'}), 500

@jobs_bp.route('/hr/metrics', methods=['GET'])
@require_auth
def get_hr_metrics():
    """Get metrics and analytics for HR dashboard"""
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'Access denied. HR role required.'}), 403
        
        time_range = request.args.get('time_range', '30d')  # 7d, 30d, 90d
        
        # Calculate date range
        days_map = {'7d': 7, '30d': 30, '90d': 90}
        days = days_map.get(time_range, 30)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get jobs created by this HR user
        hr_jobs = Job.query.filter_by(created_by=user.id).all()
        hr_job_ids = [job.id for job in hr_jobs]
        
        if not hr_job_ids:
            return jsonify({
                'success': True,
                'metrics': {
                    'total_jobs': 0,
                    'active_jobs': 0,
                    'total_applications': 0,
                    'pending_applications': 0,
                    'average_applications_per_job': 0,
                    'recent_activity': []
                }
            }), 200
        
        # Basic counts
        total_jobs = len(hr_jobs)
        active_jobs = sum(1 for job in hr_jobs if job.is_active)
        
        # Application metrics
        total_applications = Application.query.filter(
            Application.job_id.in_(hr_job_ids)
        ).count()
        
        pending_applications = Application.query.filter(
            Application.job_id.in_(hr_job_ids),
            Application.status == 'pending'
        ).count()
        
        recent_applications = Application.query.filter(
            Application.job_id.in_(hr_job_ids),
            Application.created_at >= cutoff_date
        ).count()
        
        # Calculate averages
        avg_applications = total_applications / total_jobs if total_jobs > 0 else 0
        
        # Get recent activity (last 10 applications)
        recent_activity = db.session.query(Application, Job).join(
            Job, Application.job_id == Job.id
        ).filter(
            Application.job_id.in_(hr_job_ids)
        ).order_by(desc(Application.created_at)).limit(10).all()
        
        activity_data = []
        for app, job in recent_activity:
            activity_data.append({
                'application_id': app.id,
                'job_title': job.title,
                'applicant_name': app.resume.name if app.resume else 'Unknown',
                'status': app.status,
                'applied_at': app.created_at.isoformat()
            })
        
        metrics = {
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'total_applications': total_applications,
            'pending_applications': pending_applications,
            'recent_applications': recent_applications,
            'average_applications_per_job': round(avg_applications, 1),
            'recent_activity': activity_data
        }
        
        return jsonify({
            'success': True,
            'metrics': metrics
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting HR metrics: {str(e)}")
        return jsonify({'error': 'Failed to load metrics'}), 500

@jobs_bp.route('/applications/stats/hr', methods=['GET'])
@require_auth
def get_hr_application_stats():
    """Get application statistics for HR dashboard"""
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'Access denied. HR role required.'}), 403
        
        # Get jobs created by this HR user
        hr_jobs = Job.query.filter_by(created_by=user.id).all()
        hr_job_ids = [job.id for job in hr_jobs]
        
        if not hr_job_ids:
            return jsonify({
                'success': True,
                'stats': {
                    'total': 0,
                    'pending': 0,
                    'reviewed': 0,
                    'shortlisted': 0,
                    'rejected': 0
                }
            }), 200
        
        # Get application counts by status
        stats = db.session.query(
            Application.status,
            func.count(Application.id).label('count')
        ).filter(
            Application.job_id.in_(hr_job_ids)
        ).group_by(Application.status).all()
        
        # Convert to dictionary
        status_counts = {status: count for status, count in stats}
        
        # Ensure all statuses are present
        result_stats = {
            'total': sum(status_counts.values()),
            'pending': status_counts.get('pending', 0),
            'reviewed': status_counts.get('reviewed', 0),
            'shortlisted': status_counts.get('shortlisted', 0),
            'rejected': status_counts.get('rejected', 0)
        }
        
        return jsonify({
            'success': True,
            'stats': result_stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting HR application stats: {str(e)}")
        return jsonify({'error': 'Failed to load application stats'}), 500

@jobs_bp.route('/applications/recent', methods=['GET'])
@require_auth
def get_recent_applications():
    """Get recent applications for HR dashboard"""
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'Access denied. HR role required.'}), 403
        
        limit = request.args.get('limit', 10, type=int)
        
        # Get jobs created by this HR user
        hr_jobs = Job.query.filter_by(created_by=user.id).all()
        hr_job_ids = [job.id for job in hr_jobs]
        
        if not hr_job_ids:
            return jsonify({
                'success': True,
                'applications': []
            }), 200
        
        # Get recent applications
        applications = db.session.query(Application).filter(
            Application.job_id.in_(hr_job_ids)
        ).order_by(desc(Application.created_at)).limit(limit).all()
        
        applications_data = []
        for app in applications:
            app_dict = app.to_dict()
            # Add job details
            if app.job:
                app_dict['job'] = {
                    'id': app.job.id,
                    'title': app.job.title,
                    'company': app.job.company
                }
            # Add resume details
            if app.resume:
                app_dict['resume'] = {
                    'id': app.resume.id,
                    'name': app.resume.name,
                    'email': app.resume.email
                }
            applications_data.append(app_dict)
        
        return jsonify({
            'success': True,
            'applications': applications_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting recent applications: {str(e)}")
        return jsonify({'error': 'Failed to load recent applications'}), 500

@jobs_bp.route('/<int:job_id>/match-analysis', methods=['POST'])
@require_auth  
def analyze_job_matches(job_id):
    """Analyze matches between a job and candidate resumes using AI"""
    
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'HR access required'}), 403
        
        job = Job.query.get_or_404(job_id)
        
        # Check if user owns this job
        if job.created_by != user.id:
            return jsonify({'error': 'You can only analyze matches for your own job postings'}), 403
        
        # Get optional filters
        data = request.get_json() or {}
        min_score = data.get('min_score', 0.5)
        max_results = data.get('max_results', 20)
        
        # Get all candidate resumes or specific resumes if provided
        resume_ids = data.get('resume_ids')
        if resume_ids:
            resumes = Resume.query.filter(Resume.id.in_(resume_ids)).all()
        else:
            resumes = Resume.query.all()
        
        if not resumes:
            return jsonify({
                'success': True,
                'job_id': job_id,
                'matches': [],
                'message': 'No candidate resumes found to analyze'
            })
        
        # Use job matching service
        from services.job_matching_service import JobMatchingService
        matching_service = JobMatchingService()
        
        # Analyze matches
        matches = []
        for resume in resumes:
            try:
                analysis = matching_service.analyze_job_match(
                    resume_data=resume.to_dict(),
                    job_data=job.to_dict()
                )
                
                # Filter by minimum score
                if analysis.get('overall_match_score', 0) >= (min_score * 100):
                    matches.append(analysis)
                    
            except Exception as e:
                logger.error(f"Error analyzing match for resume {resume.id}: {e}")
                continue
        
        # Sort by match score and limit results
        matches.sort(key=lambda x: x.get('overall_match_score', 0), reverse=True)
        matches = matches[:max_results]

        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'job_title': job.title,
            'total_candidates_analyzed': len(resumes),
            'matches_found': len(matches),
            'matches': matches,
            'analysis_criteria': {
                'min_score': min_score,
                'max_results': max_results
            }
        })
        
    except Exception as e:
        logger.error(f"Error in job match analysis: {e}")
        return jsonify({'error': 'Match analysis failed'}), 500

@jobs_bp.route('/<int:job_id>/compare-candidates', methods=['POST'])
@require_auth
def compare_candidates_for_job(job_id):
    """Compare multiple candidate resumes for a specific job"""
    
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'HR access required'}), 403
        
        job = Job.query.get_or_404(job_id)
        
        # Check if user owns this job
        if job.created_by != user.id:
            return jsonify({'error': 'You can only compare candidates for your own job postings'}), 403
        
        data = request.get_json()
        resume_ids = data.get('resume_ids', [])
        
        if len(resume_ids) < 2:
            return jsonify({'error': 'At least 2 resumes required for comparison'}), 400
        
        resumes = Resume.query.filter(Resume.id.in_(resume_ids)).all()
        
        if len(resumes) != len(resume_ids):
            return jsonify({'error': 'Some resumes not found'}), 404
        
        # Use job matching service
        from services.job_matching_service import JobMatchingService
        matching_service = JobMatchingService()
        
        # Get comparison analysis
        resume_data = [resume.to_dict() for resume in resumes]
        comparison_result = matching_service.compare_multiple_resumes(
            resumes=resume_data,
            job_data=job.to_dict()
        )
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'job_title': job.title,
            'comparison': comparison_result
        })
        
    except Exception as e:
        logger.error(f"Error comparing candidates: {e}")
        return jsonify({'error': 'Candidate comparison failed'}), 500

@jobs_bp.route('/<int:job_id>/skills-analysis', methods=['GET'])
@require_auth
def analyze_job_skills_requirements(job_id):
    """Analyze skills requirements for a job and suggest improvements"""
    
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'HR access required'}), 403
        
        job = Job.query.get_or_404(job_id)
        
        # Check if user owns this job
        if job.created_by != user.id:
            return jsonify({'error': 'You can only analyze your own job postings'}), 403
        
        # Use job matching service for skills analysis
        from services.job_matching_service import JobMatchingService
        matching_service = JobMatchingService()
        
        skills_analysis = matching_service.analyze_job_skills_requirements(job.to_dict())
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'job_title': job.title,
            'skills_analysis': skills_analysis
        })
        
    except Exception as e:
        logger.error(f"Error analyzing job skills: {e}")
        return jsonify({'error': 'Skills analysis failed'}), 500

@jobs_bp.route('/market-analysis', methods=['POST'])
@require_auth
def job_market_analysis():
    """Analyze job market trends and salary insights"""
    
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'HR access required'}), 403
        
        data = request.get_json()
        job_title = data.get('job_title', '')
        location = data.get('location', '')
        skills = data.get('skills', [])
        
        if not job_title:
            return jsonify({'error': 'Job title is required'}), 400
        
        # Use job matching service for market analysis
        from services.job_matching_service import JobMatchingService
        matching_service = JobMatchingService()
        
        market_analysis = matching_service.analyze_job_market(
            title=job_title,
            location=location,
            skills=skills
        )
        
        return jsonify({
            'success': True,
            'market_analysis': market_analysis
        })
        
    except Exception as e:
        logger.error(f"Error in market analysis: {e}")
        return jsonify({'error': 'Market analysis failed'}), 500

@jobs_bp.route('/applications/<int:application_id>', methods=['PUT'])
@require_auth
def update_application_status(application_id):
    """Update application status"""
    try:
        user = User.query.get(request.current_user_id)
        if not user or user.role != 'hr':
            return jsonify({'error': 'Access denied. HR role required.'}), 403
        
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        # Validate status
        valid_statuses = ['pending', 'reviewed', 'shortlisted', 'interviewed', 'hired', 'rejected']
        if new_status not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400
        
        # Get the application - make sure it's for a job created by this HR user
        application = db.session.query(Application).join(Job).filter(
            Application.id == application_id,
            Job.created_by == user.id
        ).first()
        
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        # Update status
        application.status = new_status
        application.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Application status updated to {new_status}',
            'application': {
                'id': application.id,
                'status': application.status,
                'updated_at': application.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating application status: {e}", exc_info=True)
        return jsonify({'error': 'Failed to update application status'}), 500
