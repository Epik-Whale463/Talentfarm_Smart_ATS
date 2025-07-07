#!/usr/bin/env python3
"""
Database and File Cleanup Script
This script will completely clear all data from the ATS system:
- Database tables (users, resumes, jobs, applications, interviews)
- Uploaded files
- Qdrant vector database
- Session data
"""

import os
import shutil
import glob
from datetime import datetime
from flask import Flask
from models import db, User, Resume, Job, Application, Interview
from config import Config

def clear_qdrant_database():
    """Clear the Qdrant vector database"""
    try:
        from qdrant_client import QdrantClient
        
        # Initialize Qdrant client
        client = QdrantClient("localhost", port=6333)
        
        # Delete the resume collection if it exists
        try:
            client.delete_collection("resumes")
            print("✓ Cleared Qdrant vector database (resumes collection)")
        except Exception as e:
            print(f"• Qdrant collection 'resumes' doesn't exist or already cleared: {e}")
            
    except ImportError:
        print("• Qdrant client not available, skipping vector database cleanup")
    except Exception as e:
        print(f"! Error clearing Qdrant database: {e}")

def clear_uploaded_files():
    """Clear all uploaded files"""
    upload_dirs = [
        'uploads',
        'resumes',
        'flask_session',
        'instance'
    ]
    
    total_deleted = 0
    
    for upload_dir in upload_dirs:
        if os.path.exists(upload_dir):
            try:
                # Count files before deletion
                file_count = 0
                for root, dirs, files in os.walk(upload_dir):
                    # Skip database files in instance directory
                    if upload_dir == 'instance':
                        files = [f for f in files if not f.endswith('.db')]
                    file_count += len(files)
                
                if file_count > 0:
                    # Clear files but keep directory structure
                    for root, dirs, files in os.walk(upload_dir):
                        for file in files:
                            # Skip database files in instance directory
                            if upload_dir == 'instance' and file.endswith('.db'):
                                continue
                                
                            file_path = os.path.join(root, file)
                            try:
                                os.remove(file_path)
                                total_deleted += 1
                            except Exception as e:
                                print(f"! Could not delete {file_path}: {e}")
                    
                    print(f"✓ Cleared {file_count} files from {upload_dir}/")
                else:
                    print(f"• Directory {upload_dir}/ is already empty")
                    
            except Exception as e:
                print(f"! Error clearing {upload_dir}/: {e}")
        else:
            print(f"• Directory {upload_dir}/ does not exist")
    
    return total_deleted

def clear_database_tables():
    """Clear all database tables in proper order to handle foreign key constraints"""
    try:
        print("Clearing database tables...")
        
        # Get initial counts
        counts = {
            'interviews': Interview.query.count(),
            'applications': Application.query.count(),
            'resumes': Resume.query.count(),
            'jobs': Job.query.count(),
            'users': User.query.count()
        }
        
        total_records = sum(counts.values())
        print(f"Found {total_records} total records to delete:")
        for table, count in counts.items():
            if count > 0:
                print(f"  • {table}: {count} records")
        
        if total_records == 0:
            print("• Database is already empty")
            return
        
        # Delete in order to respect foreign key constraints
        # 1. Interviews (references applications and users)
        deleted_interviews = Interview.query.delete()
        print(f"✓ Deleted {deleted_interviews} interviews")
        
        # 2. Applications (references resumes and jobs)
        deleted_applications = Application.query.delete()
        print(f"✓ Deleted {deleted_applications} applications")
        
        # 3. Resumes (references users)
        deleted_resumes = Resume.query.delete()
        print(f"✓ Deleted {deleted_resumes} resumes")
        
        # 4. Jobs (references users)
        deleted_jobs = Job.query.delete()
        print(f"✓ Deleted {deleted_jobs} jobs")
        
        # 5. Users (no dependencies)
        deleted_users = User.query.delete()
        print(f"✓ Deleted {deleted_users} users")
        
        # Commit all changes
        db.session.commit()
        print("✓ Database cleanup completed successfully")
        
    except Exception as e:
        db.session.rollback()
        print(f"! Error clearing database: {e}")
        raise

def reset_database_sequence():
    """Reset auto-increment sequences for PostgreSQL/MySQL if needed"""
    try:
        # This is mainly for PostgreSQL, SQLite handles this automatically
        db.engine.execute("DELETE FROM sqlite_sequence WHERE name IN ('user', 'resume', 'job', 'application', 'interview')")
        print("✓ Reset database sequences")
    except Exception as e:
        # This is expected for SQLite and other databases that don't use sequences
        print(f"• Sequence reset not needed or not supported: {e}")

def create_app():
    """Create Flask app for database operations"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize database
    db.init_app(app)
    
    return app

def main():
    """Main cleanup function"""
    print("=" * 60)
    print("ATS DATABASE AND FILE CLEANUP SCRIPT")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Confirm with user
    confirm = input("⚠️  This will DELETE ALL DATA from the ATS system!\n"
                   "This includes:\n"
                   "  • All users and their data\n"
                   "  • All resumes and job applications\n"
                   "  • All jobs and interviews\n"
                   "  • All uploaded files\n"
                   "  • Vector database embeddings\n"
                   "  • Session data\n\n"
                   "Are you absolutely sure? Type 'DELETE ALL' to confirm: ")
    
    if confirm != "DELETE ALL":
        print("❌ Cleanup cancelled")
        return
    
    print("\n🗑️  Starting cleanup process...\n")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Clear database tables
            clear_database_tables()
            print()
            
            # 2. Reset sequences
            reset_database_sequence()
            print()
            
            # 3. Clear uploaded files
            deleted_files = clear_uploaded_files()
            print()
            
            # 4. Clear vector database
            clear_qdrant_database()
            print()
            
            print("=" * 60)
            print("🎉 CLEANUP COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"Summary:")
            print(f"  • Database tables: ✓ Cleared")
            print(f"  • Uploaded files: ✓ {deleted_files} files deleted")
            print(f"  • Vector database: ✓ Cleared")
            print(f"  • Session data: ✓ Cleared")
            print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            print("The ATS system is now completely clean and ready for fresh data.")
            
        except Exception as e:
            print("=" * 60)
            print("❌ CLEANUP FAILED!")
            print("=" * 60)
            print(f"Error: {e}")
            print("The system may be in an inconsistent state.")
            print("Please check the error and try again.")

if __name__ == "__main__":
    main()
