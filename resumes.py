from flask import Blueprint, request, jsonify, current_app, send_file
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from auth import require_auth
from models import db, Resume, User, Application, Job
from mistral_service import MistralOCRService

resumes_bp = Blueprint('resumes', __name__)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@resumes_bp.route('/<int:resume_id>/download', methods=['GET'])
@require_auth
def download_resume(resume_id):
    """Download a resume file - accessible to resume owner or HR with related job application"""
    try:
        user = User.query.get(request.current_user_id)
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
            
        resume = Resume.query.get(resume_id)
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
            
        # Check permissions:
        # 1. User can download their own resume
        # 2. HR can download resume if it's part of an application for a job they posted
        has_permission = False
        
        if resume.user_id == user.id:
            # User can download their own resume
            has_permission = True
        elif user.role == 'hr':
            # Check if resume is part of application for a job posted by this HR
            application_exists = db.session.query(Application).join(Job).filter(
                Application.resume_id == resume_id,
                Job.created_by == user.id
            ).first() is not None
            
            if application_exists:
                has_permission = True
        
        if not has_permission:
            return jsonify({'error': 'You do not have permission to download this resume'}), 403
            
        # Ensure file exists
        if not os.path.isfile(resume.file_path):
            return jsonify({'error': 'Resume file not found on server'}), 404
            
        # Send file for download
        return send_file(
            resume.file_path, 
            as_attachment=True,
            download_name=resume.filename,
            mimetype='application/pdf'  # Assuming PDF, can be enhanced to support multiple types
        )
        
    except Exception as e:
        current_app.logger.error(f"Error downloading resume: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to download resume: {str(e)}'}), 500

@resumes_bp.route('/', methods=['GET'])
@require_auth
def get_all_resumes():
    """Get all resumes for current user (root endpoint)"""
    try:
        resumes = Resume.query.filter_by(user_id=request.current_user_id).all()
        return jsonify({
            'resumes': [resume.to_dict() for resume in resumes]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@resumes_bp.route('/upload', methods=['POST'])
@require_auth
def upload_resume():
    """Upload and parse a new resume"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Use PDF or DOCX files.'}), 400
        
        # Secure filename and save file
        filename = secure_filename(file.filename)
        timestamp = str(int(datetime.now().timestamp()))
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Parse resume using Mistral AI
        mistral_service = MistralOCRService()
        parse_result = mistral_service.parse_resume(file_path)
        
        if not parse_result['success']:
            # Clean up file if parsing failed
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': f'Resume parsing failed: {parse_result["error"]}'}), 500
        
        structured_data = parse_result['structured_data']
        raw_text = parse_result['raw_text']
        
        # Create resume record
        resume = Resume(
            user_id=request.current_user_id,
            filename=filename,
            file_path=file_path,
            parsed_data=structured_data,
            raw_text=raw_text,
            name=structured_data.get('personal_info', {}).get('name'),
            email=structured_data.get('personal_info', {}).get('email'),
            phone=structured_data.get('personal_info', {}).get('phone'),
            skills=structured_data.get('skills', []),
            experience=structured_data.get('experience', []),
            education=structured_data.get('education', [])
        )
        
        db.session.add(resume)
        db.session.commit()
        
        # Broadcast real-time update to user
        try:
            from realtime_service import broadcast_dashboard_update
            broadcast_dashboard_update(
                request.current_user_id, 
                'resume_uploaded',
                {
                    'resume_id': resume.id,
                    'filename': filename,
                    'skills_count': len(structured_data.get('skills', [])),
                    'experience_count': len(structured_data.get('experience', []))
                }
            )
        except Exception as broadcast_error:
            print(f"Failed to broadcast resume upload: {broadcast_error}")
        
        return jsonify({
            'message': 'Resume uploaded and parsed successfully',
            'resume': resume.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        # Clean up file if error occurred
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error': str(e)}), 500

@resumes_bp.route('/list', methods=['GET'])
@require_auth
def list_resumes():
    """Get all resumes for current user"""
    try:
        resumes = Resume.query.filter_by(user_id=request.current_user_id).all()
        return jsonify({
            'resumes': [resume.to_dict() for resume in resumes]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@resumes_bp.route('/<int:resume_id>', methods=['GET'])
@require_auth
def get_resume(resume_id):
    """Get resume by ID"""
    try:
        resume = Resume.query.filter_by(
            id=resume_id, 
            user_id=request.current_user_id
        ).first()
        
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
        
        return jsonify({'resume': resume.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@resumes_bp.route('/<int:resume_id>', methods=['DELETE'])
@require_auth
def delete_resume(resume_id):
    """Delete a resume"""
    try:
        resume = Resume.query.filter_by(
            id=resume_id, 
            user_id=request.current_user_id
        ).first()
        
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Check if this resume is used in any applications
        from models import Application
        applications = Application.query.filter_by(resume_id=resume_id).all()
        
        # Get force parameter from query string
        force_delete = request.args.get('force', 'false').lower() == 'true'
        
        if applications and not force_delete:
            # Return info about applications and let user decide
            return jsonify({
                'error': 'Resume is used in job applications', 
                'applications_count': len(applications),
                'applications': [
                    {
                        'id': app.id,
                        'job_title': app.job.title if app.job else 'Unknown',
                        'company': app.job.company if app.job else 'Unknown',
                        'status': app.status,
                        'applied_at': app.created_at.isoformat() if app.created_at else None
                    } for app in applications
                ],
                'message': 'Add ?force=true to delete resume and all associated applications',
                'can_force_delete': True
            }), 409  # Conflict status code
        
        # If force delete or no applications, proceed with deletion
        if applications and force_delete:
            # Delete all applications first
            for app in applications:
                db.session.delete(app)
        
        # Delete file from filesystem
        if os.path.exists(resume.file_path):
            os.remove(resume.file_path)
        
        db.session.delete(resume)
        db.session.commit()
        
        message = 'Resume deleted successfully'
        if applications and force_delete:
            message += f' (along with {len(applications)} associated applications)'
        
        return jsonify({'message': message}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@resumes_bp.route('/<int:resume_id>/insights', methods=['GET'])
@require_auth
def get_resume_insights(resume_id):
    """Generate comprehensive technical insights for a resume using Groq Llama models"""
    try:
        from resume_insights_service import resume_insights_service
        
        # Get the resume and verify ownership
        resume = Resume.query.get(resume_id)
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
            
        # Verify user owns this resume
        if resume.user_id != request.current_user_id:
            return jsonify({'error': 'You do not have permission to access this resume'}), 403
            
        # Check if resume has been parsed
        if not resume.parsed_data and not resume.raw_text:
            return jsonify({'error': 'Resume has not been processed yet. Please wait for parsing to complete.'}), 400
        
        # Generate insights using the service
        result = resume_insights_service.generate_insights(resume.to_dict())
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate insights')
            }), 500
        
        return jsonify({
            'success': True,
            'resume_id': resume_id,
            'insights': result['insights']
        }), 200
        
    except ImportError:
        current_app.logger.error("Resume insights service not available - missing dependencies")
        return jsonify({
            'success': False,
            'error': 'Resume insights feature is not available. Please contact support.'
        }), 503
        
    except Exception as e:
        current_app.logger.error(f"Error generating resume insights: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to generate insights. Please try again later.'
        }), 500

@resumes_bp.route('/<int:resume_id>/skill-recommendations', methods=['GET'])
@require_auth
def get_skill_recommendations(resume_id):
    """Get skill recommendations for a resume"""
    try:
        from resume_insights_service import resume_insights_service
        
        # Get the resume and verify ownership
        resume = Resume.query.get(resume_id)
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
            
        # Verify user owns this resume
        if resume.user_id != request.current_user_id:
            return jsonify({'error': 'You do not have permission to access this resume'}), 403
        
        # Get optional target role from query params
        target_role = request.args.get('target_role')
        
        # Get current skills from resume
        current_skills = resume.skills or []
        
        # Generate skill recommendations
        result = resume_insights_service.get_skill_recommendations(current_skills, target_role)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate skill recommendations')
            }), 500
        
        return jsonify({
            'success': True,
            'resume_id': resume_id,
            'target_role': target_role,
            'recommendations': result['recommendations']
        }), 200
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Skill recommendations feature is not available. Please contact support.'
        }), 503
        
    except Exception as e:
        current_app.logger.error(f"Error generating skill recommendations: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to generate skill recommendations. Please try again later.'
        }), 500

@resumes_bp.route('/<int:resume_id>/job-comparison', methods=['POST'])
@require_auth
def compare_resume_with_job(resume_id):
    """Compare resume against specific job requirements"""
    try:
        from resume_insights_service import resume_insights_service
        
        # Get the resume and verify ownership
        resume = Resume.query.get(resume_id)
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
            
        # Verify user owns this resume
        if resume.user_id != request.current_user_id:
            return jsonify({'error': 'You do not have permission to access this resume'}), 403
        
        # Get job requirements from request body
        data = request.json
        if not data or 'job_requirements' not in data:
            return jsonify({'error': 'Job requirements are required'}), 400
        
        job_requirements = data['job_requirements']
        if not isinstance(job_requirements, list):
            return jsonify({'error': 'Job requirements must be a list'}), 400
        
        # Generate comparison analysis
        result = resume_insights_service.compare_with_job_requirements(
            resume.to_dict(), 
            job_requirements
        )
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate job comparison')
            }), 500
        
        return jsonify({
            'success': True,
            'resume_id': resume_id,
            'job_requirements': job_requirements,
            'comparison': result['comparison']
        }), 200
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Job comparison feature is not available. Please contact support.'
        }), 503
        
    except Exception as e:
        current_app.logger.error(f"Error generating job comparison: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to generate job comparison. Please try again later.'
        }), 500
