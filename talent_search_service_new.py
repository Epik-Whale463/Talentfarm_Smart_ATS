# Enhanced Talent Search Service - Hallucination-Free Candidate Search with RAG
import json
import re
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from models import db, Resume, User, Application, Job
from auth import require_auth
from mistral_service import get_mistral_client
from rag_service import rag_service
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

talent_search_bp = Blueprint('talent_search', __name__)

class EnhancedTalentSearchService:
    def __init__(self):
        self.client = get_mistral_client()
        self.conversation_history = {}
        
    def extract_requirements(self, query: str, conversation_history: List[Dict] = None) -> Dict:
        """Extract structured requirements with enhanced validation and anti-hallucination measures"""
        
        # Build context from conversation history
        context = ""
        if conversation_history:
            context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]])
        
        prompt = f"""
You are an AI assistant helping HR professionals search for candidates. Your job is to extract ONLY the information explicitly mentioned in the query. DO NOT infer, assume, or add information that is not clearly stated.

STRICT RULES:
1. Only extract information that is explicitly mentioned
2. Use "not_specified" for missing information
3. Be conservative - if uncertain, mark as "not_specified"
4. Do not make assumptions about salary, company size, or other details not mentioned
5. Extract skills exactly as mentioned, without adding synonyms or related skills

Conversation history:
{context}

Current query: {query}

Extract ONLY the explicitly mentioned information:

Respond in this EXACT JSON format:
{{
    "job_title": "string or not_specified",
    "skills_required": ["only explicitly mentioned skills"],
    "experience_years": {{"min": "number or not_specified", "max": "number or not_specified"}},
    "education_level": "string or not_specified",
    "location": "string or not_specified", 
    "industry": "string or not_specified",
    "company_size": "not_specified",
    "remote_work": "boolean or not_specified",
    "technologies": ["only explicitly mentioned technologies"],
    "certifications": ["only explicitly mentioned certifications"],
    "confidence": "number between 0-1 based on query clarity",
    "missing_info": ["list of important missing information"],
    "follow_up_questions": ["max 3 specific questions to clarify requirements"]
}}

EXAMPLE - if query is "Find Python developers":
- job_title: "Python Developer" 
- skills_required: ["Python"]
- everything else: "not_specified"
"""

        try:
            response = self.client.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Very low temperature for consistency
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate and clean the result
            validated_result = self._validate_extracted_requirements(result, query)
            return validated_result
            
        except Exception as e:
            logger.error(f"Error extracting requirements: {e}")
            return {
                "job_title": "not_specified",
                "skills_required": [],
                "experience_years": {"min": "not_specified", "max": "not_specified"},
                "education_level": "not_specified",
                "location": "not_specified",
                "industry": "not_specified",
                "company_size": "not_specified",
                "remote_work": "not_specified",
                "technologies": [],
                "certifications": [],
                "confidence": 0.0,
                "missing_info": ["Unable to process query"],
                "follow_up_questions": ["Could you please rephrase your requirements more clearly?"]
            }
    
    def _validate_extracted_requirements(self, result: Dict, original_query: str) -> Dict:
        """Validate extracted requirements to prevent hallucination"""
        
        try:
            # Clean skills - only keep if they appear in the original query
            original_lower = original_query.lower()
            
            if 'skills_required' in result:
                validated_skills = []
                for skill in result['skills_required']:
                    if isinstance(skill, str) and skill.lower() in original_lower:
                        validated_skills.append(skill)
                result['skills_required'] = validated_skills
            
            if 'technologies' in result:
                validated_tech = []
                for tech in result['technologies']:
                    if isinstance(tech, str) and tech.lower() in original_lower:
                        validated_tech.append(tech)
                result['technologies'] = validated_tech
            
            # Validate job title - must be mentioned in query
            if 'job_title' in result and result['job_title'] != "not_specified":
                job_title = result['job_title'].lower()
                if job_title not in original_lower:
                    result['job_title'] = "not_specified"
            
            # Ensure confidence is reasonable
            confidence = result.get('confidence', 0.0)
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                result['confidence'] = 0.0
            
            # Clean follow-up questions
            follow_ups = result.get('follow_up_questions', [])
            if not isinstance(follow_ups, list):
                result['follow_up_questions'] = []
            else:
                result['follow_up_questions'] = follow_ups[:3]  # Max 3 questions
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating requirements: {e}")
            return result
    
    def search_candidates(self, query: str) -> Dict[str, Any]:
        """
        Main candidate search function with enhanced validation and anti-hallucination measures
        """
        try:
            logger.info(f"Starting candidate search for query: {query}")
            
            # Step 1: Extract and validate requirements from query
            requirements = self.extract_requirements(query)
            if not requirements or not any(requirements.values()):
                return {
                    'success': False,
                    'error': 'Could not extract valid requirements from your query. Please be more specific.',
                    'query': query
                }
            
            logger.info(f"Extracted requirements: {requirements}")
            
            # Step 2: Enhanced semantic search with strict validation
            search_results = rag_service.enhanced_semantic_search(query, requirements, top_k=15)
            
            if not search_results:
                return {
                    'success': True,
                    'candidates': [],
                    'message': 'No candidates found matching your criteria.',
                    'requirements': requirements,
                    'query': query
                }
            
            # Step 3: Get verified candidate data (NO HALLUCINATION)
            candidate_ids = [result['resume_id'] for result in search_results]
            verified_candidates = rag_service.bulk_get_verified_candidates(candidate_ids)
            
            # Step 4: Match scores with verified data and additional validation
            final_candidates = []
            for search_result in search_results:
                # Find matching verified candidate
                verified_candidate = next(
                    (c for c in verified_candidates if c['resume_id'] == search_result['resume_id']), 
                    None
                )
                
                if verified_candidate and 'error' not in verified_candidate:
                    # Additional validation - ensure minimum data quality
                    if self._validate_candidate_quality(verified_candidate, requirements):
                        # Combine search scores with verified data
                        candidate_data = {
                            **verified_candidate,
                            'search_score': search_result['final_score'],
                            'match_details': {
                                'avg_score': search_result['avg_score'],
                                'match_count': search_result['match_count'],
                                'skill_matches': search_result['skill_matches'],
                                'experience_matches': search_result['experience_matches'],
                                'diversity_score': search_result['diversity_score']
                            },
                            'relevance_explanation': self._generate_relevance_explanation(verified_candidate, requirements)
                        }
                        final_candidates.append(candidate_data)
                    else:
                        logger.info(f"Candidate {search_result['resume_id']} filtered out due to quality validation")
            
            # Step 5: Generate verified response (only based on actual data)
            response = self.generate_verified_response(query, final_candidates, requirements)
            
            return {
                'success': True,
                'candidates': final_candidates,
                'response': response,
                'requirements': requirements,
                'query': query,
                'total_found': len(final_candidates),
                'search_metadata': {
                    'initial_results': len(search_results),
                    'verified_candidates': len(verified_candidates),
                    'final_candidates': len(final_candidates),
                    'quality_filtered': len(search_results) - len(final_candidates)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in candidate search: {e}")
            return {
                'success': False,
                'error': f'Search failed: {str(e)}',
                'query': query
            }
    
    def _validate_candidate_quality(self, candidate: Dict, requirements: Dict) -> bool:
        """
        Validate candidate data quality and relevance to prevent low-quality results
        """
        try:
            # Must have basic information
            if not candidate.get('name') or not candidate.get('resume_id'):
                return False
            
            # Must have some contact information
            if not (candidate.get('email') or candidate.get('phone')):
                return False
            
            # Must have skills OR experience OR education
            has_skills = len(candidate.get('skills', [])) > 0
            has_experience = len(candidate.get('experience', [])) > 0
            has_education = len(candidate.get('education', [])) > 0
            
            if not (has_skills or has_experience or has_education):
                return False
            
            # Check minimum relevance to requirements
            if requirements.get('skills_required'):
                required_skills = [skill.lower().strip() for skill in requirements['skills_required']]
                candidate_skills = [skill.lower().strip() for skill in candidate.get('skills', [])]
                
                # Must have at least one matching skill or substantial experience
                has_skill_match = any(
                    any(req_skill in cand_skill for req_skill in required_skills) 
                    for cand_skill in candidate_skills
                )
                
                # Or relevant experience
                has_experience_match = False
                if candidate.get('experience'):
                    for exp in candidate['experience']:
                        exp_text = (exp.get('title', '') + ' ' + exp.get('description', '')).lower()
                        if any(req_skill in exp_text for req_skill in required_skills):
                            has_experience_match = True
                            break
                
                if not (has_skill_match or has_experience_match):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating candidate quality: {e}")
            return False
    
    def _generate_relevance_explanation(self, candidate: Dict, requirements: Dict) -> str:
        """
        Generate a factual explanation of why this candidate is relevant
        """
        try:
            explanations = []
            
            # Skills matching
            if requirements.get('skills_required') and candidate.get('skills'):
                required_skills = [skill.lower().strip() for skill in requirements['skills_required']]
                candidate_skills = candidate.get('skills', [])
                
                matching_skills = []
                for cand_skill in candidate_skills:
                    for req_skill in required_skills:
                        if req_skill in cand_skill.lower():
                            matching_skills.append(cand_skill)
                            break
                
                if matching_skills:
                    explanations.append(f"Has {len(matching_skills)} relevant skills: {', '.join(matching_skills[:3])}")
            
            # Experience matching
            if requirements.get('experience_years') and candidate.get('experience'):
                exp_count = len(candidate['experience'])
                if exp_count > 0:
                    explanations.append(f"Has {exp_count} work experience entries")
            
            # Education matching
            if requirements.get('education_level') and candidate.get('education'):
                edu_count = len(candidate['education'])
                if edu_count > 0:
                    explanations.append(f"Has {edu_count} education qualifications")
            
            return "; ".join(explanations) if explanations else "Candidate profile matches search criteria"
            
        except Exception as e:
            logger.error(f"Error generating relevance explanation: {e}")
            return "Relevant candidate found"
    
    def generate_verified_response(self, query: str, candidates: List[Dict], requirements: Dict) -> str:
        """Generate response with strict verification to prevent hallucination"""
        
        try:
            if not candidates:
                return self._generate_no_results_response(requirements, query)
            
            # Verify all candidate data before generating response
            verified_candidates = []
            for candidate in candidates[:5]:  # Top 5 only
                # Double-check data exists and is valid
                if self._verify_response_data(candidate):
                    verified_candidates.append(candidate)
            
            if not verified_candidates:
                return "I found some potential matches, but the candidate data needs verification. Please check the candidate cards below for accurate information."
            
            # Build verified response
            response_parts = []
            
            # Summary with exact numbers
            total_verified = len(verified_candidates)
            response_parts.append(f"I found {total_verified} verified candidate{'s' if total_verified != 1 else ''} matching your requirements.")
            
            # Add requirement context (only what was actually specified)
            req_context = self._build_requirement_context(requirements)
            if req_context:
                response_parts.append(f"Based on your search for: {req_context}")
            
            # Highlight top candidates with verified data only
            if verified_candidates:
                top_candidate = verified_candidates[0]
                name = top_candidate.get('name', 'Unknown')
                
                # Only mention verified skills/experience
                highlights = []
                
                verified_skills = top_candidate.get('skills', [])
                if verified_skills and len(verified_skills) > 0:
                    skill_count = min(len(verified_skills), 3)
                    highlights.append(f"{skill_count} relevant skills")
                
                verified_experience = top_candidate.get('experience', [])
                if verified_experience and len(verified_experience) > 0:
                    highlights.append(f"{len(verified_experience)} work experience entries")
                
                if highlights:
                    response_parts.append(f"The top match is {name} with {' and '.join(highlights)}.")
            
            # Add guidance for next steps
            response_parts.append("Please review the candidate cards below for complete details. Click on any candidate to view their full profile.")
            
            # Add verification note
            response_parts.append("All data shown has been verified from actual resume uploads.")
            
            return " ".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error generating verified response: {e}")
            return "I found some candidates for you. Please review the candidate information below for accurate details."
    
    def _verify_response_data(self, candidate: Dict) -> bool:
        """Verify candidate data is suitable for response generation"""
        
        try:
            # Must have basic information
            if not candidate.get('name') or candidate['name'] in ['Unknown', 'Not provided']:
                return False
            
            # Must have valid resume ID
            if not candidate.get('resume_id') or not isinstance(candidate['resume_id'], int):
                return False
            
            # Must have at least one verifiable data point
            has_skills = candidate.get('skills') and len(candidate['skills']) > 0
            has_experience = candidate.get('experience') and len(candidate['experience']) > 0
            has_education = candidate.get('education') and len(candidate['education']) > 0
            
            if not (has_skills or has_experience or has_education):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying response data: {e}")
            return False
    
    def _build_requirement_context(self, requirements: Dict) -> str:
        """Build requirement context string from only specified requirements"""
        
        try:
            context_parts = []
            
            # Job title
            if requirements.get('job_title') and requirements['job_title'] != 'not_specified':
                context_parts.append(f"{requirements['job_title']} role")
            
            # Skills
            skills = requirements.get('skills_required', [])
            if skills:
                if len(skills) == 1:
                    context_parts.append(f"with {skills[0]} skills")
                elif len(skills) <= 3:
                    context_parts.append(f"with {', '.join(skills)} skills")
                else:
                    context_parts.append(f"with {', '.join(skills[:3])} and {len(skills)-3} more skills")
            
            # Experience
            exp_years = requirements.get('experience_years', {})
            if exp_years.get('min') != 'not_specified':
                min_exp = exp_years.get('min')
                if isinstance(min_exp, (int, float)):
                    context_parts.append(f"{min_exp}+ years experience")
            
            return ', '.join(context_parts)
            
        except Exception as e:
            logger.error(f"Error building requirement context: {e}")
            return ""
    
    def _generate_no_results_response(self, requirements: Dict, query: str) -> str:
        """Generate response when no candidates are found"""
        
        try:
            req_context = self._build_requirement_context(requirements)
            
            if req_context:
                return f"I couldn't find any candidates matching your specific requirements for {req_context}. You might want to try broadening your search criteria or consider similar skills and experience levels."
            else:
                return "I couldn't find any candidates matching your search. Please try refining your requirements or using different keywords."
                
        except Exception as e:
            logger.error(f"Error generating no results response: {e}")
            return "No candidates found matching your criteria. Please try a different search."

# Initialize enhanced talent search service
talent_search_service = EnhancedTalentSearchService()

# Routes
@talent_search_bp.route('/search', methods=['POST'])
@require_auth
def enhanced_talent_search():
    """Enhanced main endpoint for natural language talent search with anti-hallucination"""
    
    try:
        # Get user ID from request context (set by require_auth decorator)
        user_id = getattr(request, 'current_user_id', None)
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
            
        current_user = User.query.get(user_id)
        if not current_user or current_user.role != 'hr':
            return jsonify({'error': 'HR access required'}), 403
        
        data = request.get_json()
        query = data.get('query', '').strip()
        conversation_id = data.get('conversation_id', 'default')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Get conversation history
        conversation_history = talent_search_service.conversation_history.get(conversation_id, [])
        
        # Add user query to history
        conversation_history.append({
            'role': 'user',
            'content': query,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Perform enhanced search
        search_result = talent_search_service.search_candidates(query)
        
        if not search_result['success']:
            return jsonify({
                'success': False,
                'error': search_result.get('error', 'Search failed'),
                'conversation_id': conversation_id
            }), 400
        
        # Format candidates for response
        formatted_candidates = []
        for candidate in search_result['candidates']:
            formatted_candidate = {
                'id': candidate['resume_id'],
                'name': candidate['name'],
                'email': candidate['email'],
                'phone': candidate['phone'],
                'skills': candidate['skills'][:10],  # Top 10 skills
                'experience_summary': candidate['experience'][:2],  # Top 2 experiences
                'education_summary': candidate['education'][:1],  # Latest education
                'match_score': round(candidate['search_score'] * 100, 1),
                'match_details': candidate['match_details'],
                'relevance_explanation': candidate['relevance_explanation'],
                'data_completeness': candidate['data_completeness'],
                'filename': candidate['filename'],
                'upload_date': candidate['upload_date']
            }
            formatted_candidates.append(formatted_candidate)
        
        # Add AI response to history
        conversation_history.append({
            'role': 'assistant',
            'content': search_result['response'],
            'timestamp': datetime.utcnow().isoformat(),
            'candidates_count': len(formatted_candidates)
        })
        
        # Update conversation history
        talent_search_service.conversation_history[conversation_id] = conversation_history[-10:]  # Keep last 10 messages
        
        return jsonify({
            'success': True,
            'response': search_result['response'],
            'candidates': formatted_candidates,
            'requirements': search_result['requirements'],
            'query': query,
            'conversation_id': conversation_id,
            'total_found': search_result['total_found'],
            'search_metadata': search_result['search_metadata']
        })
        
    except Exception as e:
        logger.error(f"Error in enhanced talent search: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@talent_search_bp.route('/rag/status', methods=['GET'])
@require_auth
def rag_status():
    """Get RAG system status and collection stats"""
    
    try:
        user_id = getattr(request, 'current_user_id', None)
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
            
        current_user = User.query.get(user_id)
        if not current_user or current_user.role != 'hr':
            return jsonify({'error': 'HR access required'}), 403
        
        # Get collection stats
        stats = rag_service.get_collection_stats()
        
        # Get database counts for comparison
        total_resumes = Resume.query.count()
        total_jobs = Job.query.count()
        
        return jsonify({
            'success': True,
            'database_counts': {
                'resumes': total_resumes,
                'jobs': total_jobs
            },
            'vector_database': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting RAG status: {e}")
        return jsonify({'error': 'Failed to get RAG status'}), 500

@talent_search_bp.route('/sync-resume/<int:resume_id>', methods=['POST'])
@require_auth
def sync_single_resume(resume_id):
    """Sync a single resume to vector database"""
    
    try:
        user_id = getattr(request, 'current_user_id', None)
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
            
        current_user = User.query.get(user_id)
        if not current_user or current_user.role != 'hr':
            return jsonify({'error': 'HR access required'}), 403
        
        # Get resume
        resume = Resume.query.get_or_404(resume_id)
        
        # Sync the resume
        result = rag_service.index_single_resume(resume)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'resume_id': resume_id
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'resume_id': resume_id
            }), 500
            
    except Exception as e:
        logger.error(f"Error syncing single resume: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@talent_search_bp.route('/force-sync', methods=['POST'])
@require_auth
def force_sync_all():
    """Force synchronization of all data to vector database"""
    try:
        user_id = getattr(request, 'current_user_id', None)
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
            
        current_user = User.query.get(user_id)
        if not current_user or current_user.role != 'hr':
            return jsonify({'error': 'HR access required'}), 403
        
        # Get all resumes and jobs
        resumes = Resume.query.all()
        jobs = Job.query.all()
        
        results = {
            'resumes': {'success': 0, 'failed': 0},
            'jobs': {'success': 0, 'failed': 0}
        }
        
        # Sync all resumes
        for resume in resumes:
            try:
                result = rag_service.index_single_resume(resume)
                if result['success']:
                    results['resumes']['success'] += 1
                else:
                    results['resumes']['failed'] += 1
            except Exception as e:
                logger.error(f"Error syncing resume {resume.id}: {e}")
                results['resumes']['failed'] += 1
        
        # Sync all jobs (if implemented)
        for job in jobs:
            try:
                # Use existing auto_sync_job if available
                success = rag_service.auto_sync_job(job, 'create')
                if success:
                    results['jobs']['success'] += 1
                else:
                    results['jobs']['failed'] += 1
            except Exception as e:
                logger.error(f"Error syncing job {job.id}: {e}")
                results['jobs']['failed'] += 1
        
        return jsonify({
            'success': True,
            'message': 'Force sync completed',
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in force sync: {e}")
        return jsonify({'error': 'Failed to sync data'}), 500
