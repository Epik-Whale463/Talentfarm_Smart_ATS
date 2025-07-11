# 🚀 AI-Powered Applicant Tracking System (ATS)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![AI](https://img.shields.io/badge/AI-Mistral%20%26%20Groq-purple.svg)](https://mistral.ai)

A cutting-edge, enterprise-grade Applicant Tracking System that revolutionizes the hiring process through artificial intelligence. Built with modern web technologies and advanced AI capabilities, this platform delivers intelligent resume parsing, sophisticated job matching algorithms, and comprehensive hiring workflow management.

## 🌟 Key Features

### 🤖 Advanced AI Capabilities
- **Intelligent Resume Parsing**: Extract structured data from PDF/DOCX resumes with 95% accuracy using Mistral AI
- **Smart Job Matching**: AI-powered algorithms analyze skill compatibility, experience relevance, and cultural fit
- **Skill Gap Analysis**: Detailed assessment of candidate strengths and areas for improvement
- **Resume Insights**: AI-generated recommendations for resume optimization and career development
- **Natural Language Processing**: Advanced text analysis for job descriptions and resume content

### 👥 Dual-Role Dashboard System
- **Candidate Portal**: Personalized dashboard with application tracking, interview scheduling, and career insights
- **HR Management Panel**: Comprehensive recruitment tools with application management and analytics
- **Real-time Notifications**: Live updates using WebSocket technology for instant communication
- **Responsive Design**: Modern glassmorphic UI with mobile-first approach

### 🔐 Enterprise Security
- **JWT Authentication**: Secure token-based authentication system
- **Role-Based Access Control**: Granular permissions for different user types
- **OAuth Integration**: GitHub OAuth support for seamless third-party authentication
- **Data Protection**: Comprehensive input validation and XSS prevention

### 📊 Analytics & Reporting
- **Match Score Analytics**: Detailed compatibility scoring between candidates and positions
- **Application Tracking**: Complete audit trail of application status changes
- **Performance Metrics**: Dashboard analytics with key hiring metrics
- **Export Capabilities**: Generate comprehensive reports for stakeholder review

## 🛠 Technology Stack

### Backend Architecture
- **Flask 2.3.3**: Robust Python web framework with modular blueprint design
- **SQLAlchemy 3.0.5**: Advanced ORM with relationship management and database abstraction
- **Flask-SocketIO 5.3.6**: Real-time bidirectional communication
- **PyJWT 2.8.0**: Secure JSON Web Token implementation
- **Werkzeug 2.3.7**: WSGI utility library with security features

### AI & Machine Learning
- **Mistral AI 1.8.2**: State-of-the-art language model for resume parsing and analysis
- **LangChain 0.2.0+**: Advanced AI application framework for complex reasoning
- **Groq 0.8.0+**: High-performance AI inference for real-time processing
- **Custom Algorithms**: Proprietary matching algorithms with skill compatibility scoring

### Frontend Technologies
- **HTML5**: Semantic markup with accessibility compliance (WCAG 2.1 AA)
- **Bootstrap 5**: Responsive framework with custom glassmorphic design system
- **Vanilla JavaScript (ES6+)**: Modern client-side functionality without heavy dependencies
- **CSS3**: Advanced styling with animations, gradients, and backdrop filters
- **Socket.IO Client**: Real-time frontend integration

### Database & Storage
- **SQLite**: Default lightweight database (for development)
- **PostgreSQL**: Production-ready database with scalability and performance
- **Docker Integration**: Containerized PostgreSQL setup for easy deployment
- **File Storage**: Secure document upload and management system
- **Session Management**: Flask-Session with configurable backends

### DevOps & Deployment
- **Docker Ready**: Containerization support for consistent deployments
- **Environment Configuration**: Flexible configuration management with .env support
- **Logging**: Comprehensive application logging and error tracking
- **Performance Monitoring**: Built-in metrics and health checks

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.8 or higher
- Git
- A modern web browser
- (Optional) Docker for Qdrant vector database

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd ATS2

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys:
# - MISTRAL_API_KEY: Get from https://console.mistral.ai/
# - GROQ_API_KEY: Get from https://console.groq.com/
# - SECRET_KEY: Generate a secure random string
# - JWT_SECRET_KEY: Generate another secure random string
```

### 3. Database Setup

#### Development (SQLite)
```bash
# Set environment to development
python set_environment.py dev

# Run migration for SQLite
python migrate_db.py
```

#### Production (PostgreSQL)
```bash
# See detailed PostgreSQL setup instructions
cat POSTGRESQL_SETUP.md

# Set environment to production (after setting PostgreSQL environment variables)
python set_environment.py prod

# Run migration for PostgreSQL
python migrate_db.py
```

This will:
- Create the appropriate database schema
- Set up tables and relationships
- Initialize the application with a clean database

### 4. System Health Check

```bash
# Verify all components are working
python system_health_check.py

# This validates:
# - Configuration
# - Database connectivity
# - AI service access
# - File system permissions
# - API endpoints
# - Frontend integration
```

### 5. Start the Application

```bash
# Start the development server
python app.py

# Application will be available at:
# http://localhost:5000
```

### 6. Demo Login Credentials

```
HR Manager:
Email: hr@demo.com
Password: demo123

Candidate:
Email: candidate@demo.com
Password: demo123
```

## 🔧 Advanced Setup

### Vector Database (Qdrant) Setup

For enhanced RAG search capabilities:

```bash
# Option 1: Docker (Recommended)
docker run -p 6333:6333 qdrant/qdrant

# Option 2: Local installation
# Follow instructions at: https://qdrant.tech/documentation/quick-start/
```

### Production Configuration

For production deployment, configure your environment variables:

```bash
# Update .env.production for production deployment
FLASK_ENV=production
SECRET_KEY=your-secure-production-key

# PostgreSQL Database Configuration
DB_USER=atsuser
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ats

# Vector Database Configuration
QDRANT_URL=http://your-qdrant-server:6333
QDRANT_API_KEY=your-qdrant-api-key

# See POSTGRESQL_SETUP.md for detailed PostgreSQL setup instructions
```

### Docker Deployment

The application includes scripts for Docker deployment to both Docker Hub and AWS:

```bash
# Windows PowerShell
.\docker-deploy.ps1 build   # Build the Docker image
.\docker-deploy.ps1 run     # Build and run with docker-compose
.\docker-deploy.ps1 push    # Build and push to Docker Hub
.\docker-deploy.ps1 aws     # Build and push to AWS ECR
.\docker-deploy.ps1 all     # Do all steps

# Windows CMD
docker-deploy.bat build     # Build the Docker image
docker-deploy.bat run       # Build and run with docker-compose
docker-deploy.bat push      # Build and push to Docker Hub
docker-deploy.bat aws       # Build and push to AWS ECR
docker-deploy.bat all       # Do all steps

# Linux/Mac
chmod +x docker-deploy.sh   # Make script executable
./docker-deploy.sh build    # Build the Docker image
./docker-deploy.sh run      # Build and run with docker-compose
./docker-deploy.sh push     # Build and push to Docker Hub
./docker-deploy.sh aws      # Build and push to AWS ECR
./docker-deploy.sh all      # Do all steps
```

For detailed instructions on PostgreSQL setup, Docker deployment, and AWS deployment:

```bash
# View PostgreSQL and deployment guide
cat POSTGRESQL_SETUP.md
```

## 🎯 Core Features Deep Dive

### 1. Resume Parsing & Analysis

**Intelligent Document Processing:**
- Supports PDF and DOCX formats
- Extracts personal information, skills, experience, education
- AI-powered skill categorization
- Experience validation and parsing
- Contact information extraction

**Resume Insights:**
- Technical skill assessment
- Career progression analysis
- Skill gap identification
- Industry trend alignment
- Improvement recommendations

```python
# Example: Get resume insights
await fetch('/api/resumes/1/insights', {
    headers: { 'Authorization': `Bearer ${token}` }
});
```

### 2. Advanced Talent Search

**Multi-Service Search:**
- Standard keyword-based search
- RAG-enhanced semantic search
- Service comparison capabilities
- Advanced filters and criteria

**Search Methods:**
- Natural language queries
- Structured field searches
- Skill-based matching
- Experience level filtering
- Location and remote work preferences

```python
# Example: Advanced search
await fetch('/api/talent-search/rag-search', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({
        query: "Find Python developers with 3+ years experience",
        filters: { experience_level: "senior", location: "remote" }
    })
});
```

### 3. Job Matching & Analysis

**AI-Powered Matching:**
- Compatibility scoring algorithm
- Skill requirement analysis
- Experience relevance assessment
- Cultural fit evaluation

**Matching Features:**
- Job-candidate compatibility analysis
- Multiple candidate comparison
- Skills gap identification
- Market analysis and trends

```python
# Example: Analyze job matches
await fetch('/api/jobs/1/match-analysis', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ min_score: 0.7, max_results: 10 })
});
```

### 4. Real-time Updates

**WebSocket Integration:**
- Instant application status updates
- Interview notifications
- New job alerts
- Dashboard statistics updates

**Event Types:**
- `application_status_update`
- `interview_scheduled`
- `new_job_posted`
- `resume_analysis_complete`
- `talent_search_update`

## 📁 Project Structure

```
ATS2/
├── 🐍 app.py                    # Main Flask application
├── 🗄️ models.py                 # Database models and schema
├── ⚙️ config.py                 # Configuration management
├── 🔐 auth.py                   # Authentication & OAuth
├── 📄 resumes.py                # Resume management
├── 💼 jobs.py                   # Job posting management
├── 🎤 interviews.py             # Interview scheduling
├── 🎛️ dashboard.py              # Route handlers
├── 🔍 talent_search_service.py  # Main talent search
├── 🔍 rag_talent_search.py      # RAG-enhanced search
├── 📊 job_matching_service.py   # Job matching algorithms
├── 🧠 resume_insights_service.py # Resume analysis
├── ⚡ realtime_service.py       # WebSocket real-time updates
├── 🤖 mistral_service.py        # Mistral AI integration
├── 🗄️ rag_service.py            # RAG service core
├── 🔄 vector_sync_listeners.py  # Auto-sync to vector DB
├── 🚀 migrate_and_setup.py      # Database migration
├── 🏥 system_health_check.py    # System diagnostics
├── 📋 requirements.txt          # Dependencies
├── 🌍 .env.example             # Environment template
├── static/                     # Frontend assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── main.js
│       └── auth.js
├── templates/                  # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── hr_dashboard.html
│   ├── candidate_dashboard.html
│   ├── jobs.html
│   ├── resumes.html
│   ├── login.html
│   └── register.html
├── uploads/                   # File storage
└── instance/                  # Instance-specific files
```

## 🔧 API Reference

### Authentication Endpoints
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/github/login` - GitHub OAuth
- `POST /api/auth/logout` - User logout

### Resume Management
- `GET /api/resumes/` - List user resumes
- `POST /api/resumes/upload` - Upload new resume
- `GET /api/resumes/{id}/insights` - Get AI insights
- `GET /api/resumes/{id}/skill-recommendations` - Get skill recommendations
- `POST /api/resumes/{id}/job-comparison` - Compare with job

### Job Management
- `GET /api/jobs/` - List jobs (role-based)
- `POST /api/jobs/` - Create new job (HR only)
- `POST /api/jobs/{id}/match-analysis` - Analyze matches
- `POST /api/jobs/{id}/compare-candidates` - Compare candidates

### Talent Search
- `POST /api/talent-search/search` - Standard search
- `POST /api/talent-search/rag-search` - RAG-enhanced search
- `POST /api/talent-search/compare-services` - Compare search methods
- `GET /api/talent-search/rag/status` - RAG system status

### Interview Management
- `GET /api/interviews/` - List interviews
- `POST /api/interviews/` - Schedule interview
- `PUT /api/interviews/{id}` - Update interview
- `POST /api/interviews/{id}/feedback` - Add feedback

## 🧪 Testing

### Run System Tests

```bash
# Comprehensive system health check
python system_health_check.py

# Manual API testing
python test_talent_search.py
```

### Test Coverage Areas
- Authentication flow
- Resume parsing accuracy
- Job matching algorithms
- Search functionality
- Real-time updates
- Database integrity
- API endpoint responses

## 🐛 Troubleshooting

### Common Issues

**1. Configuration Errors**
```bash
# Check configuration
python -c "from config import Config; print(Config.validate_config())"
```

**2. Database Issues**
```bash
# Reset SQLite database (development)
python set_environment.py dev
rm instance/ats.db
python migrate_db.py

# Reset PostgreSQL database (production)
python set_environment.py prod
# You may need to drop and recreate the database:
# For docker: docker exec -it ats-postgres psql -U atsuser -c "DROP DATABASE IF EXISTS ats; CREATE DATABASE ats;"
# For local PostgreSQL: psql -U atsuser -c "DROP DATABASE IF EXISTS ats; CREATE DATABASE ats;"
python migrate_db.py
```

**3. API Key Problems**
```bash
# Verify API keys in .env
# Ensure they don't start with 'your-' or 'dev-'
```

**4. Vector Database Issues**
```bash
# Start Qdrant (if using Docker)
docker run -p 6333:6333 qdrant/qdrant

# Check connection
curl http://localhost:6333/collections
```

**5. Permission Errors**
```bash
# Fix upload directory permissions
chmod 755 uploads/
```

## 🤝 Contributing

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run in development mode
export FLASK_ENV=development
python app.py
```

### Code Style
- Follow PEP 8 for Python code
- Use ESLint for JavaScript
- Comment complex algorithms
- Write comprehensive docstrings

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Mistral AI](https://mistral.ai/) for advanced language models
- [Groq](https://groq.com/) for high-performance AI inference
- [Flask](https://flask.palletsprojects.com/) for the robust web framework
- [Qdrant](https://qdrant.tech/) for vector database capabilities
- [Bootstrap](https://getbootstrap.com/) for responsive UI components

## 📞 Support

For support, please:
1. Check the troubleshooting section
2. Run the system health check
3. Review the logs for error details
4. Create an issue with detailed reproduction steps

---

**Built with ❤️ for the future of hiring**