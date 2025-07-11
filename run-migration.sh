#!/bin/bash
# Script to create migrate_db.py in the container and run it

echo "Creating database migration script inside container..."

# Create the migration script inside the container
docker exec ats-application bash -c "cat > /app/migrate_db.py << 'EOF'
\"\"\"
Enhanced database migration script with PostgreSQL support
\"\"\"
import os
import sys
from app import create_app
from models import db
from config import Config

def migrate_database():
    \"\"\"Update the database schema\"\"\"
    app = create_app()
    
    # Get database type from current configuration
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    db_type = 'postgresql' if db_uri.startswith('postgresql') else 'sqlite'
    
    print(f\"\\n{'=' * 60}\")
    print(f\"Database Migration: {db_type.upper()}\")
    print(f\"{'=' * 60}\")
    
    with app.app_context():
        print(\"\\nPre-migration checks...\")
        
        # Database specific operations
        if db_type == 'sqlite':
            print(\"SQLite database detected\")
            try:
                # Enable foreign key constraints for SQLite
                with db.engine.connect() as conn:
                    conn.execute(db.text(\"PRAGMA foreign_keys = ON\"))
                    conn.commit()
                print(\"Foreign key constraints enabled\")
            except Exception as e:
                print(f\"Warning: Could not enable foreign key constraints: {e}\")
        
        elif db_type == 'postgresql':
            print(\"PostgreSQL database detected\")
            try:
                # Test PostgreSQL connection
                with db.engine.connect() as conn:
                    result = conn.execute(db.text(\"SELECT version()\"))
                    version = result.scalar()
                    print(f\"Connected to PostgreSQL: {version}\")
            except Exception as e:
                print(f\"Error: Could not connect to PostgreSQL database: {e}\")
                print(\"\\nPlease check your PostgreSQL configuration:\")
                print(f\"  - Database URI: {db_uri}\")
                sys.exit(1)
        
        print(\"\\nStarting database migration...\")
        
        try:
            # Drop and recreate all tables with new constraints
            print(\"Dropping existing tables...\")
            db.drop_all()
            print(\"Tables dropped successfully\")
            
            print(\"Creating new tables...\")
            db.create_all()
            print(\"Tables created successfully\")
            
            print(\"\\nDatabase migration completed successfully!\")
            
        except Exception as e:
            print(f\"Migration failed: {e}\")
            sys.exit(1)
        
        print(\"\\nNote: All existing data has been cleared. You'll need to register new accounts.\")
        print(f\"{'=' * 60}\\n\")

if __name__ == '__main__':
    # No confirmation prompt in container to allow automated execution
    migrate_database()
EOF"

# Make it executable
docker exec ats-application chmod +x /app/migrate_db.py

# Run the migration script
echo "Running database migration..."
docker exec ats-application python /app/migrate_db.py

echo "Migration completed!"
