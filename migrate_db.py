"""
Enhanced database migration script with PostgreSQL support
"""
import os
import sys
from app import create_app
from models import db
from config import Config
import time

def migrate_database():
    """Update the database schema with proper production/development handling"""
    app = create_app()
    
    # Get database type from current configuration
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    db_type = 'postgresql' if db_uri.startswith('postgresql') else 'sqlite'
    
    print(f"\n{'=' * 60}")
    print(f"Database Migration: {db_type.upper()}")
    print(f"{'=' * 60}")
    
    # Check if we're in production mode
    in_production = app.config.get('ENV') == 'production'
    
    # If in production, add additional confirmation
    if in_production:
        print("\n⚠️  WARNING: You are about to migrate a PRODUCTION database!")
        print("This will drop and recreate all tables, and ALL DATA WILL BE LOST.")
        confirm = input("\nAre you sure you want to continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Migration canceled.")
            sys.exit(0)
    
    with app.app_context():
        print("\n📋 Pre-migration checks...")
        
        # Database specific operations
        if db_type == 'sqlite':
            print("✅ SQLite database detected")
            try:
                # Enable foreign key constraints for SQLite
                with db.engine.connect() as conn:
                    conn.execute(db.text("PRAGMA foreign_keys = ON"))
                    conn.commit()
                print("✅ Foreign key constraints enabled")
            except Exception as e:
                print(f"⚠️  Warning: Could not enable foreign key constraints: {e}")
        
        elif db_type == 'postgresql':
            print("✅ PostgreSQL database detected")
            try:
                # Test PostgreSQL connection
                with db.engine.connect() as conn:
                    result = conn.execute(db.text("SELECT version()"))
                    version = result.scalar()
                    print(f"✅ Connected to PostgreSQL: {version}")
            except Exception as e:
                print(f"❌ Error: Could not connect to PostgreSQL database: {e}")
                print("\nPlease check your PostgreSQL configuration:")
                print(f"  - Database URI: {db_uri}")
                sys.exit(1)
        
        print("\n🔄 Starting database migration...")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        try:
            # Drop and recreate all tables with new constraints
            print("⏳ Dropping existing tables...")
            db.drop_all()
            print("✅ Tables dropped successfully")
            
            print("⏳ Creating new tables...")
            db.create_all()
            print("✅ Tables created successfully")
            
            print("\n✅ Database migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            sys.exit(1)
        
        print("\n⚠️  Note: All existing data has been cleared. You'll need to register new accounts.")
        print(f"{'=' * 60}\n")

if __name__ == '__main__':
    migrate_database()
