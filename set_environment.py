"""
Utility script to switch between development and production environments
"""
import os
import sys
import argparse
import subprocess

def set_environment():
    """Set the environment variables for development or production"""
    parser = argparse.ArgumentParser(description='Set environment for ATS')
    parser.add_argument('env', choices=['dev', 'prod'], help='Environment to set (dev or prod)')
    args = parser.parse_args()
    
    if args.env == 'dev':
        print("Setting up development environment (SQLite)")
        
        # Set development environment variables
        os.environ['FLASK_ENV'] = 'development'
        
        # Unset production PostgreSQL variables if they exist
        for var in ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_NAME']:
            if var in os.environ:
                del os.environ[var]
        
        print("Environment set to development. The application will use SQLite database.")
        
    elif args.env == 'prod':
        print("Setting up production environment (PostgreSQL)")
        
        # Set production environment variables
        os.environ['FLASK_ENV'] = 'production'
        
        # Check if PostgreSQL environment variables are set
        required_vars = ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_NAME']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            print(f"Missing required PostgreSQL environment variables: {', '.join(missing_vars)}")
            print("Please set these variables in your environment or .env file.")
            print("Example:")
            print("  DB_USER=atsuser")
            print("  DB_PASSWORD=your_secure_password")
            print("  DB_HOST=localhost")
            print("  DB_PORT=5432 (optional, defaults to 5432)")
            print("  DB_NAME=ats")
            sys.exit(1)
        
        print("Environment set to production. The application will use PostgreSQL database.")
        print(f"Database: {os.environ.get('DB_NAME')} at {os.environ.get('DB_HOST')}")
    
    # Return the environment setting for use in scripts
    return args.env

if __name__ == '__main__':
    env = set_environment()
    
    # Optionally run the app after setting the environment
    if len(sys.argv) > 2 and sys.argv[2] == '--run':
        print(f"Starting the application in {env} mode...")
        subprocess.run(["python", "app.py"])
