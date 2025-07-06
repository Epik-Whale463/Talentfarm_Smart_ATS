"""
Resume Insights Service using LangChain and Groq Llama models
Provides structured technical analysis of candidate resumes
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import BaseOutputParser
from config import Config


class ResumeInsightsOutputParser(BaseOutputParser):
    """Custom output parser for structured resume insights"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """Parse the LLM output into structured insights"""
        try:
            # Try to extract JSON from the response
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # Fallback parsing if JSON is not found
                return {
                    "error": "Could not parse structured insights",
                    "raw_response": text
                }
        except json.JSONDecodeError:
            return {
                "error": "Invalid JSON in response",
                "raw_response": text
            }


class ResumeInsightsService:
    """Service for generating structured resume insights using Groq Llama models"""
    
    def __init__(self):
        """Initialize the service with Groq LLM"""
        self.llm = ChatGroq(
            groq_api_key=Config.GROQ_API_KEY,
            model_name="llama3-70b-8192",  # Using Llama 3 70B model
            temperature=0.1,  # Low temperature for consistent analysis
            max_tokens=4000
        )
        self.output_parser = ResumeInsightsOutputParser()
    
    def generate_insights(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive technical insights for a resume
        
        Args:
            resume_data: Parsed resume data from the database
            
        Returns:
            Dict containing structured insights
        """
        try:
            # Create the prompt template
            prompt_template = ChatPromptTemplate.from_template("""
You are an expert technical recruiter and career advisor. Analyze the following resume data and provide a comprehensive, structured technical assessment.

Resume Data:
- Name: {name}
- Skills: {skills}
- Experience: {experience}
- Education: {education}
- Raw Text: {raw_text}

Please provide a detailed analysis in the following JSON structure:

{{
    "technical_assessment": {{
        "overall_rating": "number (1-10)",
        "technical_strength": "string (Beginner/Intermediate/Advanced/Expert)",
        "summary": "brief overall assessment"
    }},
    "skills_analysis": {{
        "technical_skills": {{
            "programming_languages": [
                {{"skill": "language", "proficiency": "Beginner/Intermediate/Advanced/Expert", "evidence": "brief explanation"}}
            ],
            "frameworks_libraries": [
                {{"skill": "framework", "proficiency": "level", "evidence": "explanation"}}
            ],
            "databases": [
                {{"skill": "database", "proficiency": "level", "evidence": "explanation"}}
            ],
            "tools_technologies": [
                {{"skill": "tool", "proficiency": "level", "evidence": "explanation"}}
            ]
        }},
        "soft_skills": [
            {{"skill": "soft skill", "evidence": "how it's demonstrated in resume"}}
        ],
        "skill_gaps": [
            {{"gap": "missing skill", "importance": "High/Medium/Low", "recommendation": "how to acquire"}}
        ]
    }},
    "experience_evaluation": {{
        "total_years": "number",
        "career_progression": "Poor/Fair/Good/Excellent",
        "project_quality": {{
            "complexity": "Low/Medium/High",
            "impact": "description of project impact",
            "technical_depth": "assessment of technical implementation"
        }},
        "responsibilities": [
            {{"role": "job title", "key_achievements": ["achievement1", "achievement2"], "technical_growth": "assessment"}}
        ]
    }},
    "education_assessment": {{
        "relevance": "High/Medium/Low",
        "institutions": [
            {{"name": "institution", "degree": "degree", "relevance_score": "1-10", "notes": "assessment"}}
        ],
        "certifications": [
            {{"name": "certification", "relevance": "High/Medium/Low", "validity": "Current/Expired/Unknown"}}
        ]
    }},
    "recommendations": {{
        "immediate_improvements": [
            {{"area": "improvement area", "action": "specific action to take", "priority": "High/Medium/Low"}}
        ],
        "career_advancement": [
            {{"suggestion": "career advice", "timeline": "short/medium/long term", "rationale": "why this helps"}}
        ],
        "technical_development": [
            {{"skill": "skill to develop", "resources": "learning resources", "estimated_time": "time to learn"}}
        ]
    }},
    "market_positioning": {{
        "suitable_roles": ["role1", "role2", "role3"],
        "experience_level": "Junior/Mid/Senior/Lead",
        "competitive_advantage": "what makes this candidate stand out",
        "market_demand": "High/Medium/Low",
        "salary_range_estimate": "estimated range based on skills and experience"
    }},
    "red_flags": [
        {{"issue": "potential concern", "severity": "High/Medium/Low", "impact": "how it affects candidacy"}}
    ],
    "strengths": [
        {{"strength": "key strength", "evidence": "supporting evidence", "market_value": "how valuable this is"}}
    ]
}}

Important: Respond ONLY with the JSON structure. Do not include any additional text, explanations, or markdown formatting.
""")
            
            # Prepare the data for the prompt
            skills_str = json.dumps(resume_data.get('skills', []))
            experience_str = json.dumps(resume_data.get('experience', []))
            education_str = json.dumps(resume_data.get('education', []))
            
            # Create the prompt with resume data
            messages = prompt_template.format_messages(
                name=resume_data.get('name', 'Unknown'),
                skills=skills_str,
                experience=experience_str,
                education=education_str,
                raw_text=resume_data.get('raw_text', '')[:2000]  # Limit raw text to avoid token limits
            )
            
            # Generate insights using the LLM
            response = self.llm(messages)
            
            # Parse the response
            insights = self.output_parser.parse(response.content)
            
            # Add metadata
            insights['generated_at'] = datetime.now().isoformat()
            insights['model_used'] = 'llama3-70b-8192'
            insights['service_version'] = '1.0'
            
            return {
                'success': True,
                'insights': insights
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to generate insights: {str(e)}'
            }
    
    def get_skill_recommendations(self, current_skills: List[str], target_role: str = None) -> Dict[str, Any]:
        """
        Get specific skill recommendations based on current skills and target role
        
        Args:
            current_skills: List of current skills
            target_role: Target job role (optional)
            
        Returns:
            Dict containing skill recommendations
        """
        try:
            prompt_template = ChatPromptTemplate.from_template("""
You are a technical career advisor. Based on the current skills and target role, provide skill recommendations.

Current Skills: {skills}
Target Role: {target_role}

Provide recommendations in this JSON format:
{{
    "recommended_skills": [
        {{"skill": "skill name", "priority": "High/Medium/Low", "reason": "why important", "learning_path": "how to learn"}}
    ],
    "skill_upgrades": [
        {{"current_skill": "existing skill", "upgrade_to": "advanced version", "benefit": "what this provides"}}
    ],
    "trending_skills": [
        {{"skill": "trending skill", "relevance": "why relevant", "demand": "market demand level"}}
    ]
}}

Respond ONLY with JSON.
""")
            
            messages = prompt_template.format_messages(
                skills=json.dumps(current_skills),
                target_role=target_role or "General Software Development"
            )
            
            response = self.llm(messages)
            recommendations = self.output_parser.parse(response.content)
            
            return {
                'success': True,
                'recommendations': recommendations
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to generate skill recommendations: {str(e)}'
            }
    
    def compare_with_job_requirements(self, resume_data: Dict[str, Any], job_requirements: List[str]) -> Dict[str, Any]:
        """
        Compare resume against specific job requirements
        
        Args:
            resume_data: Parsed resume data
            job_requirements: List of job requirements
            
        Returns:
            Dict containing comparison analysis
        """
        try:
            prompt_template = ChatPromptTemplate.from_template("""
Compare this resume against the job requirements and provide a fit analysis.

Resume Skills: {skills}
Resume Experience: {experience}
Job Requirements: {requirements}

Provide analysis in this JSON format:
{{
    "overall_fit_score": "number (0-100)",
    "matching_skills": [
        {{"skill": "skill name", "match_strength": "Exact/Partial/Related", "evidence": "where found in resume"}}
    ],
    "missing_skills": [
        {{"skill": "missing skill", "importance": "Critical/Important/Nice-to-have", "alternative": "similar skill candidate has"}}
    ],
    "transferable_skills": [
        {{"resume_skill": "existing skill", "job_requirement": "required skill", "transferability": "High/Medium/Low"}}
    ],
    "experience_match": {{
        "years_requirement_met": true/false,
        "relevant_projects": ["project1", "project2"],
        "gap_areas": ["area1", "area2"]
    }},
    "recommendation": "Overall recommendation (Strong Fit/Good Fit/Potential Fit/Poor Fit)",
    "improvement_suggestions": [
        {{"area": "improvement area", "action": "what to do", "timeline": "when to do it"}}
    ]
}}

Respond ONLY with JSON.
""")
            
            messages = prompt_template.format_messages(
                skills=json.dumps(resume_data.get('skills', [])),
                experience=json.dumps(resume_data.get('experience', [])),
                requirements=json.dumps(job_requirements)
            )
            
            response = self.llm(messages)
            comparison = self.output_parser.parse(response.content)
            
            return {
                'success': True,
                'comparison': comparison
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to generate job comparison: {str(e)}'
            }


# Global service instance
resume_insights_service = ResumeInsightsService()
