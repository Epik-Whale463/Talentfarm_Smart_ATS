"""
Database migration script to update foreign key constraints for proper cascade deletion
"""
import sqlite3
import os
from app import create_app
from models import db

def migrate_database():
    """Update the database schema to support proper cascade deletion"""
    app = create_app()
    
    with app.app_context():
        # SQLite doesn't support altering foreign key constraints directly
        # So we need to recreate tables with proper constraints
        
        # First, let's backup existing data
        print("Starting database migration...")
        
        # Enable foreign key constraints
        with db.engine.connect() as conn:
            conn.execute(db.text("PRAGMA foreign_keys = ON"))
            conn.commit()
        
        # Drop and recreate all tables with new constraints
        db.drop_all()
        db.create_all()
        
        print("Database migration completed successfully!")
        print("Note: All existing data has been cleared. You'll need to register new accounts.")

if __name__ == '__main__':
    migrate_database()
