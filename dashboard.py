from flask import Blueprint, render_template, redirect, url_for, request
from auth import require_auth

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@dashboard_bp.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')

@dashboard_bp.route('/register')
def register_page():
    """Registration page"""
    return render_template('register.html')

@dashboard_bp.route('/select-role')
def select_role_page():
    """Role selection page after GitHub OAuth login"""
    return render_template('role_selection.html')

@dashboard_bp.route('/dashboard')
def dashboard():
    """Main dashboard - redirects based on user role"""
    # This will render dashboard.html which contains JavaScript 
    # to check the user's role and redirect to the appropriate dashboard
    return render_template('dashboard.html')

@dashboard_bp.route('/candidate')
def candidate_dashboard():
    """Candidate dashboard"""
    return render_template('candidate_dashboard.html')

@dashboard_bp.route('/hr')
def hr_dashboard():
    """HR dashboard"""
    return render_template('hr_dashboard.html')

@dashboard_bp.route('/resumes')
def resumes_page():
    """Resume management page"""
    return render_template('resumes.html')

@dashboard_bp.route('/jobs')
def jobs_page():
    """Job listings page"""
    return render_template('jobs.html')

@dashboard_bp.route('/jobs/<int:job_id>')
def job_details_page(job_id):
    """Job details page for individual job"""
    return render_template('job_details.html', job_id=job_id)

@dashboard_bp.route('/profile')
def profile_page():
    """User profile page"""
    return render_template('profile.html')
