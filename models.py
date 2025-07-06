from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and profile management"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Now nullable since GitHub users won't have a password
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=True)  # Made nullable to allow role selection after GitHub OAuth
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # GitHub OAuth fields
    github_id = db.Column(db.String(50), unique=True, nullable=True)
    github_username = db.Column(db.String(100), nullable=True)
    github_avatar = db.Column(db.String(255), nullable=True)
    github_access_token = db.Column(db.String(255), nullable=True)
    
    # Relationships
    resumes = db.relationship('Resume', backref='user', lazy=True, cascade='all, delete-orphan')
    created_jobs = db.relationship('Job', backref='creator', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary for JSON response"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'created_at': self.created_at.isoformat(),
            'github_username': self.github_username,
            'github_avatar': self.github_avatar,
            'auth_provider': 'github' if self.github_id else 'local'
        }

class Resume(db.Model):
    """Resume model for storing parsed resume data"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    
    # Parsed data from Mistral AI
    parsed_data = db.Column(db.JSON)  # Store structured JSON data
    raw_text = db.Column(db.Text)     # Store raw OCR text
    
    # Extracted fields
    name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    skills = db.Column(db.JSON)       # Array of skills
    experience = db.Column(db.JSON)   # Array of experience objects
    education = db.Column(db.JSON)    # Array of education objects
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='resume', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert resume to dictionary for JSON response"""
        return {
            'id': self.id,
            'filename': self.filename,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'skills': self.skills,
            'experience': self.experience,
            'education': self.education,
            'parsed_data': self.parsed_data,  # Include the full parsed data
            'raw_text': self.raw_text,        # Include raw text for debugging
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Job(db.Model):
    """Job listing model for HR users"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.JSON)  # Array of requirements
    location = db.Column(db.String(100))
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    employment_type = db.Column(db.String(50))  # full-time, part-time, contract
    category = db.Column(db.String(50), default='other')  # job category
    
    # Job status
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='job', lazy=True, cascade='all, delete-orphan')
    # Remove the creator relationship since it's now defined in User model
    
    def to_dict(self):
        """Convert job to dictionary for JSON response"""
        return {
            'id': self.id,
            'title': self.title,
            'company': self.company,
            'description': self.description,
            'requirements': self.requirements,
            'location': self.location,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'employment_type': self.employment_type,
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Application(db.Model):
    """Job application model linking users to jobs"""
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resume.id', ondelete='CASCADE'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id', ondelete='CASCADE'), nullable=False)
    
    status = db.Column(db.String(50), default='pending')  # pending, reviewing, interview, rejected, accepted
    cover_letter = db.Column(db.Text)
    match_score = db.Column(db.Float)  # AI-calculated match score
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # Resume and job relationships are defined in their respective models with proper cascading
    
    def to_dict(self):
        """Convert application to dictionary for JSON response"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'resume_id': self.resume_id,
            'status': self.status,
            'cover_letter': self.cover_letter,
            'match_score': self.match_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Interview(db.Model):
    """Interview model for scheduling and managing interviews"""
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id', ondelete='CASCADE'), nullable=False)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    # Interview details
    interview_type = db.Column(db.String(50), nullable=False, default='technical')  # technical, hr, final, phone, video
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Scheduling
    scheduled_at = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    location = db.Column(db.String(255), nullable=True)  # Can be room, zoom link, etc.
    meeting_link = db.Column(db.String(500), nullable=True)  # For video interviews
    
    # Status and results
    status = db.Column(db.String(50), nullable=False, default='scheduled')  # scheduled, completed, cancelled, rescheduled
    feedback = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Integer, nullable=True)  # 1-5 rating
    recommendation = db.Column(db.String(50), nullable=True)  # hire, reject, next_round
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    application = db.relationship('Application', backref='interviews', lazy=True)
    interviewer = db.relationship('User', backref='conducted_interviews', lazy=True)
    
    def to_dict(self):
        """Convert interview to dictionary for JSON response"""
        return {
            'id': self.id,
            'application_id': self.application_id,
            'interviewer_id': self.interviewer_id,
            'interviewer_name': self.interviewer.name if self.interviewer else None,
            'interview_type': self.interview_type,
            'title': self.title,
            'description': self.description,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'duration_minutes': self.duration_minutes,
            'location': self.location,
            'meeting_link': self.meeting_link,
            'status': self.status,
            'feedback': self.feedback,
            'rating': self.rating,
            'recommendation': self.recommendation,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            # Include candidate and job info for convenience
            'candidate_name': self.application.resume.name if self.application and self.application.resume else None,
            'candidate_email': self.application.resume.email if self.application and self.application.resume else None,
            'job_title': self.application.job.title if self.application and self.application.job else None,
            'company': self.application.job.company if self.application and self.application.job else None
        }
