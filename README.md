# AI-Powered Applicant Tracking System (ATS)

An intelligent ATS platform that leverages AI to streamline the hiring process. The system includes resume parsing, candidate matching, and job application management features.

## Features

- **AI Resume Parsing**: Automatically extract structured data from PDF and DOCX resumes using Mistral AI
- **Dashboard for HR and Candidates**: Different views for recruiters and job seekers
- **User Authentication**: Secure login and registration
- **Resume Management**: Upload, view, and manage multiple resumes
- **Job Match Analysis**: AI-powered matching between candidates and job listings

## Tech Stack

### Backend
- **Flask**: Python web framework
- **SQLAlchemy**: Database ORM
- **Mistral AI**: Resume parsing and analysis
- **JWT**: Authentication tokens
- **Werkzeug**: Password hashing and file handling

### Frontend
- **HTML5**: Modern semantic markup
- **Bootstrap 5**: Responsive CSS framework
- **JavaScript (ES6+)**: Client-side functionality
- **CSS3**: Custom styling and animations

### Database
- **SQLite**: Default database (configurable)
- **Supports**: PostgreSQL, MySQL, and other SQLAlchemy-compatible databases

### AI Integration
- **Mistral AI OCR**: Advanced document parsing
- **Structured Data Extraction**: JSON-formatted resume data
- **Match Scoring**: AI-powered candidate-job matching

## Installation

### Prerequisites
- Python 3.8+
- Mistral AI API key (get one from https://console.mistral.ai/)

### Quick Setup (Windows)

1. **Download or clone this repository**
   ```cmd
   git clone <repository-url>
   cd ATS2
   ```

2. **Run the setup script**
   ```cmd
   setup.bat
   ```

3. **Configure your environment**
   - Edit the `.env` file that was created
   - Add your Mistral AI API key:
     ```
     MISTRAL_API_KEY=your_mistral_api_key_here
     ```

4. **Start the application**
   ```cmd
   run.bat
   ```

5. **Access the application**
   - Open your browser and go to `http://localhost:5000`

### Manual Setup

1. **Create virtual environment**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Install dependencies**
   ```cmd
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Copy `.env.example` to `.env` and configure:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///ats.db
   JWT_SECRET_KEY=your-jwt-secret-key-here
   MISTRAL_API_KEY=your_mistral_api_key_here
   ```

4. **Create uploads directory**
   ```cmd
   mkdir uploads
   ```

5. **Run the application**
   ```cmd
   python app.py
   ```

### Project Structure

The application follows a modular Flask architecture:

- **Backend**: Flask with SQLAlchemy, JWT authentication, Mistral AI integration
- **Frontend**: Server-side rendered HTML with Bootstrap 5, vanilla JavaScript
- **Database**: SQLite (easily configurable to PostgreSQL/MySQL)
- **AI Service**: Mistral AI for resume parsing and job matching

## Usage

### Candidate Features
- Register and create a profile
- Upload resumes for AI analysis
- View parsed resume data 
- Apply to jobs with your parsed resume

### HR Features
- Create job listings
- View applicants and their parsed resumes
- Match candidates to positions using AI analysis
- Manage the hiring workflow

## API Documentation

The backend API provides the following endpoints:

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login to get JWT token
- `GET /api/auth/user` - Get current user info

### Resumes
- `GET /api/resumes/list` - Get all resumes for current user
- `GET /api/resumes/:id` - Get resume by ID
- `POST /api/resumes/upload` - Upload a new resume
- `DELETE /api/resumes/:id` - Delete a resume

### Jobs (for HR)
- `GET /api/jobs` - Get all job listings
- `POST /api/jobs` - Create a new job listing
- `GET /api/jobs/:id` - Get job by ID
- `PUT /api/jobs/:id` - Update a job listing
- `DELETE /api/jobs/:id` - Delete a job listing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 