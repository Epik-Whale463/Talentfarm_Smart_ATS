# RAG Service for Talent Search using LangChain + Groq + Qdrant
import os
import json
import uuid
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from models import Resume, User, Application, Job
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGTalentSearchService:
    def __init__(self):
        # Initialize Groq LLM
        self.llm = ChatGroq(
            groq_api_key=Config.GROQ_API_KEY,
            model_name="llama3-70b-8192",
            temperature=0.1,
            max_tokens=1024
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            url=os.getenv('QDRANT_URL', 'http://localhost:6333'),
            api_key=os.getenv('QDRANT_API_KEY')  # Optional for local setup
        )
        
        # Collection name for candidate resumes
        self.collection_name = "candidate_resumes"
        
        # Initialize collection
        self._initialize_collection()
        
        # Text splitter for chunking resume content
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        self.conversation_history = {}
    
    def _initialize_collection(self):
        """Initialize Qdrant collection for candidate resumes"""
        try:
            # Get embedding dimension
            sample_embedding = self.embedding_model.encode("sample text")
            vector_size = len(sample_embedding)
            
            # Check if collection exists
            collections = self.qdrant_client.get_collections().collections
            collection_exists = any(col.name == self.collection_name for col in collections)
            
            if not collection_exists:
                # Create collection
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error initializing Qdrant collection: {e}")
    
    def index_candidate_resume(self, resume: Resume):
        """Index a candidate resume in Qdrant vector database"""
        try:
            # Prepare resume text for embedding
            resume_text = self._prepare_resume_text(resume)
            
            # Split text into chunks
            text_chunks = self.text_splitter.split_text(resume_text)
            
            # Generate embeddings and store in Qdrant
            points = []
            for i, chunk in enumerate(text_chunks):
                embedding = self.embedding_model.encode(chunk).tolist()
                
                point_id = f"{resume.id}_{i}"
                
                payload = {
                    "resume_id": resume.id,
                    "chunk_index": i,
                    "text": chunk,
                    "candidate_name": resume.name,
                    "candidate_email": resume.email,
                    "candidate_phone": resume.phone,
                    "skills": resume.skills or [],
                    "experience": resume.experience or [],
                    "education": resume.education or [],
                    "filename": resume.filename,
                    "created_at": resume.created_at.isoformat()
                }
                
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                )
            
            # Upload points to Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Indexed resume {resume.id} with {len(text_chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error indexing resume {resume.id}: {e}")
    
    def _prepare_resume_text(self, resume: Resume) -> str:
        """Prepare comprehensive text from resume for embedding"""
        text_parts = []
        
        # Add basic info
        if resume.name:
            text_parts.append(f"Name: {resume.name}")
        if resume.email:
            text_parts.append(f"Email: {resume.email}")
        if resume.phone:
            text_parts.append(f"Phone: {resume.phone}")
        
        # Add skills
        if resume.skills:
            skills_text = "Skills: " + ", ".join(resume.skills)
            text_parts.append(skills_text)
        
        # Add experience
        if resume.experience:
            for exp in resume.experience:
                if isinstance(exp, dict):
                    exp_text = f"Experience: {exp.get('title', '')} at {exp.get('company', '')}"
                    if exp.get('duration'):
                        exp_text += f" ({exp['duration']})"
                    if exp.get('description'):
                        exp_text += f" - {exp['description']}"
                    text_parts.append(exp_text)
        
        # Add education
        if resume.education:
            for edu in resume.education:
                if isinstance(edu, dict):
                    edu_text = f"Education: {edu.get('degree', '')} from {edu.get('institution', '')}"
                    if edu.get('year'):
                        edu_text += f" ({edu['year']})"
                    text_parts.append(edu_text)
        
        # Add raw text if available
        if resume.raw_text:
            text_parts.append(f"Additional Information: {resume.raw_text[:1000]}")  # Limit raw text
        
        return "\n".join(text_parts)
    
    def index_all_resumes(self):
        """Index all resumes in the database"""
        try:
            # Clear existing collection
            self.qdrant_client.delete_collection(self.collection_name)
            self._initialize_collection()
            
            # Get all resumes
            resumes = Resume.query.all()
            
            for resume in resumes:
                if resume.parsed_data:  # Only index parsed resumes
                    self.index_candidate_resume(resume)
            
            logger.info(f"Indexed {len(resumes)} resumes")
            
        except Exception as e:
            logger.error(f"Error indexing all resumes: {e}")
    
    def extract_search_requirements(self, query: str, conversation_history: List[Dict] = None) -> Dict:
        """Extract structured requirements from natural language query using Groq Llama"""
        
        # Build context from conversation history
        context = ""
        if conversation_history:
            context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]])
        
        system_prompt = """You are an AI assistant helping HR professionals search for candidates. 
        Analyze the query and extract structured search requirements in JSON format.
        
        Extract the following information:
        1. Job title/role
        2. Required skills (technical and soft skills)
        3. Experience level (in years)
        4. Education requirements
        5. Location preferences
        6. Industry experience
        7. Company size preference (startup, mid-size, enterprise)
        8. Remote work requirements
        9. Specific technologies/tools
        10. Certifications needed
        
        Also determine:
        - Confidence level (how specific is the query?)
        - Missing information that should be clarified
        - Suggested follow-up questions to improve search accuracy
        
        Respond ONLY with valid JSON in this exact format:
        {
            "requirements": {
                "job_title": "string or null",
                "required_skills": ["skill1", "skill2"],
                "experience_years": {"min": number, "max": number},
                "education_level": "string or null",
                "location": "string or null",
                "industry": "string or null",
                "company_size": "string or null",
                "remote_work": "boolean or null",
                "technologies": ["tech1", "tech2"],
                "certifications": ["cert1", "cert2"]
            },
            "confidence": 0.0-1.0,
            "missing_info": ["missing1", "missing2"],
            "follow_up_questions": ["question1", "question2"]
        }"""
        
        user_prompt = f"""
        Conversation history:
        {context}
        
        Current query: {query}
        
        Extract search requirements from this query:"""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Parse JSON response
            result = json.loads(response.content)
            return result
            
        except Exception as e:
            logger.error(f"Error extracting requirements with Groq: {e}")
            return {
                "requirements": {},
                "confidence": 0.0,
                "missing_info": [],
                "follow_up_questions": ["Could you provide more details about the specific skills required?"]
            }
    
    def semantic_search_candidates(self, query: str, requirements: Dict, limit: int = 5) -> List[Dict]:
        """Perform semantic search for candidates using RAG"""
        try:
            # Create search query from requirements
            search_query = self._build_search_query(query, requirements)
            
            # Generate embedding for the search query
            query_embedding = self.embedding_model.encode(search_query).tolist()
            
            # Search in Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit * 3,  # Get more results to deduplicate by resume_id
                score_threshold=0.3
            )
            
            # Group results by resume_id and calculate aggregate scores
            resume_scores = {}
            resume_data = {}
            
            for result in search_results:
                resume_id = result.payload['resume_id']
                score = result.score
                
                if resume_id not in resume_scores:
                    resume_scores[resume_id] = []
                    resume_data[resume_id] = result.payload
                
                resume_scores[resume_id].append(score)
            
            # Calculate final scores and rank candidates
            final_candidates = []
            for resume_id, scores in resume_scores.items():
                # Use max score with bonus for multiple matches
                final_score = max(scores) + (len(scores) - 1) * 0.1
                
                payload = resume_data[resume_id]
                final_candidates.append({
                    'resume_id': resume_id,
                    'score': final_score,
                    'payload': payload,
                    'match_count': len(scores)
                })
            
            # Sort by final score
            final_candidates.sort(key=lambda x: x['score'], reverse=True)
            
            # Return top candidates
            return final_candidates[:limit]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def _build_search_query(self, original_query: str, requirements: Dict) -> str:
        """Build an enhanced search query from requirements"""
        query_parts = [original_query]
        
        req = requirements
        
        if req.get('job_title'):
            query_parts.append(f"Job title: {req['job_title']}")
        
        if req.get('required_skills'):
            query_parts.append(f"Skills: {', '.join(req['required_skills'])}")
        
        if req.get('technologies'):
            query_parts.append(f"Technologies: {', '.join(req['technologies'])}")
        
        if req.get('experience_years'):
            exp = req['experience_years']
            if exp.get('min'):
                query_parts.append(f"Experience: {exp['min']}+ years")
        
        if req.get('education_level'):
            query_parts.append(f"Education: {req['education_level']}")
        
        if req.get('industry'):
            query_parts.append(f"Industry: {req['industry']}")
        
        return " ".join(query_parts)
    
    def generate_candidate_analysis(self, candidate_data: Dict, requirements: Dict, original_query: str) -> Dict:
        """Generate detailed analysis of candidate match using Groq Llama"""
        
        system_prompt = """You are an expert HR analyst. Analyze how well a candidate matches the job requirements.
        
        Provide analysis in JSON format with:
        1. Overall match score (0-100)
        2. Strengths (what makes them a good fit)
        3. Gaps (what they're missing)
        4. Skills match analysis
        5. Experience match analysis
        6. Recommendation (hire/interview/pass)
        
        Be thorough but concise."""
        
        user_prompt = f"""
        Original Search Query: {original_query}
        
        Job Requirements:
        {json.dumps(requirements, indent=2)}
        
        Candidate Information:
        Name: {candidate_data.get('candidate_name', 'Unknown')}
        Email: {candidate_data.get('candidate_email', 'Unknown')}
        Skills: {candidate_data.get('skills', [])}
        Experience: {candidate_data.get('experience', [])}
        Education: {candidate_data.get('education', [])}
        
        Analyze this candidate's fit for the role and respond with JSON:
        {
            "overall_match_score": 0-100,
            "strengths": ["strength1", "strength2"],
            "gaps": ["gap1", "gap2"],
            "skills_analysis": "detailed analysis",
            "experience_analysis": "detailed analysis",
            "recommendation": "hire/interview/pass",
            "reasoning": "explanation of the recommendation"
        }"""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            result = json.loads(response.content)
            return result
            
        except Exception as e:
            logger.error(f"Error generating candidate analysis: {e}")
            return {
                "overall_match_score": 50,
                "strengths": ["Candidate found in search results"],
                "gaps": ["Analysis unavailable"],
                "skills_analysis": "Unable to analyze",
                "experience_analysis": "Unable to analyze",
                "recommendation": "review",
                "reasoning": "Analysis failed, manual review recommended"
            }
    
    def search_candidates_with_rag(self, query: str, conversation_history: List[Dict] = None) -> Dict:
        """Main RAG search function that combines all components"""
        try:
            # Extract requirements from query
            extraction_result = self.extract_search_requirements(query, conversation_history)
            requirements = extraction_result.get('requirements', {})
            confidence = extraction_result.get('confidence', 0.0)
            follow_up_questions = extraction_result.get('follow_up_questions', [])
            
            candidates = []
            
            if confidence > 0.3:  # Lower threshold for semantic search
                # Perform semantic search
                search_results = self.semantic_search_candidates(query, requirements, limit=5)
                
                # Generate detailed analysis for each candidate
                for result in search_results:
                    candidate_analysis = self.generate_candidate_analysis(
                        result['payload'], 
                        requirements, 
                        query
                    )
                    
                    candidates.append({
                        'resume_id': result['resume_id'],
                        'name': result['payload'].get('candidate_name'),
                        'email': result['payload'].get('candidate_email'),
                        'phone': result['payload'].get('candidate_phone'),
                        'skills': result['payload'].get('skills', []),
                        'experience': result['payload'].get('experience', []),
                        'education': result['payload'].get('education', []),
                        'filename': result['payload'].get('filename'),
                        'semantic_score': round(result['score'] * 100, 1),
                        'match_analysis': candidate_analysis,
                        'match_count': result['match_count']
                    })
            
            # Generate AI response using Groq
            ai_response = self._generate_ai_response(query, candidates, confidence, requirements)
            
            return {
                'success': True,
                'ai_response': ai_response,
                'candidates': candidates,
                'follow_up_questions': follow_up_questions,
                'requirements_extracted': requirements,
                'confidence': confidence,
                'search_summary': {
                    'total_candidates_searched': self._get_total_candidates_count(),
                    'matches_found': len(candidates),
                    'search_confidence': confidence,
                    'search_method': 'semantic_rag'
                }
            }
            
        except Exception as e:
            logger.error(f"Error in RAG search: {e}")
            return {
                'success': False,
                'error': str(e),
                'ai_response': 'I encountered an error while searching. Please try again.',
                'candidates': [],
                'follow_up_questions': ['Could you rephrase your search query?'],
                'requirements_extracted': {},
                'confidence': 0.0
            }
    
    def _generate_ai_response(self, query: str, candidates: List[Dict], confidence: float, requirements: Dict) -> str:
        """Generate contextual AI response using Groq"""
        
        if candidates:
            if len(candidates) == 1:
                response = f"Great! I found 1 excellent candidate that matches your requirements for '{query}'."
            else:
                response = f"Excellent! I found {len(candidates)} strong candidates that match your search for '{query}'. Here are the top matches ranked by relevance:"
        elif confidence > 0.4:
            response = f"I understand you're looking for '{query}', but I couldn't find candidates that closely match these specific requirements. You might want to broaden your criteria or try different keywords."
        else:
            response = f"I'd love to help you find the perfect candidate for '{query}'! Let me ask a few questions to better understand your requirements and improve the search results."
        
        return response
    
    def _get_total_candidates_count(self) -> int:
        """Get total number of candidates in the system"""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return collection_info.points_count
        except:
            return Resume.query.count()

# Initialize RAG service
rag_talent_search_service = RAGTalentSearchService()
