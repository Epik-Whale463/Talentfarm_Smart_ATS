"""
Job Matching Analysis Service using LangChain and Groq
Provides detailed match analysis between resumes and job descriptions
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobMatchingService:
    """Service for analyzing job matches using AI"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Groq LLM"""
        # Try to get API key from parameter first, then environment
        groq_api_key = api_key or os.getenv('GROQ_API_KEY')
        
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY is required. Please provide it as a parameter or set the environment variable.")
        
        # Try different models in order of preference
        model_options = [
            "llama-3.1-8b-instant",
            "llama3-8b-8192", 
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
        
        self.llm = None
        for model in model_options:
            try:
                self.llm = ChatGroq(
                    temperature=0.1,
                    groq_api_key=groq_api_key,
                    model_name=model
                )
                logger.info(f"Successfully initialized with model: {model}")
                break
            except Exception as e:
                logger.warning(f"Failed to initialize model {model}: {str(e)}")
                continue
        
        if not self.llm:
            raise ValueError("Failed to initialize any supported Groq model")
    
    def analyze_job_match(self, resume_data: Dict, job_data: Dict) -> Dict:
        """
        Analyze the match between a resume and job description
        
        Args:
            resume_data: Dictionary containing resume information
            job_data: Dictionary containing job information
            
        Returns:
            Dictionary with detailed match analysis
        """
        try:
            logger.info(f"Analyzing match for resume {resume_data.get('id')} and job {job_data.get('id')}")
            
            # Extract relevant information
            resume_text = self._extract_resume_text(resume_data)
            job_text = self._extract_job_text(job_data)
            
            # Create the analysis prompt
            analysis_prompt = self._create_match_analysis_prompt()
            
            # Generate the analysis
            response = self.llm.invoke([
                SystemMessage(content="You are an expert recruiter and career advisor with deep knowledge of job matching, skills assessment, and career development."),
                HumanMessage(content=analysis_prompt.format(
                    resume_text=resume_text,
                    job_text=job_text
                ))
            ])
            
            # Parse the response
            analysis_result = self._parse_analysis_response(response.content)
            
            # Add metadata
            analysis_result['resume_id'] = resume_data.get('id')
            analysis_result['job_id'] = job_data.get('id')
            analysis_result['job_title'] = job_data.get('title')
            analysis_result['company'] = job_data.get('company')
            
            logger.info(f"Match analysis completed with {analysis_result.get('overall_match_score', 0)}% match")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in job match analysis: {str(e)}")
            return self._create_error_response(str(e))
    
    def compare_multiple_resumes(self, resumes: List[Dict], job_data: Dict) -> List[Dict]:
        """
        Compare multiple resumes against a single job description
        
        Args:
            resumes: List of resume dictionaries
            job_data: Job description dictionary
            
        Returns:
            List of match analyses sorted by match score
        """
        analyses = []
        
        for resume in resumes:
            analysis = self.analyze_job_match(resume, job_data)
            analyses.append(analysis)
        
        # Sort by match score descending
        analyses.sort(key=lambda x: x.get('overall_match_score', 0), reverse=True)
        return analyses
    
    def get_skill_gap_analysis(self, resume_data: Dict, job_data: Dict) -> Dict:
        """
        Detailed analysis of skill gaps and recommendations
        
        Args:
            resume_data: Resume information
            job_data: Job information
            
        Returns:
            Detailed skill gap analysis
        """
        try:
            resume_text = self._extract_resume_text(resume_data)
            job_text = self._extract_job_text(job_data)
            
            gap_analysis_prompt = self._create_skill_gap_prompt()
            
            response = self.llm.invoke([
                SystemMessage(content="You are a career development expert specializing in skill gap analysis and professional growth recommendations."),
                HumanMessage(content=gap_analysis_prompt.format(
                    resume_text=resume_text,
                    job_text=job_text
                ))
            ])
            
            return self._parse_skill_gap_response(response.content)
            
        except Exception as e:
            logger.error(f"Error in skill gap analysis: {str(e)}")
            return self._create_error_response(str(e))
    
    def _extract_resume_text(self, resume_data: Dict) -> str:
        """Extract comprehensive text from resume data"""
        parts = []
        
        # Basic info
        if resume_data.get('name'):
            parts.append(f"Name: {resume_data['name']}")
        if resume_data.get('email'):
            parts.append(f"Email: {resume_data['email']}")
        
        # Skills
        if resume_data.get('skills'):
            skills_text = ", ".join(resume_data['skills']) if isinstance(resume_data['skills'], list) else str(resume_data['skills'])
            parts.append(f"Skills: {skills_text}")
        
        # Experience
        if resume_data.get('experience'):
            parts.append("Experience:")
            experiences = resume_data['experience'] if isinstance(resume_data['experience'], list) else [resume_data['experience']]
            for exp in experiences:
                if isinstance(exp, dict):
                    exp_text = f"- {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')}"
                    if exp.get('duration'):
                        exp_text += f" ({exp['duration']})"
                    if exp.get('description'):
                        exp_text += f": {exp['description']}"
                    parts.append(exp_text)
                else:
                    parts.append(f"- {exp}")
        
        # Education
        if resume_data.get('education'):
            parts.append("Education:")
            educations = resume_data['education'] if isinstance(resume_data['education'], list) else [resume_data['education']]
            for edu in educations:
                if isinstance(edu, dict):
                    edu_text = f"- {edu.get('degree', 'N/A')} from {edu.get('institution', 'N/A')}"
                    if edu.get('year'):
                        edu_text += f" ({edu['year']})"
                    parts.append(edu_text)
                else:
                    parts.append(f"- {edu}")
        
        # Raw text if available
        if resume_data.get('raw_text'):
            parts.append("Additional Information:")
            parts.append(resume_data['raw_text'])
        
        return "\n".join(parts)
    
    def _extract_job_text(self, job_data: Dict) -> str:
        """Extract comprehensive text from job data"""
        parts = []
        
        if job_data.get('title'):
            parts.append(f"Job Title: {job_data['title']}")
        if job_data.get('company'):
            parts.append(f"Company: {job_data['company']}")
        if job_data.get('location'):
            parts.append(f"Location: {job_data['location']}")
        if job_data.get('employment_type'):
            parts.append(f"Employment Type: {job_data['employment_type']}")
        if job_data.get('salary_min') and job_data.get('salary_max'):
            parts.append(f"Salary Range: ${job_data['salary_min']:,} - ${job_data['salary_max']:,}")
        
        if job_data.get('description'):
            parts.append(f"Job Description: {job_data['description']}")
        
        if job_data.get('requirements'):
            parts.append("Requirements:")
            requirements = job_data['requirements'] if isinstance(job_data['requirements'], list) else [job_data['requirements']]
            for req in requirements:
                parts.append(f"- {req}")
        
        return "\n".join(parts)
    
    def _create_match_analysis_prompt(self) -> PromptTemplate:
        """Create the prompt template for match analysis"""
        template = """
Analyze the match between this resume and job description. Provide a comprehensive analysis in JSON format.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_text}

Provide your analysis in the following JSON format (return ONLY valid JSON, no comments or markdown):
{{
    "overall_match_score": <number between 0-100>,
    "skill_match_score": <number between 0-100>,
    "experience_match_score": <number between 0-100>,
    "education_match_score": <number between 0-100>,
    "matching_skills": ["skill1", "skill2"],
    "missing_skills": ["skill1", "skill2"],
    "matching_experience": ["experience1", "experience2"],
    "missing_experience": ["requirement1", "requirement2"],
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "recommendations": ["recommendation1", "recommendation2"],
    "fit_assessment": "Excellent/Good/Fair/Poor",
    "summary": "Brief 2-3 sentence summary of the match",
    "detailed_analysis": {{
        "skills_analysis": "Detailed analysis of skills match",
        "experience_analysis": "Detailed analysis of experience match", 
        "education_analysis": "Detailed analysis of education match",
        "culture_fit": "Assessment of potential culture fit",
        "growth_potential": "Assessment of growth potential in this role"
    }}
}}

Be thorough and specific in your analysis. Focus on relevant skills, experience levels, and qualifications. Return ONLY the JSON object, no other text.
"""
        return PromptTemplate(template=template, input_variables=["resume_text", "job_text"])
    
    def _create_skill_gap_prompt(self) -> PromptTemplate:
        """Create prompt for detailed skill gap analysis"""
        template = """
Perform a detailed skill gap analysis between this resume and job requirements.

RESUME:
{resume_text}

JOB REQUIREMENTS:
{job_text}

Provide a detailed skill gap analysis in JSON format:
{{
    "critical_gaps": [
        {{
            "skill": "skill_name",
            "importance": "High/Medium/Low",
            "current_level": "None/Beginner/Intermediate/Advanced",
            "required_level": "Beginner/Intermediate/Advanced/Expert",
            "learning_resources": ["resource1", "resource2", ...],
            "time_to_acquire": "1-3 months/3-6 months/6-12 months/1+ years"
        }}
    ],
    "minor_gaps": [...],
    "strengths_to_leverage": [
        {{
            "skill": "skill_name",
            "proficiency": "current level",
            "relevance": "how it applies to the job"
        }}
    ],
    "learning_path": [
        {{
            "phase": 1,
            "duration": "time period",
            "focus_areas": ["area1", "area2", ...],
            "suggested_actions": ["action1", "action2", ...]
        }}
    ],
    "certification_recommendations": ["cert1", "cert2", ...],
    "project_suggestions": ["project1", "project2", ...],
    "networking_advice": "advice for building relevant connections",
    "interview_preparation": {{
        "likely_questions": ["question1", "question2", ...],
        "key_points_to_emphasize": ["point1", "point2", ...],
        "stories_to_prepare": ["story1", "story2", ...]
    }}
}}
"""
        return PromptTemplate(template=template, input_variables=["resume_text", "job_text"])
    
    def _parse_analysis_response(self, response_text: str) -> Dict:
        """Parse the AI response into structured data"""
        try:
            # Try to extract JSON from the response
            # Handle markdown code blocks
            if '```json' in response_text:
                start_idx = response_text.find('```json') + 7
                end_idx = response_text.find('```', start_idx)
                if end_idx != -1:
                    json_text = response_text[start_idx:end_idx].strip()
                else:
                    # Find the JSON block
                    start_idx = response_text.find('{', start_idx)
                    end_idx = response_text.rfind('}') + 1
                    json_text = response_text[start_idx:end_idx] if start_idx != -1 else ""
            else:
                # Fallback to finding JSON blocks
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_text = response_text[start_idx:end_idx] if start_idx != -1 else ""
            
            if json_text:
                # Clean up common JSON issues
                json_text = json_text.replace('// Not applicable as education details are not provided in the resume', '')
                json_text = json_text.replace('// ', '')  # Remove other comment-style issues
                return json.loads(json_text)
            else:
                return self._create_fallback_analysis(response_text)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}")
            return self._create_fallback_analysis(response_text)
    
    def _parse_skill_gap_response(self, response_text: str) -> Dict:
        """Parse skill gap analysis response"""
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx]
                return json.loads(json_text)
            else:
                return self._create_fallback_skill_gap(response_text)
                
        except json.JSONDecodeError:
            return self._create_fallback_skill_gap(response_text)
    
    def _create_fallback_analysis(self, response_text: str) -> Dict:
        """Create a fallback analysis when JSON parsing fails"""
        return {
            "overall_match_score": 50,
            "skill_match_score": 50,
            "experience_match_score": 50,
            "education_match_score": 50,
            "matching_skills": [],
            "missing_skills": [],
            "matching_experience": [],
            "missing_experience": [],
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
            "fit_assessment": "Analysis needed",
            "summary": "Analysis could not be completed automatically. Manual review recommended.",
            "detailed_analysis": {
                "skills_analysis": response_text[:500] + "..." if len(response_text) > 500 else response_text,
                "experience_analysis": "Manual analysis required",
                "education_analysis": "Manual analysis required",
                "culture_fit": "Manual assessment required",
                "growth_potential": "Manual assessment required"
            }
        }
    
    def _create_fallback_skill_gap(self, response_text: str) -> Dict:
        """Create fallback skill gap analysis"""
        return {
            "critical_gaps": [],
            "minor_gaps": [],
            "strengths_to_leverage": [],
            "learning_path": [],
            "certification_recommendations": [],
            "project_suggestions": [],
            "networking_advice": "Connect with professionals in your target industry",
            "interview_preparation": {
                "likely_questions": [],
                "key_points_to_emphasize": [],
                "stories_to_prepare": []
            },
            "raw_analysis": response_text
        }
    
    def _create_error_response(self, error_message: str) -> Dict:
        """Create an error response"""
        return {
            "error": True,
            "message": error_message,
            "overall_match_score": 0,
            "skill_match_score": 0,
            "experience_match_score": 0,
            "education_match_score": 0,
            "matching_skills": [],
            "missing_skills": [],
            "matching_experience": [],
            "missing_experience": [],
            "strengths": [],
            "weaknesses": [],
            "recommendations": ["Unable to analyze due to technical error"],
            "fit_assessment": "Error",
            "summary": f"Analysis failed: {error_message}",
            "detailed_analysis": {
                "skills_analysis": f"Error: {error_message}",
                "experience_analysis": f"Error: {error_message}",
                "education_analysis": f"Error: {error_message}",
                "culture_fit": f"Error: {error_message}",
                "growth_potential": f"Error: {error_message}"
            }
        }
