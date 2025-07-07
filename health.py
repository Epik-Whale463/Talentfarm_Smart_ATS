from flask import Blueprint, jsonify
from models import db, User, Resume, Job, Application
from config import Config
import os
import requests
from datetime import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/system', methods=['GET'])
def get_system_health():
    """Get comprehensive system health status"""
    try:
        health_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'HEALTHY',
            'status_percentage': 100,
            'components': {},
            'warnings': [],
            'errors': []
        }
        
        # Database connectivity check
        try:
            db.session.execute('SELECT 1')
            health_data['components']['database'] = {
                'status': 'HEALTHY',
                'message': 'Database connection successful'
            }
        except Exception as e:
            health_data['components']['database'] = {
                'status': 'CRITICAL',
                'message': f'Database connection failed: {str(e)}'
            }
            health_data['errors'].append('Database connectivity issue')
            health_data['overall_status'] = 'CRITICAL'
        
        # Data presence checks
        try:
            total_users = User.query.count()
            total_resumes = Resume.query.count()
            total_jobs = Job.query.count()
            total_applications = Application.query.count()
            
            health_data['components']['data'] = {
                'status': 'HEALTHY',
                'users': total_users,
                'resumes': total_resumes,
                'jobs': total_jobs,
                'applications': total_applications
            }
            
            if total_users == 0:
                health_data['warnings'].append('No users found in the system')
            if total_jobs == 0:
                health_data['warnings'].append('No jobs posted yet')
            if total_resumes == 0:
                health_data['warnings'].append('No resumes uploaded yet')
                
        except Exception as e:
            health_data['components']['data'] = {
                'status': 'WARNING',
                'message': f'Data check failed: {str(e)}'
            }
            health_data['warnings'].append('Unable to verify data integrity')
        
        # Configuration checks
        config_status = 'HEALTHY'
        config_issues = []
        
        # Check critical configuration
        if not Config.SECRET_KEY or Config.SECRET_KEY.startswith('dev-'):
            config_issues.append('Insecure SECRET_KEY detected')
            config_status = 'WARNING'
        
        if not Config.MISTRAL_API_KEY or Config.MISTRAL_API_KEY.startswith('your-'):
            config_issues.append('Mistral AI API key not configured')
            config_status = 'WARNING'
        
        if not Config.GROQ_API_KEY or Config.GROQ_API_KEY.startswith('your-'):
            config_issues.append('Groq API key not configured')
            config_status = 'WARNING'
        
        health_data['components']['configuration'] = {
            'status': config_status,
            'issues': config_issues
        }
        
        if config_issues:
            health_data['warnings'].extend(config_issues)
        
        # Vector database check
        try:
            # Try to connect to Qdrant
            if hasattr(Config, 'QDRANT_URL'):
                import requests
                response = requests.get(f"{Config.QDRANT_URL}/health", timeout=5)
                if response.status_code == 200:
                    health_data['components']['vector_db'] = {
                        'status': 'HEALTHY',
                        'message': 'Qdrant vector database is accessible'
                    }
                else:
                    health_data['components']['vector_db'] = {
                        'status': 'WARNING',
                        'message': 'Qdrant responded but may have issues'
                    }
                    health_data['warnings'].append('Vector database connectivity issues')
            else:
                health_data['components']['vector_db'] = {
                    'status': 'SKIP',
                    'message': 'Vector database not configured'
                }
        except Exception as e:
            health_data['components']['vector_db'] = {
                'status': 'WARNING',
                'message': f'Vector database check failed: {str(e)}'
            }
            health_data['warnings'].append('Vector database unavailable')
        
        # File system checks
        try:
            upload_dir = Config.UPLOAD_FOLDER
            if os.path.exists(upload_dir) and os.access(upload_dir, os.W_OK):
                health_data['components']['filesystem'] = {
                    'status': 'HEALTHY',
                    'message': 'Upload directory is accessible and writable'
                }
            else:
                health_data['components']['filesystem'] = {
                    'status': 'WARNING',
                    'message': 'Upload directory has permission issues'
                }
                health_data['warnings'].append('File upload may not work properly')
        except Exception as e:
            health_data['components']['filesystem'] = {
                'status': 'WARNING',
                'message': f'Filesystem check failed: {str(e)}'
            }
        
        # Calculate overall status and percentage
        component_statuses = [comp['status'] for comp in health_data['components'].values()]
        
        if 'CRITICAL' in component_statuses:
            health_data['overall_status'] = 'CRITICAL'
            health_data['status_percentage'] = 30
        elif 'WARNING' in component_statuses or health_data['warnings']:
            health_data['overall_status'] = 'WARNING'
            health_data['status_percentage'] = 75
        else:
            health_data['overall_status'] = 'HEALTHY'
            health_data['status_percentage'] = 100
        
        # Add summary
        health_data['summary'] = {
            'total_components': len(health_data['components']),
            'healthy_components': len([s for s in component_statuses if s == 'HEALTHY']),
            'warning_components': len([s for s in component_statuses if s == 'WARNING']),
            'critical_components': len([s for s in component_statuses if s == 'CRITICAL']),
            'total_warnings': len(health_data['warnings']),
            'total_errors': len(health_data['errors'])
        }
        
        return jsonify({
            'success': True,
            'health': health_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Health check failed: {str(e)}',
            'health': {
                'overall_status': 'CRITICAL',
                'status_percentage': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 500

@health_bp.route('/quick', methods=['GET'])
def get_quick_health():
    """Get quick health status for dashboard"""
    try:
        # Quick database check
        db.session.execute('SELECT 1')
        
        # Quick data count
        user_count = User.query.count()
        job_count = Job.query.count()
        resume_count = Resume.query.count()
        
        # Determine status based on basic checks
        if user_count > 0 and job_count > 0:
            status = 'OPERATIONAL'
            percentage = 98
        elif user_count > 0:
            status = 'PARTIAL'
            percentage = 75
        else:
            status = 'STARTING'
            percentage = 50
        
        return jsonify({
            'success': True,
            'status': status,
            'percentage': percentage,
            'counts': {
                'users': user_count,
                'jobs': job_count,
                'resumes': resume_count
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'ERROR',
            'percentage': 25,
            'error': str(e)
        }), 500
