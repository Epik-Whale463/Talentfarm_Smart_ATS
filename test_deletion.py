"""
Test script to verify account deletion functionality
"""
from app import create_app
from models import db, User, Resume, Job, Application
import requests
import json

def test_account_deletion():
    app = create_app()
    
    with app.app_context():
        # Create a test user
        test_user = User(
            email='test@example.com',
            name='Test User',
            role='candidate'
        )
        test_user.set_password('testpassword')
        
        db.session.add(test_user)
        db.session.commit()
        
        print(f"Created test user with ID: {test_user.id}")
        
        # Verify user exists
        user_count_before = User.query.count()
        print(f"Total users before deletion: {user_count_before}")
        
        # Create a test resume for the user
        test_resume = Resume(
            user_id=test_user.id,
            filename='test_resume.pdf',
            file_path='/uploads/test_resume.pdf',
            name='Test User',
            email='test@example.com'
        )
        
        db.session.add(test_resume)
        db.session.commit()
        
        print(f"Created test resume with ID: {test_resume.id}")
        
        # Now manually test the deletion logic
        try:
            # Delete applications for user's resumes
            user_resume_ids = [r.id for r in Resume.query.filter_by(user_id=test_user.id).all()]
            user_job_ids = [j.id for j in Job.query.filter_by(created_by=test_user.id).all()]
            
            print(f"User resume IDs: {user_resume_ids}")
            print(f"User job IDs: {user_job_ids}")
            
            # Delete applications for user's resumes
            if user_resume_ids:
                deleted_apps = Application.query.filter(Application.resume_id.in_(user_resume_ids)).delete(synchronize_session=False)
                print(f"Deleted {deleted_apps} applications for user's resumes")
            
            # Delete applications for user's jobs
            if user_job_ids:
                deleted_job_apps = Application.query.filter(Application.job_id.in_(user_job_ids)).delete(synchronize_session=False)
                print(f"Deleted {deleted_job_apps} applications for user's jobs")
            
            # Delete user's jobs
            deleted_jobs = Job.query.filter_by(created_by=test_user.id).delete(synchronize_session=False)
            print(f"Deleted {deleted_jobs} jobs created by user")
            
            # Delete user's resumes
            deleted_resumes = Resume.query.filter_by(user_id=test_user.id).delete(synchronize_session=False)
            print(f"Deleted {deleted_resumes} resumes for user")
            
            # Finally delete the user
            db.session.delete(test_user)
            db.session.commit()
            
            print("User deletion committed successfully")
            
            # Verify user is deleted
            user_count_after = User.query.count()
            print(f"Total users after deletion: {user_count_after}")
            
            # Try to find the deleted user
            deleted_user = User.query.get(test_user.id)
            if deleted_user is None:
                print("✅ SUCCESS: User account was completely deleted!")
            else:
                print("❌ FAILURE: User account still exists!")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERROR during deletion: {e}")

if __name__ == '__main__':
    test_account_deletion()
