# Project Structure

```
ATS2/
├── app.py                     # Main Flask application entry point
├── config.py                  # Configuration settings
├── models.py                  # Database models (User, Resume, Job, Application)
├── auth.py                    # Authentication routes and middleware
├── resumes.py                 # Resume management routes
├── jobs.py                    # Job listing routes
├── dashboard.py               # Dashboard and page routes
├── mistral_service.py         # Mistral AI integration service
├── requirements.txt           # Python dependencies
├── setup.bat                  # Windows setup script
├── run.bat                    # Windows run script
├── .env.example              # Environment variables template
├── README.md                 # Project documentation
├── labs.ipynb               # Jupyter notebook for testing/development
├── resumes/                 # Sample resume files
│   └── RamaCharan_resume.pdf
├── templates/               # HTML templates
│   ├── base.html           # Base template with navigation
│   ├── index.html          # Landing page
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── candidate_dashboard.html # Candidate dashboard
│   ├── resumes.html        # Resume management page
│   └── jobs.html           # Job listings page
└── static/                 # Static files (CSS, JS)
    ├── css/
    │   └── style.css       # Custom CSS styles
    └── js/
        ├── auth.js         # Authentication JavaScript
        └── main.js         # Main JavaScript utilities
```

## Component Overview

### Backend Components

1. **app.py** - Application factory and main entry point
2. **config.py** - Configuration management with environment variables
3. **models.py** - SQLAlchemy database models
4. **auth.py** - JWT authentication system
5. **resumes.py** - Resume upload and management
6. **jobs.py** - Job listings and applications
7. **dashboard.py** - Web page routing
8. **mistral_service.py** - AI-powered resume parsing

### Frontend Components

1. **templates/** - Jinja2 HTML templates with Bootstrap 5
2. **static/css/style.css** - Custom CSS with responsive design
3. **static/js/auth.js** - Client-side authentication
4. **static/js/main.js** - Utility functions and UI helpers

### Key Features

- **Modular Architecture**: Separated concerns with blueprints
- **AI Integration**: Mistral AI for resume parsing and matching
- **Responsive Design**: Bootstrap 5 with custom CSS
- **Authentication**: JWT-based authentication system
- **File Management**: Secure file upload and processing
- **Database**: SQLAlchemy with SQLite (easily changeable)
- **API Documentation**: RESTful API endpoints

### Security Features

- JWT token authentication
- File type validation
- SQL injection prevention with SQLAlchemy
- CORS protection
- Secure file uploads
- Password hashing with Werkzeug

### Scalability Considerations

- Blueprint-based modular structure
- Configurable database backend
- Environment-based configuration
- Separation of concerns
- API-first design for future mobile apps
