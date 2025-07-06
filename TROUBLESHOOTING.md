# Troubleshooting Guide

## Common Issues and Solutions

### 1. Mistral AI API Issues

#### Error: "Files.upload() got an unexpected keyword argument 'purpose'"
**Solution**: Updated the Mistral service to use the latest API format. The `purpose` parameter has been removed.

#### Error: "MISTRAL_API_KEY not found"
**Solution**: 
1. Copy `.env.example` to `.env`
2. Add your Mistral API key: `MISTRAL_API_KEY=your_api_key_here`
3. Get an API key from https://console.mistral.ai/

#### Error: "Invalid API key"
**Solution**: Verify your API key is correct and has sufficient credits.

### 2. Template/URL Issues

#### Error: "Could not build url for endpoint 'dashboard.register'"
**Solution**: Fixed template URLs to use correct endpoint names (`register_page` instead of `register`).

#### Error: "TemplateNotFound"
**Solution**: All required templates have been created in the `templates/` directory.

### 3. Database Issues

#### Error: "No such table"
**Solution**: Database tables are automatically created when the app starts. If issues persist:
```bash
python create_demo_data.py
```

#### Error: "Database is locked"
**Solution**: Close all database connections and restart the application.

### 4. File Upload Issues

#### Error: "No file provided"
**Solution**: Ensure you're selecting a PDF or DOCX file in the upload form.

#### Error: "File type not allowed"
**Solution**: Only PDF and DOCX files are supported. Convert other formats first.

### 5. Authentication Issues

#### Error: "Invalid or expired token"
**Solution**: 
1. Clear browser localStorage
2. Log in again
3. Check that JWT_SECRET_KEY is consistent

#### Error: "CSRF state validation failed" or "mismatching_state"
**Solution**:
1. This is often due to session issues with the OAuth flow
2. Try clearing your browser cookies and cache
3. Make sure you're not using multiple tabs for the authentication flow
4. Check that cookies are enabled in your browser

#### Error: "User not found"
**Solution**: Register a new account or use the demo data script.

## Testing the Application

### 1. Test Mistral AI Integration
```bash
python test_mistral.py
```

### 2. Create Demo Data
```bash
python create_demo_data.py
```
This creates:
- HR User: `hr@company.com` / `password123`
- Candidate: `candidate@email.com` / `password123`
- Sample job listings

### 3. Test File Upload
1. Log in as candidate
2. Go to Resumes page
3. Upload the sample resume: `resumes/RamaCharan_resume.pdf`

### 4. Test Job Application
1. Upload a resume first
2. Go to Jobs page
3. Apply to a job using your parsed resume

## Configuration Checklist

### Required Environment Variables
- `MISTRAL_API_KEY`: Your Mistral AI API key
- `SECRET_KEY`: Flask secret key (auto-generated for development)
- `JWT_SECRET_KEY`: JWT signing key (auto-generated for development)

### Optional Environment Variables
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `FLASK_ENV`: Set to `production` for production deployment

### File Structure Verification
```
ATS2/
├── app.py ✓
├── config.py ✓
├── models.py ✓
├── auth.py ✓
├── resumes.py ✓
├── jobs.py ✓
├── dashboard.py ✓
├── mistral_service.py ✓
├── templates/ ✓
│   ├── base.html ✓
│   ├── index.html ✓
│   ├── login.html ✓
│   ├── register.html ✓
│   ├── candidate_dashboard.html ✓
│   ├── hr_dashboard.html ✓
│   ├── dashboard.html ✓
│   ├── resumes.html ✓
│   ├── jobs.html ✓
│   └── profile.html ✓
├── static/ ✓
│   ├── css/style.css ✓
│   └── js/
│       ├── auth.js ✓
│       └── main.js ✓
├── uploads/ (created automatically)
├── .env (copy from .env.example)
└── requirements.txt ✓
```

## Performance Tips

### 1. Mistral AI Rate Limits
- The service includes basic error handling
- Consider implementing retry logic for production
- Monitor API usage and costs

### 2. Database Optimization
- For production, use PostgreSQL instead of SQLite
- Add database indexes for frequently queried fields
- Implement connection pooling

### 3. File Upload Optimization
- Current limit: 16MB per file
- Consider cloud storage for production (AWS S3, etc.)
- Implement file compression for large documents

## Production Deployment

### 1. Security Checklist
- [ ] Change default secret keys
- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS
- [ ] Implement rate limiting
- [ ] Add input validation and sanitization
- [ ] Use a production WSGI server (Gunicorn, uWSGI)

### 2. Database Migration
- [ ] Switch to PostgreSQL or MySQL
- [ ] Set up database backups
- [ ] Implement database migrations
- [ ] Monitor database performance

### 3. Monitoring and Logging
- [ ] Set up application logging
- [ ] Monitor API usage and costs
- [ ] Implement health checks
- [ ] Set up error tracking (Sentry, etc.)

## Getting Help

1. Check this troubleshooting guide first
2. Review the application logs for detailed error messages
3. Test individual components using the provided test scripts
4. Verify your environment configuration
5. Check the Mistral AI documentation for API changes
