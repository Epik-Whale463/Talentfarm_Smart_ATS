#!/bin/bash
# This script creates a temporary Python script inside the container to initialize the database

# Create a temporary script
docker exec ats-application bash -c "cat > /app/setup_db.py << 'EOF'
from app import create_app
from models import db

print('Setting up the database...')
app = create_app()
with app.app_context():
    print('Creating database tables...')
    db.create_all()
    print('Database initialized successfully!')
EOF"

# Run the script
echo "Running database setup..."
docker exec ats-application python /app/setup_db.py

# Remove the temporary script
docker exec ats-application rm /app/setup_db.py

echo "Setup complete!"
