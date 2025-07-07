#!/usr/bin/env python3
"""
Database Migration and Update Script
Updates database schema and ensures all features are properly connected
"""

import os
import sys
from flask import Flask
from models import db, User, Resume, Job, Application, Interview
from config import Config
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create Flask app for database operations"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize database
    db.init_app(app)
    
    return app

def backup_database():
    """Create database backup before migration"""
    try:
        import shutil
        from datetime import datetime
        
        db_path = 'ats.db'
        if os.path.exists(db_path):
            backup_name = f"ats_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(db_path, backup_name)
            logger.info(f"✅ Database backed up to: {backup_name}")
            return backup_name
        else:
            logger.info("ℹ️  No existing database found, skipping backup")
            return None
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        return None

def migrate_database():
    """Run database migrations"""
    
    app = create_app()
    
    with app.app_context():
        try:
            logger.info("🔄 Running database migrations...")
            
            # Create all tables
            db.create_all()
            logger.info("✅ Database tables created/updated")
            
            # Check and add any missing columns (for future migrations)
            # This is where you would add ALTER TABLE statements if needed
            
            # Verify all tables exist
            inspector = db.inspect(db.engine)
            table_names = inspector.get_table_names()
            
            expected_tables = ['user', 'resume', 'job', 'application', 'interview']
            missing_tables = [table for table in expected_tables if table not in table_names]
            
            if missing_tables:
                logger.error(f"❌ Missing tables: {missing_tables}")
                return False
            else:
                logger.info("✅ All required tables present")
            
            # Test data integrity
            try:
                # Test basic queries
                user_count = User.query.count()
                resume_count = Resume.query.count()
                job_count = Job.query.count()
                application_count = Application.query.count()
                interview_count = Interview.query.count()
                
                logger.info(f"📊 Current data counts:")
                logger.info(f"   Users: {user_count}")
                logger.info(f"   Resumes: {resume_count}")
                logger.info(f"   Jobs: {job_count}")
                logger.info(f"   Applications: {application_count}")
                logger.info(f"   Interviews: {interview_count}")
                
            except Exception as e:
                logger.error(f"❌ Data integrity check failed: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False

def seed_demo_data():
    """Add demo data if database is empty"""
    
    app = create_app()
    
    with app.app_context():
        try:
            if User.query.count() == 0:
                logger.info("🌱 Seeding demo data...")
                
                # Create demo HR user
                hr_user = User(
                    email='hr@demo.com',
                    name='Demo HR Manager',
                    role='hr'
                )
                hr_user.set_password('demo123')
                db.session.add(hr_user)
                
                # Create demo candidate user
                candidate_user = User(
                    email='candidate@demo.com',
                    name='Demo Candidate',
                    role='candidate'
                )
                candidate_user.set_password('demo123')
                db.session.add(candidate_user)
                
                db.session.commit()
                
                # Create demo job
                demo_job = Job(
                    title='Senior Software Engineer',
                    company='Demo Tech Inc',
                    description='We are looking for a senior software engineer with experience in Python, JavaScript, and cloud technologies.',
                    requirements=['Python', 'JavaScript', 'AWS', 'Docker', 'React'],
                    location='San Francisco, CA',
                    salary_min=120000,
                    salary_max=180000,
                    employment_type='full-time',
                    category='technology',
                    created_by=hr_user.id
                )
                db.session.add(demo_job)
                
                # Create demo resume
                demo_resume = Resume(
                    user_id=candidate_user.id,
                    filename='demo_resume.pdf',
                    file_path='uploads/demo_resume.pdf',
                    name='Demo Candidate',
                    email='candidate@demo.com',
                    phone='+1-555-0123',
                    skills=['Python', 'JavaScript', 'React', 'Node.js', 'MongoDB'],
                    experience=[
                        {
                            'title': 'Software Engineer',
                            'company': 'Tech Startup',
                            'duration': '2021-2023',
                            'description': 'Developed web applications using React and Node.js'
                        }
                    ],
                    education=[
                        {
                            'degree': 'Bachelor of Computer Science',
                            'school': 'University of Technology',
                            'year': '2021'
                        }
                    ]
                )
                db.session.add(demo_resume)
                
                db.session.commit()
                logger.info("✅ Demo data created")
                logger.info("   HR Login: hr@demo.com / demo123")
                logger.info("   Candidate Login: candidate@demo.com / demo123")
                
            else:
                logger.info("ℹ️  Database already contains data, skipping demo data creation")
                
        except Exception as e:
            logger.error(f"❌ Demo data creation failed: {e}")
            db.session.rollback()

def initialize_vector_database():
    """Initialize vector database for RAG features"""
    try:
        logger.info("🔄 Initializing vector database...")
        
        # Try to initialize Qdrant
        from qdrant_client import QdrantClient
        from qdrant_client.http import models
        
        client = QdrantClient(url=Config.QDRANT_URL)
        
        # Create collection if it doesn't exist
        collection_name = "candidate_resumes"
        try:
            collections = client.get_collections()
            collection_exists = any(col.name == collection_name for col in collections.collections)
            
            if not collection_exists:
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=384,  # all-MiniLM-L6-v2 embedding size
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"✅ Created vector collection: {collection_name}")
            else:
                logger.info(f"ℹ️  Vector collection already exists: {collection_name}")
                
        except Exception as e:
            logger.warning(f"⚠️  Vector database initialization warning: {e}")
            logger.info("ℹ️  RAG search features may not work without Qdrant")
            
    except ImportError:
        logger.warning("⚠️  Qdrant client not installed. Install with: pip install qdrant-client")
    except Exception as e:
        logger.warning(f"⚠️  Vector database initialization failed: {e}")

def update_file_permissions():
    """Ensure proper file permissions"""
    try:
        logger.info("🔒 Checking file permissions...")
        
        # Ensure upload directory exists and is writable
        upload_dir = Config.UPLOAD_FOLDER
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            logger.info(f"✅ Created upload directory: {upload_dir}")
        
        # Check if directory is writable
        if os.access(upload_dir, os.W_OK):
            logger.info("✅ Upload directory is writable")
        else:
            logger.error("❌ Upload directory is not writable")
            
    except Exception as e:
        logger.error(f"❌ Permission check failed: {e}")

def main():
    """Run complete migration process"""
    logger.info("🚀 Starting ATS Database Migration...")
    logger.info("=" * 50)
    
    # Step 1: Backup existing database
    backup_file = backup_database()
    
    # Step 2: Run database migrations
    if not migrate_database():
        logger.error("💥 Migration failed! Check logs above.")
        if backup_file:
            logger.info(f"🔄 Restore from backup: {backup_file}")
        sys.exit(1)
    
    # Step 3: Seed demo data if needed
    seed_demo_data()
    
    # Step 4: Initialize vector database
    initialize_vector_database()
    
    # Step 5: Update file permissions
    update_file_permissions()
    
    logger.info("=" * 50)
    logger.info("✅ Migration completed successfully!")
    logger.info("🎯 Next steps:")
    logger.info("   1. Start the application: python app.py")
    logger.info("   2. Run system health check: python system_health_check.py")
    logger.info("   3. Access the application at: http://localhost:5000")

if __name__ == '__main__':
    main()
