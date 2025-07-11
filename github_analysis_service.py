import requests
import base64
import json
from flask import Blueprint, request, jsonify, session, redirect
from auth import require_auth, verify_token
from config import Config
from mistral_service import MistralOCRService
from models import User, db
from functools import wraps

github_analysis_bp = Blueprint('github_analysis', __name__)

def require_auth_with_session(f):
    """Custom decorator that handles both JWT and session authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check JWT token
        token = request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token[7:]
            user_id = verify_token(token)
            if user_id:
                request.current_user_id = user_id
                # Get user to check session data
                user = User.query.get(user_id)
                if user:
                    return f(*args, **kwargs)
        
        return jsonify({'error': 'Authentication required'}), 401
    
    return decorated_function

class GitHubAnalysisService:
    def __init__(self):
        self.mistral_service = MistralOCRService()
    
    def generate_response(self, prompt):
        """Generate response using Mistral AI"""
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.mistral_service.client.chat.complete(
                model="mistral-small-latest",
                messages=messages,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def get_user_repos(self, access_token):
        """Get all repositories for the authenticated user"""
        try:
            headers = {'Authorization': f'token {access_token}'}
            
            # Get all repositories (including private ones if scope allows)
            repos_url = "https://api.github.com/user/repos?sort=updated&per_page=100"
            response = requests.get(repos_url, headers=headers)
            
            if response.status_code != 200:
                return None, f"Failed to fetch repositories: {response.status_code}"
            
            repos = response.json()
            
            # Extract relevant information
            simplified_repos = []
            for repo in repos:
                repo_data = {
                    'name': repo.get('name'),
                    'description': repo.get('description'),
                    'language': repo.get('language'),
                    'size': repo.get('size'),
                    'stargazers_count': repo.get('stargazers_count'),
                    'forks_count': repo.get('forks_count'),
                    'created_at': repo.get('created_at'),
                    'updated_at': repo.get('updated_at'),
                    'topics': repo.get('topics', []),
                    'homepage': repo.get('homepage'),
                    'private': repo.get('private'),
                    'full_name': repo.get('full_name')
                }
                simplified_repos.append(repo_data)
            
            return simplified_repos, None
        
        except Exception as e:
            return None, f"Error fetching repositories: {str(e)}"
    
    def get_readme_content(self, access_token, repo_full_name):
        """Get README content for a specific repository"""
        try:
            headers = {'Authorization': f'token {access_token}'}
            
            # Try different README file names
            readme_names = ['README.md', 'readme.md', 'README.txt', 'readme.txt', 'README']
            
            for readme_name in readme_names:
                readme_url = f"https://api.github.com/repos/{repo_full_name}/contents/{readme_name}"
                response = requests.get(readme_url, headers=headers)
                
                if response.status_code == 200:
                    file_data = response.json()
                    if file_data.get('content'):
                        # Decode base64 content
                        content = base64.b64decode(file_data['content']).decode('utf-8')
                        return content, None
            
            return None, "No README file found"
        
        except Exception as e:
            return None, f"Error fetching README: {str(e)}"
    
    def analyze_repository(self, repo_data, readme_content=None):
        """Analyze a single repository using AI"""
        try:
            # Create analysis prompt
            prompt = f"""
            Analyze this GitHub repository and provide a critical assessment:

            Repository: {repo_data['name']}
            Description: {repo_data.get('description', 'No description')}
            Language: {repo_data.get('language', 'Not specified')}
            Stars: {repo_data.get('stargazers_count', 0)}
            Forks: {repo_data.get('forks_count', 0)}
            Size: {repo_data.get('size', 0)} KB
            Topics: {', '.join(repo_data.get('topics', []))}
            Homepage: {repo_data.get('homepage', 'None')}
            
            README Content:
            {readme_content if readme_content else 'No README available'}
            
            Please provide a critical and insightful analysis in JSON format:
            {{
                "project_quality": "poor|fair|good|excellent",
                "complexity_level": "simple|intermediate|advanced|expert",
                "technical_depth": "surface|moderate|deep|comprehensive",
                "reach_impact": "personal|local|community|industry",
                "code_quality_indicators": ["indicator1", "indicator2"],
                "strengths": ["strength1", "strength2"],
                "weaknesses": ["weakness1", "weakness2"],
                "business_value": "low|medium|high|very_high",
                "innovation_score": 1-10,
                "maintainability": "poor|fair|good|excellent",
                "documentation_quality": "poor|fair|good|excellent",
                "overall_verdict": "Brief critical summary of the project",
                "technical_skills_demonstrated": ["skill1", "skill2"],
                "improvement_suggestions": ["suggestion1", "suggestion2"]
            }}
            
            Be honest and critical in your assessment. Consider factors like:
            - Code organization and structure
            - Documentation quality
            - Project scope and ambition
            - Technical challenges addressed
            - Real-world applicability
            - Innovation and creativity
            """
            
            # Get AI analysis
            analysis = self.generate_response(prompt)
            
            # Try to parse JSON response
            import json
            try:
                analysis_data = json.loads(analysis)
                return analysis_data, None
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw analysis
                return {
                    "overall_verdict": analysis,
                    "project_quality": "unknown",
                    "complexity_level": "unknown",
                    "technical_depth": "unknown"
                }, None
        
        except Exception as e:
            return None, f"Error analyzing repository: {str(e)}"
    
    def generate_overall_assessment(self, repo_analyses):
        """Generate an overall GitHub profile assessment"""
        try:
            # Prepare summary data
            total_repos = len(repo_analyses)
            languages_used = set()
            total_stars = 0
            total_forks = 0
            quality_scores = []
            
            for analysis in repo_analyses:
                repo_data = analysis.get('repo_data', {})
                if repo_data.get('language'):
                    languages_used.add(repo_data['language'])
                total_stars += repo_data.get('stargazers_count', 0)
                total_forks += repo_data.get('forks_count', 0)
                
                # Map quality to score
                quality = analysis.get('analysis', {}).get('project_quality', 'fair')
                quality_map = {'poor': 1, 'fair': 2, 'good': 3, 'excellent': 4}
                quality_scores.append(quality_map.get(quality, 2))
            
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 2
            
            # Create comprehensive assessment prompt
            prompt = f"""
            Analyze this developer's complete GitHub profile and provide a critical assessment:

            Profile Summary:
            - Total Repositories: {total_repos}
            - Languages Used: {', '.join(languages_used)}
            - Total Stars Received: {total_stars}
            - Total Forks: {total_forks}
            - Average Project Quality: {avg_quality:.1f}/4

            Individual Repository Analyses:
            {json.dumps(repo_analyses, indent=2)}

            Provide a comprehensive assessment in JSON format:
            {{
                "overall_rating": "novice|intermediate|advanced|expert",
                "developer_level": "junior|mid|senior|lead|architect",
                "technical_strengths": ["strength1", "strength2"],
                "areas_for_improvement": ["area1", "area2"],
                "standout_projects": ["project1", "project2"],
                "technology_breadth": "narrow|moderate|broad|extensive",
                "code_quality_trend": "declining|stable|improving|excellent",
                "collaboration_indicators": ["indicator1", "indicator2"],
                "innovation_factor": 1-10,
                "employability_score": 1-100,
                "recommended_roles": ["role1", "role2"],
                "skill_gaps": ["gap1", "gap2"],
                "portfolio_summary": "Critical 3-4 sentence summary of their coding abilities",
                "hiring_recommendation": "avoid|consider|recommend|strongly_recommend",
                "key_insights": ["insight1", "insight2", "insight3"]
            }}

            Be brutally honest and provide actionable insights. Consider:
            - Code quality and best practices
            - Project complexity and scope
            - Consistency and commitment
            - Technology choices and trends
            - Documentation and communication skills
            - Problem-solving approach
            - Industry relevance
            """
            
            # Get comprehensive analysis
            assessment = self.generate_response(prompt)
            
            try:
                assessment_data = json.loads(assessment)
                return assessment_data, None
            except json.JSONDecodeError:
                return {
                    "portfolio_summary": assessment,
                    "overall_rating": "intermediate",
                    "employability_score": 65
                }, None
        
        except Exception as e:
            return None, f"Error generating overall assessment: {str(e)}"

# Route handlers
@github_analysis_bp.route('/github/connect', methods=['GET'])
@require_auth
def connect_github():
    """Initiate GitHub OAuth connection for analysis"""
    github_auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={Config.GITHUB_CLIENT_ID}&"
        f"scope=repo,user:email&"
        f"redirect_uri=http://localhost:5000/api/auth/github/authorize"
    )
    return jsonify({'auth_url': github_auth_url})

@github_analysis_bp.route('/auth/github/authorize', methods=['GET'])
def github_callback():
    """Handle GitHub OAuth callback and store access token"""
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'No authorization code provided'}), 400
    
    # Exchange code for access token
    token_url = "https://github.com/login/oauth/access_token"
    token_data = {
        'client_id': Config.GITHUB_CLIENT_ID,
        'client_secret': Config.GITHUB_CLIENT_SECRET,
        'code': code
    }
    headers = {'Accept': 'application/json'}
    
    response = requests.post(token_url, data=token_data, headers=headers)
    token_response = response.json()
    
    access_token = token_response.get('access_token')
    if not access_token:
        return jsonify({'error': 'Failed to get access token'}), 400
    
    # Store token in session
    session['github_access_token'] = access_token
    
    # Redirect to analysis page
    return redirect('/candidate#github-analysis')

@github_analysis_bp.route('/github/analyze', methods=['POST'])
@require_auth_with_session
def analyze_github():
    """Analyze user's GitHub repositories"""
    # Get current user from request context
    user = User.query.get(request.current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user has GitHub token stored
    access_token = session.get('github_access_token')
    if not access_token:
        # Also check if it's stored in user model (fallback)
        if hasattr(user, 'github_access_token') and user.github_access_token:
            access_token = user.github_access_token
        else:
            # Provide GitHub login URL for frontend redirection
            github_auth_url = f"/api/auth/github?redirect_to_frontend=true"
            return jsonify({
                'error': 'GitHub access token not found. Please connect your GitHub account first.',
                'github_login_url': github_auth_url
            }), 401
    
    github_service = GitHubAnalysisService()
    
    try:
        # Get user repositories
        repos, error = github_service.get_user_repos(access_token)
        if error:
            return jsonify({'error': error}), 400
        
        if not repos:
            return jsonify({'error': 'No repositories found'}), 404
        
        # Analyze repositories (limit to top 10 for performance)
        repo_analyses = []
        for repo in repos[:10]:  # Limit to 10 repos
            # Get README content
            readme_content, _ = github_service.get_readme_content(access_token, repo['full_name'])
            
            # Analyze repository
            analysis, error = github_service.analyze_repository(repo, readme_content)
            if analysis:
                repo_analyses.append({
                    'repo_data': repo,
                    'analysis': analysis
                })
        
        # Generate overall assessment
        overall_assessment, error = github_service.generate_overall_assessment(repo_analyses)
        
        return jsonify({
            'success': True,
            'total_repos': len(repos),
            'analyzed_repos': len(repo_analyses),
            'repo_analyses': repo_analyses,
            'overall_assessment': overall_assessment
        })
    
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@github_analysis_bp.route('/github/repos', methods=['GET'])
@require_auth_with_session
def get_github_repos():
    """Get user's GitHub repositories without analysis"""
    # Get current user from request context
    user = User.query.get(request.current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user has GitHub token stored
    access_token = session.get('github_access_token')
    if not access_token:
        # Also check if it's stored in user model (fallback)
        if hasattr(user, 'github_access_token') and user.github_access_token:
            access_token = user.github_access_token
        else:
            # Provide GitHub login URL for frontend redirection
            github_auth_url = f"/api/auth/github?redirect_to_frontend=true"
            return jsonify({
                'error': 'GitHub access token not found', 
                'github_login_url': github_auth_url
            }), 401
    
    github_service = GitHubAnalysisService()
    repos, error = github_service.get_user_repos(access_token)
    
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({
        'success': True,
        'repositories': repos
    })
