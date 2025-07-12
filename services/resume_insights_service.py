"""
Resume Insights Service using LangChain and Groq Llama models
Provides structure    "executive_summary": {
        "overall_score": "number (1-10 with decimals, be harsh)",
        "technical_level": "Junior/Mid/Senior/Principal/Distinguished",
        "hire_confidence": "Strong Yes/Yes/Maybe/No/Strong No",
        "risk_level": "Low/Medium/High/Critical",
        "summary": "3-4 sentence brutal honest summary of this candidate's strengths and weaknesses",
        "market_tier": "Top 5%/Top 10%/Top 25%/Average/Below Average/Poor"
    },ical analysis of candidate resumes
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
            # Clean the text first
            text = text.strip()
            
            # Try to extract JSON from the response
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = text[start_idx:end_idx]
                
                # Try to clean up common JSON issues
                json_str = json_str.replace('\n', ' ')
                json_str = json_str.replace('\\', '')
                
                parsed_json = json.loads(json_str)
                
                # Validate required fields
                if not isinstance(parsed_json, dict):
                    raise ValueError("Parsed result is not a dictionary")
                
                # Ensure executive_summary exists
                if 'executive_summary' not in parsed_json:
                    raise ValueError("Missing executive_summary in parsed JSON")
                
                return parsed_json
            else:
                # Fallback parsing if JSON is not found
                return {
                    "error": "Could not find valid JSON structure in response",
                    "raw_response": text[:500]  # Limit raw response length
                }
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON in response: {str(e)}",
                "raw_response": text[:500]
            }
        except Exception as e:
            return {
                "error": f"Failed to parse response: {str(e)}",
                "raw_response": text[:500]
            }


class ResumeInsightsService:
    """Service for generating structured resume insights using Groq Llama models"""
    
    def __init__(self):
        """Initialize the service with Groq LLM"""
        self.llm = ChatGroq(
            groq_api_key=Config.GROQ_API_KEY,
            model_name="llama3-70b-8192",  # Using Llama 3 70B model for deep analysis
            temperature=0.05,  # Very low temperature for consistent, critical analysis
            max_tokens=8000  # Increased for extensive analysis
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
            # Create a more reliable, simpler prompt template
            prompt_template = ChatPromptTemplate.from_template("""
You are a senior technical recruiter. Analyze this resume and provide structured assessment.

Resume Data:
Name: {name}
Skills: {skills}
Experience: {experience}
Education: {education}

Provide analysis in valid JSON format exactly like this:

{{
    "executive_summary": {{
        "overall_score": 7.5,
        "technical_level": "Mid",
        "hire_confidence": "Yes",
        "risk_level": "Low",
        "summary": "Detailed assessment summary goes here"
    }},
    "deep_technical_analysis": {{
        "core_skills": [
            {{
                "skill": "Python",
                "claimed_level": "Advanced",
                "assessed_level": "Intermediate",
                "evidence_quality": "Moderate",
                "depth_indicators": ["Built web applications", "Used frameworks"],
                "red_flags": [],
                "verdict": "Competent"
            }}
        ],
        "architecture_understanding": {{
            "system_design": "Shows basic understanding of web architecture",
            "scalability_awareness": "Limited evidence of large-scale systems",
            "complexity_handled": "Small to medium applications",
            "architectural_patterns": ["MVC", "REST APIs"]
        }},
        "code_quality_indicators": {{
            "testing_practices": "Some evidence of unit testing",
            "documentation_habits": "Basic documentation shown",
            "code_review_experience": "Team collaboration mentioned",
            "technical_debt_awareness": "Good coding practices evident"
        }}
    }},
    "experience_scrutiny": {{
        "career_velocity": {{
            "progression_rate": "Appropriate for experience level",
            "responsibility_growth": "Steady increase in project complexity",
            "technical_growth": "Clear skill development over time",
            "leadership_trajectory": "Shows potential for technical leadership"
        }},
        "project_analysis": [
            {{
                "project": "E-commerce Platform",
                "complexity_assessment": "Medium",
                "technical_challenges": "Payment integration, user management",
                "impact_verification": "Mentioned improved user experience",
                "role_clarity": "Clear technical contributions described",
                "buzzword_ratio": "20%",
                "credibility_score": 7
            }}
        ],
        "employment_red_flags": []
    }},
    "hiring_recommendation": {{
        "decision": "Yes",
        "confidence": "Medium",
        "conditions": ["Verify technical depth in interview"],
        "interview_priorities": ["System design capabilities", "Code quality practices"],
        "onboarding_requirements": ["Mentoring on enterprise patterns"],
        "risk_factors": ["May need guidance on complex architectures"]
    }},
    "development_roadmap": {{
        "immediate_gaps": [
            {{
                "gap": "System design experience",
                "business_impact": "May struggle with complex architecture decisions",
                "time_to_fill": "6-12 months",
                "training_cost": "Medium"
            }}
        ],
        "growth_potential": {{
            "trajectory": "Steady",
            "learning_velocity": "Good - shows consistent skill acquisition",
            "adaptability": "Adapts well to new technologies",
            "ceiling": "Senior Engineer with proper mentoring"
        }}
    }},
    "skill_verification": {{
        "verified_skills": ["Python", "JavaScript", "SQL"],
        "unverified_claims": ["Machine Learning", "DevOps"],
        "skill_gaps": ["System Design", "Performance Optimization"],
        "market_competitiveness": "Competitive for mid-level positions"
    }}
}}

Respond with ONLY the JSON structure above, no other text.
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
                education=education_str
            )
            
            # Generate insights using the LLM
            response = self.llm(messages)
            
            # Parse the response with better error handling
            insights = self.output_parser.parse(response.content)
            
            # Check if parsing failed
            if "error" in insights:
                # Create a fallback response
                insights = self._create_fallback_insights(resume_data)
            
            # Add metadata
            insights['generated_at'] = datetime.now().isoformat()
            insights['model_used'] = 'llama3-70b-8192'
            insights['service_version'] = '2.0-enhanced'
            insights['analysis_type'] = 'comprehensive_critical'
            insights['review_depth'] = 'senior_technical_recruiter'
            
            return {
                'success': True,
                'insights': insights
            }
            
        except Exception as e:
            # Return fallback insights if LLM fails
            fallback_insights = self._create_fallback_insights(resume_data)
            fallback_insights['error'] = str(e)
            fallback_insights['fallback'] = True
            
            return {
                'success': True,  # Still return success with fallback
                'insights': fallback_insights
            }
    
    def _create_fallback_insights(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback insights when LLM fails"""
        skills = resume_data.get('skills', [])
        experience = resume_data.get('experience', [])
        
        # Basic scoring based on data available
        skill_count = len(skills)
        exp_count = len(experience)
        
        if skill_count > 10 and exp_count > 3:
            score = 7.0
            level = "Senior"
            confidence = "Yes"
        elif skill_count > 5 and exp_count > 1:
            score = 6.0
            level = "Mid"
            confidence = "Maybe"
        else:
            score = 4.0
            level = "Junior"
            confidence = "Maybe"
        
        return {
            "executive_summary": {
                "overall_score": score,
                "technical_level": level,
                "hire_confidence": confidence,
                "risk_level": "Medium",
                "summary": f"Candidate has {skill_count} technical skills and {exp_count} work experiences. Assessment based on available data only."
            },
            "deep_technical_analysis": {
                "core_skills": [
                    {
                        "skill": skill,
                        "claimed_level": "Unknown",
                        "assessed_level": "Unknown",
                        "evidence_quality": "Weak",
                        "depth_indicators": [],
                        "red_flags": [],
                        "verdict": "Unproven"
                    } for skill in skills[:5]
                ],
                "architecture_understanding": {
                    "system_design": "Insufficient data for assessment",
                    "scalability_awareness": "Cannot assess from available data",
                    "complexity_handled": "Unknown",
                    "architectural_patterns": []
                },
                "code_quality_indicators": {
                    "testing_practices": "Not evident from resume",
                    "documentation_habits": "Not clear from available data",
                    "code_review_experience": "Cannot assess",
                    "technical_debt_awareness": "Unknown"
                }
            },
            "experience_scrutiny": {
                "career_velocity": {
                    "progression_rate": "Cannot assess",
                    "responsibility_growth": "Insufficient data",
                    "technical_growth": "Cannot determine",
                    "leadership_trajectory": "Unknown"
                },
                "project_analysis": [],
                "employment_red_flags": []
            },
            "hiring_recommendation": {
                "decision": confidence,
                "confidence": "Low",
                "conditions": ["Comprehensive technical interview required"],
                "interview_priorities": ["Technical depth validation", "Problem-solving abilities"],
                "onboarding_requirements": ["Full technical assessment"],
                "risk_factors": ["Limited data for accurate assessment"]
            },
            "development_roadmap": {
                "immediate_gaps": [
                    {
                        "gap": "Detailed technical assessment needed",
                        "business_impact": "Cannot accurately assess fit without more data",
                        "time_to_fill": "Immediate",
                        "training_cost": "Unknown"
                    }
                ],
                "growth_potential": {
                    "trajectory": "Unknown",
                    "learning_velocity": "Cannot assess",
                    "adaptability": "Unknown",
                    "ceiling": "Cannot determine without more data"
                }
            },
            "skill_verification": {
                "verified_skills": [],
                "unverified_claims": skills,
                "skill_gaps": ["Comprehensive technical interview needed"],
                "market_competitiveness": "Cannot assess"
            },
            "fallback_mode": True
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
    
    def generate_technical_assessment(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate ultra-detailed technical assessment focusing on technical competency validation
        
        Args:
            resume_data: Parsed resume data from the database
            
        Returns:
            Dict containing deep technical insights
        """
        try:
            prompt_template = ChatPromptTemplate.from_template("""
You are a Principal Software Engineer and Technical Architect with 20+ years of experience conducting technical interviews at FAANG companies. Your job is to evaluate this resume with extreme technical rigor.

Resume Data:
- Name: {name}
- Skills: {skills}
- Experience: {experience}
- Education: {education}
- Raw Text: {raw_text}

TECHNICAL ASSESSMENT CRITERIA:
- Distinguish between theoretical knowledge vs. practical experience
- Identify depth vs. breadth in technical skills
- Assess problem-solving complexity based on described projects
- Evaluate technical leadership and mentorship capabilities
- Flag potential resume inflation or exaggeration

Provide your technical assessment in this JSON format:

{{
    "technical_credibility_score": {{
        "overall_score": "1-10 (be harsh, 7+ is exceptional)",
        "confidence_level": "Low/Medium/High confidence in this assessment",
        "assessment_basis": "what evidence supports this score"
    }},
    
    "coding_competency": {{
        "programming_languages": [
            {{
                "language": "language name",
                "claimed_proficiency": "what resume suggests",
                "evidence_analysis": "specific evidence from projects/experience",
                "likely_actual_level": "Novice/Beginner/Intermediate/Advanced/Expert",
                "technical_debt_risk": "risk they write unmaintainable code",
                "interview_focus": ["specific areas to probe in coding interview"]
            }}
        ],
        "algorithmic_thinking": {{
            "evidence": "signs of computational thinking in their experience",
            "complexity_handled": "most complex algorithms/data structures used",
            "optimization_awareness": "evidence they think about performance",
            "scalability_understanding": "signs they understand big-O and scaling"
        }},
        "code_architecture": {{
            "design_patterns": "evidence of knowing proper patterns",
            "system_design": "largest/most complex system they've architected",
            "api_design": "experience with designing APIs and interfaces",
            "testing_maturity": "sophistication of their testing approach"
        }}
    }},
    
    "project_deep_dive": [
        {{
            "project_name": "project title",
            "technical_complexity": "1-10 scale",
            "role_clarity": "clearly defined vs vague responsibilities",
            "technical_depth": "depth of technical implementation details",
            "problem_solving": "evidence of solving hard technical problems",
            "impact_measurability": "quantifiable technical/business impact",
            "technologies_justified": "whether tech stack choices make sense",
            "red_flags": ["concerning aspects of this project description"],
            "follow_up_questions": ["questions to validate their actual contribution"]
        }}
    ],
    
    "technical_leadership": {{
        "mentorship_evidence": "concrete signs of mentoring others",
        "technical_decision_making": "evidence of making architectural decisions",
        "cross_team_collaboration": "signs of working with other engineering teams",
        "technical_communication": "ability to explain complex concepts",
        "influence_scope": "how many engineers they've influenced/led"
    }},
    
    "learning_and_growth": {{
        "technology_adoption": "how quickly they adopt new technologies",
        "continuous_learning": "evidence of staying current with tech trends",
        "depth_vs_breadth": "do they go deep or stay surface-level",
        "learning_velocity": "estimated speed of acquiring new technical skills",
        "adaptability": "evidence of transitioning between different tech stacks"
    }},
    
    "potential_concerns": [
        {{
            "concern": "specific technical concern",
            "risk_level": "Critical/High/Medium/Low",
            "validation_method": "how to verify this in interview",
            "mitigation": "what could address this concern"
        }}
    ],
    
    "interview_strategy": {{
        "technical_validation_priorities": ["top 3 things to validate technically"],
        "coding_challenge_focus": ["types of problems to give them"],
        "system_design_complexity": "appropriate system design challenge level",
        "deep_dive_projects": ["which projects to probe deeply"],
        "red_flag_questions": ["questions to ask about concerning areas"]
    }},
    
    "hire_recommendation": {{
        "technical_fit": "Strong Yes/Yes/Maybe/No/Strong No",
        "level_recommendation": "Junior/Mid/Senior/Staff/Principal",
        "team_fit_considerations": ["technical considerations for team placement"],
        "growth_trajectory": "likely technical growth path if hired",
        "risk_factors": ["technical risks if we hire this person"]
    }}
}}

Be extremely critical and specific. Question everything. Provide evidence-based assessments only.
Respond ONLY with JSON.
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
                raw_text=resume_data.get('raw_text', '')[:3000]  # More raw text for technical analysis
            )
            
            # Generate insights using the LLM
            response = self.llm(messages)
            
            # Parse the response
            insights = self.output_parser.parse(response.content)
            
            # Add metadata
            insights['generated_at'] = datetime.now().isoformat()
            insights['model_used'] = 'llama3-70b-8192'
            insights['analysis_type'] = 'technical_deep_dive'
            insights['reviewer_level'] = 'principal_engineer'
            
            return {
                'success': True,
                'technical_assessment': insights
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to generate technical assessment: {str(e)}'
            }
    

# Global service instance
resume_insights_service = ResumeInsightsService()
