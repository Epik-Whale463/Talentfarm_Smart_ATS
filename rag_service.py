# RAG Service for Talent Search - Qdrant Vector Database Integration
import json
import uuid
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import numpy as np

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, Range, MatchValue
from sentence_transformers import SentenceTransformer
import re

from models import Resume, Job, db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGTalentService:
    def __init__(self):
        """Initialize RAG service with Qdrant and SentenceTransformers"""
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            url="https://222f8841-7574-4680-85ca-696426f82250.europe-west3-0.gcp.cloud.qdrant.io:6333", 
            api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.Gd5vuQE4uY1n4Uqts7tHBzPfPzKOvNlmLojb0Rd9rm0",
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dimension = 384  # Dimension for all-MiniLM-L6-v2
        
        # Collection names
        self.collections = {
            'resumes': 'talent_resumes',
            'skills': 'talent_skills', 
            'experience': 'talent_experience',
            'education': 'talent_education',
            'jobs': 'talent_jobs'  # Add jobs collection for job matching
        }
        
        # Initialize collections
        self._initialize_collections()
        
    def _initialize_collections(self):
        """Create Qdrant collections if they don't exist"""
        
        try:
            # Get existing collections
            existing_collections = {col.name for col in self.qdrant_client.get_collections().collections}
            
            # Create collections that don't exist
            for collection_name in self.collections.values():
                if collection_name not in existing_collections:
                    self.qdrant_client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=self.embedding_dimension,
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"Created collection: {collection_name}")
                else:
                    logger.info(f"Collection already exists: {collection_name}")
                    
        except Exception as e:
            logger.error(f"Error initializing collections: {e}")
            
    def chunk_resume_text(self, resume: Resume) -> List[Dict]:
        """Break resume into semantic chunks for better retrieval"""
        
        chunks = []
        
        # Full resume chunk (for general search)
        if resume.raw_text:
            chunks.append({
                'text': resume.raw_text,
                'type': 'full_resume',
                'metadata': {
                    'resume_id': resume.id,
                    'name': resume.name,
                    'email': resume.email,
                    'phone': resume.phone or '',
                    'filename': resume.filename
                }
            })
        
        # Skills chunks
        if resume.skills and isinstance(resume.skills, list):
            skills_text = ' '.join(str(skill) for skill in resume.skills)
            chunks.append({
                'text': f"Skills and Technologies: {skills_text}",
                'type': 'skills',
                'metadata': {
                    'resume_id': resume.id,
                    'name': resume.name or 'Unknown',
                    'skills': resume.skills,
                    'skills_count': len(resume.skills)
                }
            })
        
        # Experience chunks (each job separately)
        if resume.experience and isinstance(resume.experience, list):
            for i, exp in enumerate(resume.experience):
                if isinstance(exp, dict):
                    exp_text_parts = []
                    
                    if exp.get('title'):
                        exp_text_parts.append(f"Position: {exp['title']}")
                    if exp.get('company'):
                        exp_text_parts.append(f"Company: {exp['company']}")
                    if exp.get('duration'):
                        exp_text_parts.append(f"Duration: {exp['duration']}")
                    if exp.get('description'):
                        exp_text_parts.append(f"Description: {exp['description']}")
                    
                    if exp_text_parts:
                        chunks.append({
                            'text': ' | '.join(exp_text_parts),
                            'type': 'experience',
                            'metadata': {
                                'resume_id': resume.id,
                                'name': resume.name or 'Unknown',
                                'job_title': exp.get('title', ''),
                                'company': exp.get('company', ''),
                                'duration': exp.get('duration', ''),
                                'experience_index': i
                            }
                        })
        
        # Education chunks
        if resume.education and isinstance(resume.education, list):
            for i, edu in enumerate(resume.education):
                if isinstance(edu, dict):
                    edu_text_parts = []
                    
                    if edu.get('degree'):
                        edu_text_parts.append(f"Degree: {edu['degree']}")
                    if edu.get('institution'):
                        edu_text_parts.append(f"Institution: {edu['institution']}")
                    if edu.get('year'):
                        edu_text_parts.append(f"Year: {edu['year']}")
                    if edu.get('grade'):
                        edu_text_parts.append(f"Grade: {edu['grade']}")
                    
                    if edu_text_parts:
                        chunks.append({
                            'text': ' | '.join(edu_text_parts),
                            'type': 'education',
                            'metadata': {
                                'resume_id': resume.id,
                                'name': resume.name or 'Unknown',
                                'degree': edu.get('degree', ''),
                                'institution': edu.get('institution', ''),
                                'year': edu.get('year', ''),
                                'education_index': i
                            }
                        })
        
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        try:
            embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return np.array([])
    
    def index_resume(self, resume: Resume) -> bool:
        """Index a single resume into Qdrant collections"""
        
        try:
            # Generate chunks
            chunks = self.chunk_resume_text(resume)
            
            if not chunks:
                logger.warning(f"No chunks generated for resume {resume.id}")
                return False
            
            # Prepare points for each collection
            points_by_collection = {collection: [] for collection in self.collections.values()}
            
            for chunk in chunks:
                # Generate embedding
                embedding = self.generate_embeddings([chunk['text']])[0]
                
                # Create point
                point_id = str(uuid.uuid4())
                point = PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload={
                        'text': chunk['text'],
                        'type': chunk['type'],
                        **chunk['metadata'],
                        'indexed_at': datetime.utcnow().isoformat()
                    }
                )
                
                # Add to appropriate collection
                if chunk['type'] == 'full_resume':
                    points_by_collection[self.collections['resumes']].append(point)
                elif chunk['type'] == 'skills':
                    points_by_collection[self.collections['skills']].append(point)
                elif chunk['type'] == 'experience':
                    points_by_collection[self.collections['experience']].append(point)
                elif chunk['type'] == 'education':
                    points_by_collection[self.collections['education']].append(point)
            
            # Insert points into collections
            for collection_name, points in points_by_collection.items():
                if points:
                    self.qdrant_client.upsert(
                        collection_name=collection_name,
                        points=points
                    )
            
            logger.info(f"Successfully indexed resume {resume.id} with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing resume {resume.id}: {e}")
            return False
    
    def index_all_resumes(self) -> Dict[str, int]:
        """Index all resumes in the database"""
        
        results = {'success': 0, 'failed': 0, 'total': 0}
        
        try:
            # Get all resumes
            resumes = Resume.query.all()
            results['total'] = len(resumes)
            
            logger.info(f"Starting indexing of {results['total']} resumes")
            
            for resume in resumes:
                if self.index_resume(resume):
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    
                # Log progress every 10 resumes
                if (results['success'] + results['failed']) % 10 == 0:
                    logger.info(f"Processed {results['success'] + results['failed']}/{results['total']} resumes")
            
            logger.info(f"Indexing complete: {results['success']} success, {results['failed']} failed")
            
        except Exception as e:
            logger.error(f"Error in bulk indexing: {e}")
            
        return results
    
    def semantic_search(self, query: str, requirements: Dict, top_k: int = 10) -> List[Dict]:
        """Perform semantic search across all collections"""
        
        try:
            # Generate query embedding
            query_embedding = self.generate_embeddings([query])[0]
            
            # Search across different collections with different weights
            all_results = []
            
            # Search configurations
            search_configs = [
                {
                    'collection': self.collections['resumes'],
                    'weight': 1.0,
                    'limit': top_k
                },
                {
                    'collection': self.collections['skills'], 
                    'weight': 1.5,  # Higher weight for skills
                    'limit': top_k
                },
                {
                    'collection': self.collections['experience'],
                    'weight': 1.2,  # Higher weight for experience
                    'limit': top_k
                },
                {
                    'collection': self.collections['education'],
                    'weight': 0.8,  # Lower weight for education
                    'limit': top_k // 2
                }
            ]
            
            # Perform searches
            for config in search_configs:
                try:
                    results = self.qdrant_client.search(
                        collection_name=config['collection'],
                        query_vector=query_embedding.tolist(),
                        limit=config['limit'],
                        score_threshold=0.3  # Minimum similarity threshold
                    )
                    
                    # Process results
                    for result in results:
                        all_results.append({
                            'resume_id': result.payload['resume_id'],
                            'name': result.payload['name'],
                            'text': result.payload['text'],
                            'type': result.payload['type'],
                            'score': result.score * config['weight'],  # Apply weight
                            'original_score': result.score,
                            'collection': config['collection'],
                            'metadata': {k: v for k, v in result.payload.items() 
                                       if k not in ['text', 'type', 'resume_id', 'name']}
                        })
                        
                except Exception as e:
                    logger.error(f"Error searching collection {config['collection']}: {e}")
            
            # Group by resume_id and aggregate scores
            resume_scores = {}
            for result in all_results:
                resume_id = result['resume_id']
                if resume_id not in resume_scores:
                    resume_scores[resume_id] = {
                        'resume_id': resume_id,
                        'name': result['name'],
                        'total_score': 0,
                        'match_count': 0,
                        'matches': [],
                        'best_match_score': 0
                    }
                
                resume_scores[resume_id]['total_score'] += result['score']
                resume_scores[resume_id]['match_count'] += 1
                resume_scores[resume_id]['matches'].append(result)
                resume_scores[resume_id]['best_match_score'] = max(
                    resume_scores[resume_id]['best_match_score'], 
                    result['score']
                )
            
            # Calculate final scores and rank
            final_results = []
            for resume_data in resume_scores.values():
                # Weighted score: average score * match diversity bonus
                avg_score = resume_data['total_score'] / resume_data['match_count']
                diversity_bonus = min(resume_data['match_count'] / len(search_configs), 1.0)
                final_score = avg_score * (1 + diversity_bonus * 0.2)
                
                final_results.append({
                    'resume_id': resume_data['resume_id'],
                    'name': resume_data['name'],
                    'final_score': final_score,
                    'avg_score': avg_score,
                    'match_count': resume_data['match_count'],
                    'best_match_score': resume_data['best_match_score'],
                    'matches': resume_data['matches'][:3]  # Top 3 matches per resume
                })
            
            # Sort by final score and return top results
            final_results.sort(key=lambda x: x['final_score'], reverse=True)
            return final_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def requirement_based_search(self, requirements: Dict, top_k: int = 10) -> List[Dict]:
        """Search based on structured requirements with filters"""
        
        try:
            all_results = []
            
            # Skills-based search
            if requirements.get('required_skills'):
                skills_query = f"Skills: {' '.join(requirements['required_skills'])}"
                skills_results = self.semantic_search(skills_query, requirements, top_k)
                all_results.extend(skills_results)
            
            # Experience-based search
            if requirements.get('job_title') or requirements.get('industry'):
                exp_parts = []
                if requirements.get('job_title'):
                    exp_parts.append(f"Job title: {requirements['job_title']}")
                if requirements.get('industry'):
                    exp_parts.append(f"Industry: {requirements['industry']}")
                
                exp_query = ' '.join(exp_parts)
                exp_results = self.semantic_search(exp_query, requirements, top_k)
                all_results.extend(exp_results)
            
            # Technology-based search
            if requirements.get('technologies'):
                tech_query = f"Technologies: {' '.join(requirements['technologies'])}"
                tech_results = self.semantic_search(tech_query, requirements, top_k)
                all_results.extend(tech_results)
            
            # Education-based search
            if requirements.get('education_level'):
                edu_query = f"Education: {requirements['education_level']}"
                edu_results = self.semantic_search(edu_query, requirements, top_k)
                all_results.extend(edu_results)
            
            # If no specific requirements, do general search
            if not all_results and requirements.get('job_title'):
                general_query = requirements['job_title']
                all_results = self.semantic_search(general_query, requirements, top_k)
            
            # Deduplicate and rank
            unique_resumes = {}
            for result in all_results:
                resume_id = result['resume_id']
                if resume_id not in unique_resumes:
                    unique_resumes[resume_id] = result
                else:
                    # Keep the one with higher score
                    if result['final_score'] > unique_resumes[resume_id]['final_score']:
                        unique_resumes[resume_id] = result
            
            # Sort and return
            final_results = list(unique_resumes.values())
            final_results.sort(key=lambda x: x['final_score'], reverse=True)
            return final_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in requirement-based search: {e}")
            return []
    
    def get_resume_details_with_rag(self, resume_id: int) -> Dict:
        """Get detailed resume information with RAG context"""
        
        try:
            # Get resume from database
            resume = Resume.query.get(resume_id)
            if not resume:
                return {}
            
            # Search for all chunks related to this resume
            all_chunks = []
            
            for collection_name in self.collections.values():
                try:
                    # Use scroll to get all points for this resume
                    results = self.qdrant_client.scroll(
                        collection_name=collection_name,
                        scroll_filter=Filter(
                            must=[
                                FieldCondition(
                                    key="resume_id",
                                    match=MatchValue(value=resume_id)
                                )
                            ]
                        ),
                        limit=100
                    )[0]  # Get points from scroll result
                    
                    for point in results:
                        all_chunks.append({
                            'text': point.payload['text'],
                            'type': point.payload['type'],
                            'metadata': {k: v for k, v in point.payload.items() 
                                       if k not in ['text', 'type']}
                        })
                        
                except Exception as e:
                    logger.error(f"Error getting chunks from {collection_name}: {e}")
            
            return {
                'resume': resume,
                'chunks': all_chunks,
                'chunk_count': len(all_chunks)
            }
            
        except Exception as e:
            logger.error(f"Error getting resume details with RAG: {e}")
            return {}
    
    def auto_sync_resume(self, resume: Resume, operation: str = 'create'):
        """
        Automatically sync resume to vector database when created/updated/deleted
        
        Args:
            resume: Resume object
            operation: 'create', 'update', or 'delete'
        """
        try:
            if operation == 'delete':
                return self.delete_resume_from_index(resume.id)
            
            # For create/update operations
            result = self.index_single_resume(resume)
            
            if result['success']:
                logger.info(f"Auto-synced resume {resume.id} ({operation}): {result['message']}")
                return True
            else:
                logger.error(f"Failed to auto-sync resume {resume.id}: {result['error']}")
                return False
                
        except Exception as e:
            logger.error(f"Error in auto_sync_resume for resume {resume.id}: {e}")
            return False
    
    def auto_sync_job(self, job: Job, operation: str = 'create'):
        """
        Automatically sync job to vector database when created/updated/deleted
        
        Args:
            job: Job object
            operation: 'create', 'update', or 'delete'
        """
        try:
            if operation == 'delete':
                return self.delete_job_from_index(job.id)
            
            # For create/update operations
            result = self.index_single_job(job)
            
            if result['success']:
                logger.info(f"Auto-synced job {job.id} ({operation}): {result['message']}")
                return True
            else:
                logger.error(f"Failed to auto-sync job {job.id}: {result['error']}")
                return False
                
        except Exception as e:
            logger.error(f"Error in auto_sync_job for job {job.id}: {e}")
            return False
    
    def index_single_job(self, job: Job) -> Dict[str, Any]:
        """Index a single job posting to vector database"""
        try:
            # Create job chunks for indexing
            job_chunks = self.chunk_job_text(job)
            
            if not job_chunks:
                return {'success': False, 'error': 'No job content to index'}
            
            points_added = 0
            
            for chunk in job_chunks:
                try:
                    # Generate embedding
                    embedding = self.embedding_model.encode(chunk['text']).tolist()
                    
                    # Create point for Qdrant
                    point = PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload={
                            'text': chunk['text'],
                            'chunk_type': chunk['type'],
                            'job_id': job.id,
                            'indexed_at': datetime.now().isoformat(),
                            **chunk['metadata']
                        }
                    )
                    
                    # Index to jobs collection
                    self.qdrant_client.upsert(
                        collection_name=self.collections['jobs'],
                        points=[point]
                    )
                    
                    points_added += 1
                    
                except Exception as e:
                    logger.error(f"Error indexing job chunk: {e}")
                    continue
            
            return {
                'success': True,
                'message': f'Indexed job {job.id} with {points_added} chunks',
                'points_added': points_added
            }
            
        except Exception as e:
            logger.error(f"Error indexing job {job.id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def chunk_job_text(self, job: Job) -> List[Dict]:
        """Break job posting into semantic chunks for better matching"""
        
        chunks = []
        
        # Full job description chunk
        full_text_parts = []
        
        if job.title:
            full_text_parts.append(f"Job Title: {job.title}")
        if job.company:
            full_text_parts.append(f"Company: {job.company}")
        if job.location:
            full_text_parts.append(f"Location: {job.location}")
        if job.employment_type:
            full_text_parts.append(f"Employment Type: {job.employment_type}")
        if job.category:
            full_text_parts.append(f"Category: {job.category}")
        if job.description:
            full_text_parts.append(f"Description: {job.description}")
        
        if full_text_parts:
            chunks.append({
                'text': ' | '.join(full_text_parts),
                'type': 'full_job',
                'metadata': {
                    'job_id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'location': job.location or '',
                    'category': job.category,
                    'employment_type': job.employment_type,
                    'salary_min': job.salary_min,
                    'salary_max': job.salary_max,
                    'is_active': job.is_active
                }
            })
        
        # Requirements chunk (if requirements exist and are structured)
        if job.requirements:
            if isinstance(job.requirements, list):
                requirements_text = ' '.join(str(req) for req in job.requirements)
            else:
                requirements_text = str(job.requirements)
            
            chunks.append({
                'text': f"Job Requirements: {requirements_text}",
                'type': 'requirements',
                'metadata': {
                    'job_id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'requirements': job.requirements
                }
            })
        
        return chunks
    
    def delete_resume_from_index(self, resume_id: int) -> bool:
        """Remove resume from all vector collections"""
        try:
            collections_to_clean = ['resumes', 'skills', 'experience', 'education']
            
            for collection_key in collections_to_clean:
                collection_name = self.collections[collection_key]
                
                # Delete all points with this resume_id
                self.qdrant_client.delete(
                    collection_name=collection_name,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="resume_id",
                                match=MatchValue(value=resume_id)
                            )
                        ]
                    )
                )
            
            logger.info(f"Deleted resume {resume_id} from vector database")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting resume {resume_id} from index: {e}")
            return False
    
    def delete_job_from_index(self, job_id: int) -> bool:
        """Remove job from vector database"""
        try:
            # Delete all points with this job_id
            self.qdrant_client.delete(
                collection_name=self.collections['jobs'],
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="job_id",
                            match=MatchValue(value=job_id)
                        )
                    ]
                )
            )
            
            logger.info(f"Deleted job {job_id} from vector database")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting job {job_id} from index: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Dict]:
        """Get statistics for all collections"""
        try:
            stats = {}
            
            for collection_key, collection_name in self.collections.items():
                try:
                    # Get collection info
                    collection_info = self.qdrant_client.get_collection(collection_name)
                    
                    stats[collection_key] = {
                        'collection_name': collection_name,
                        'points_count': collection_info.points_count,
                        'vectors_count': collection_info.vectors_count,
                        'status': collection_info.status
                    }
                    
                except Exception as e:
                    stats[collection_key] = {
                        'collection_name': collection_name,
                        'error': str(e),
                        'points_count': 0
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    def enhanced_semantic_search(self, query: str, requirements: Dict, top_k: int = 20) -> List[Dict]:
        """
        Enhanced semantic search with strict data validation and anti-hallucination measures
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embeddings([query])[0]
            
            # Search configurations with adjusted thresholds for better results
            search_configs = [
                {
                    'collection': self.collections['resumes'],
                    'weight': 1.0,
                    'limit': top_k * 2,  # Get more candidates for better filtering
                    'threshold': 0.2  # Lower threshold for more results
                },
                {
                    'collection': self.collections['skills'], 
                    'weight': 2.0,  # Much higher weight for skills matching
                    'limit': top_k * 2,
                    'threshold': 0.25  # Lower threshold for skills
                },
                {
                    'collection': self.collections['experience'],
                    'weight': 1.8,  # High weight for experience
                    'limit': top_k * 2,
                    'threshold': 0.25  # Lower threshold for experience
                },
                {
                    'collection': self.collections['education'],
                    'weight': 0.9,
                    'limit': top_k,
                    'threshold': 0.2  # Lower threshold for education
                }
            ]
            
            all_results = []
            
            # Perform searches with validation
            for config in search_configs:
                try:
                    results = self.qdrant_client.search(
                        collection_name=config['collection'],
                        query_vector=query_embedding.tolist(),
                        limit=config['limit'],
                        score_threshold=config['threshold']  # Strict threshold
                    )
                    
                    # Validate and process results
                    for result in results:
                        if self._validate_search_result(result):
                            all_results.append({
                                'resume_id': result.payload['resume_id'],
                                'name': result.payload.get('name', 'Unknown'),
                                'text': result.payload['text'],
                                'type': result.payload['type'],
                                'score': result.score * config['weight'],
                                'original_score': result.score,
                                'collection': config['collection'],
                                'metadata': self._extract_validated_metadata(result.payload)
                            })
                    
                    logger.info(f"Collection {config['collection']}: {len(results)} raw results, {len([r for r in results if self._validate_search_result(r)])} valid results")
                        
                except Exception as e:
                    logger.error(f"Error searching collection {config['collection']}: {e}")
            
            # Advanced aggregation with score validation
            aggregated_results = self._aggregate_and_validate_results(all_results, top_k)
            
            logger.info(f"Enhanced semantic search complete: {len(all_results)} raw results -> {len(aggregated_results)} final results")
            return aggregated_results
            
        except Exception as e:
            logger.error(f"Error in enhanced semantic search: {e}")
            return []
    
    def _validate_search_result(self, result) -> bool:
        """Validate search result to prevent hallucination"""
        try:
            payload = result.payload
            
            # Must have essential fields
            if not payload.get('resume_id') or not payload.get('text'):
                return False
            
            # Resume ID must be valid integer
            try:
                int(payload['resume_id'])
            except (ValueError, TypeError):
                return False
            
            # Score must be reasonable (not NaN or infinite)
            if not (0 <= result.score <= 1):
                return False
            
            # Text must not be empty or just whitespace
            if not payload['text'].strip():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating search result: {e}")
            return False
    
    def _extract_validated_metadata(self, payload: Dict) -> Dict:
        """Extract and validate metadata from payload"""
        safe_metadata = {}
        
        # Safe field extraction with validation
        safe_fields = [
            'email', 'phone', 'filename', 'skills', 'job_title', 
            'company', 'duration', 'degree', 'institution', 'year'
        ]
        
        for field in safe_fields:
            if field in payload and payload[field] is not None:
                # Clean and validate the field
                value = payload[field]
                if isinstance(value, (str, int, float, list)):
                    safe_metadata[field] = value
        
        return safe_metadata
    
    def _aggregate_and_validate_results(self, all_results: List[Dict], top_k: int) -> List[Dict]:
        """Aggregate results by resume and validate final scores"""
        
        # Group by resume_id with enhanced validation
        resume_scores = {}
        
        for result in all_results:
            resume_id = result['resume_id']
            
            if resume_id not in resume_scores:
                resume_scores[resume_id] = {
                    'resume_id': resume_id,
                    'name': result['name'],
                    'total_score': 0,
                    'weighted_score': 0,
                    'match_count': 0,
                    'skill_matches': 0,
                    'experience_matches': 0,
                    'matches': [],
                    'best_match_score': 0,
                    'collection_diversity': set()
                }
            
            # Add validated result
            resume_data = resume_scores[resume_id]
            resume_data['total_score'] += result['score']
            resume_data['match_count'] += 1
            resume_data['matches'].append(result)
            resume_data['best_match_score'] = max(resume_data['best_match_score'], result['score'])
            resume_data['collection_diversity'].add(result['collection'])
            
            # Track specific match types for better ranking
            if 'skills' in result['collection']:
                resume_data['skill_matches'] += 1
            elif 'experience' in result['collection']:
                resume_data['experience_matches'] += 1
        
        # Calculate final validated scores
        final_results = []
        
        for resume_data in resume_scores.values():
            # Calculate weighted score with diversity bonus
            avg_score = resume_data['total_score'] / resume_data['match_count']
            diversity_bonus = len(resume_data['collection_diversity']) * 0.1
            skill_bonus = resume_data['skill_matches'] * 0.15  # Higher bonus for skill matches
            experience_bonus = resume_data['experience_matches'] * 0.1
            
            final_score = avg_score + diversity_bonus + skill_bonus + experience_bonus
            
            # Only include results with reasonable scores
            if final_score >= 0.3:  # Minimum threshold for inclusion
                final_results.append({
                    'resume_id': resume_data['resume_id'],
                    'name': resume_data['name'],
                    'final_score': min(final_score, 2.0),  # Cap score to prevent inflation
                    'avg_score': avg_score,
                    'match_count': resume_data['match_count'],
                    'skill_matches': resume_data['skill_matches'],
                    'experience_matches': resume_data['experience_matches'],
                    'best_match_score': resume_data['best_match_score'],
                    'diversity_score': len(resume_data['collection_diversity']),
                    'top_matches': sorted(resume_data['matches'], 
                                        key=lambda x: x['score'], reverse=True)[:3]
                })
        
        # Sort by final score and return top validated results
        final_results.sort(key=lambda x: x['final_score'], reverse=True)
        return final_results[:top_k]
    
    def get_verified_candidate_data(self, resume_id: int) -> Dict:
        """
        Get verified candidate data with strict validation - NO HALLUCINATION
        """
        try:
            # Get resume from database - this is the source of truth
            resume = Resume.query.get(resume_id)
            if not resume:
                return {'error': 'Candidate not found', 'resume_id': resume_id}
            
            # Build verified data structure with only confirmed fields
            verified_data = {
                'resume_id': resume.id,
                'name': self._safe_string(resume.name),
                'email': self._safe_string(resume.email),
                'phone': self._safe_string(resume.phone),
                'filename': self._safe_string(resume.filename),
                'upload_date': resume.created_at.isoformat() if resume.created_at else None,  # Fix: use created_at instead of upload_date
                'skills': [],
                'experience': [],
                'education': [],
                'raw_text_length': len(resume.raw_text) if resume.raw_text else 0,
                'data_completeness': {}
            }
            
            # Validate and add skills
            if resume.skills and isinstance(resume.skills, list):
                verified_data['skills'] = [self._safe_string(skill) for skill in resume.skills 
                                         if skill and str(skill).strip()]
            
            # Validate and add experience
            if resume.experience and isinstance(resume.experience, list):
                for exp in resume.experience:
                    if isinstance(exp, dict):
                        clean_exp = {}
                        for key in ['title', 'company', 'duration', 'description']:
                            if key in exp and exp[key]:
                                clean_exp[key] = self._safe_string(exp[key])
                        
                        if clean_exp:  # Only add if has some content
                            verified_data['experience'].append(clean_exp)
            
            # Validate and add education
            if resume.education and isinstance(resume.education, list):
                for edu in resume.education:
                    if isinstance(edu, dict):
                        clean_edu = {}
                        for key in ['degree', 'institution', 'year', 'grade']:
                            if key in edu and edu[key]:
                                clean_edu[key] = self._safe_string(edu[key])
                        
                        if clean_edu:  # Only add if has some content
                            verified_data['education'].append(clean_edu)
            
            # Calculate data completeness scores
            verified_data['data_completeness'] = {
                'has_contact': bool(verified_data['email'] or verified_data['phone']),
                'has_skills': len(verified_data['skills']) > 0,
                'has_experience': len(verified_data['experience']) > 0,
                'has_education': len(verified_data['education']) > 0,
                'skills_count': len(verified_data['skills']),
                'experience_count': len(verified_data['experience']),
                'education_count': len(verified_data['education'])
            }
            
            return verified_data
            
        except Exception as e:
            logger.error(f"Error getting verified candidate data for {resume_id}: {e}")
            return {'error': f'Failed to retrieve candidate data: {str(e)}', 'resume_id': resume_id}
    
    def _safe_string(self, value) -> str:
        """Safely convert value to string, handling None and empty values"""
        if value is None:
            return ""
        
        str_value = str(value).strip()
        return str_value if str_value else ""
    
    def bulk_get_verified_candidates(self, resume_ids: List[int]) -> List[Dict]:
        """
        Get verified data for multiple candidates efficiently
        """
        verified_candidates = []
        
        for resume_id in resume_ids:
            try:
                candidate_data = self.get_verified_candidate_data(resume_id)
                if 'error' not in candidate_data:
                    verified_candidates.append(candidate_data)
                else:
                    logger.warning(f"Could not verify candidate {resume_id}: {candidate_data.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error verifying candidate {resume_id}: {e}")
        
        return verified_candidates
    
    def index_single_resume(self, resume: Resume) -> Dict[str, Any]:
        """Index a single resume with enhanced validation"""
        try:
            # Validate resume object first
            if not resume or not resume.id:
                return {'success': False, 'error': 'Invalid resume object'}
            
            # Delete existing entries for this resume to avoid duplicates
            self.delete_resume_from_index(resume.id)
            
            # Generate validated chunks
            chunks = self.chunk_resume_text(resume)
            
            if not chunks:
                return {'success': False, 'error': 'No valid content to index'}
            
            # Prepare points for each collection with validation
            points_by_collection = {collection: [] for collection in self.collections.values()}
            points_added = 0
            
            for chunk in chunks:
                if not chunk.get('text') or not chunk['text'].strip():
                    continue  # Skip empty chunks
                
                try:
                    # Generate embedding
                    embedding = self.generate_embeddings([chunk['text']])[0]
                    
                    # Validate embedding
                    if len(embedding) != self.embedding_dimension:
                        logger.error(f"Invalid embedding dimension for resume {resume.id}")
                        continue
                    
                    # Create validated point
                    point_id = str(uuid.uuid4())
                    point = PointStruct(
                        id=point_id,
                        vector=embedding.tolist(),
                        payload={
                            'text': chunk['text'],
                            'type': chunk['type'],
                            'resume_id': resume.id,  # Ensure this is always included
                            'indexed_at': datetime.utcnow().isoformat(),
                            **chunk['metadata']
                        }
                    )
                    
                    # Add to appropriate collection
                    if chunk['type'] == 'full_resume':
                        points_by_collection[self.collections['resumes']].append(point)
                    elif chunk['type'] == 'skills':
                        points_by_collection[self.collections['skills']].append(point)
                    elif chunk['type'] == 'experience':
                        points_by_collection[self.collections['experience']].append(point)
                    elif chunk['type'] == 'education':
                        points_by_collection[self.collections['education']].append(point)
                    
                    points_added += 1
                    
                except Exception as e:
                    logger.error(f"Error creating point for resume {resume.id}: {e}")
                    continue
            
            # Insert points into collections
            collections_updated = 0
            for collection_name, points in points_by_collection.items():
                if points:
                    try:
                        self.qdrant_client.upsert(
                            collection_name=collection_name,
                            points=points
                        )
                        collections_updated += 1
                    except Exception as e:
                        logger.error(f"Error upserting to {collection_name}: {e}")
            
            if points_added > 0 and collections_updated > 0:
                return {
                    'success': True,
                    'message': f'Successfully indexed resume {resume.id} with {points_added} points across {collections_updated} collections',
                    'points_added': points_added,
                    'collections_updated': collections_updated
                }
            else:
                return {'success': False, 'error': 'No points were successfully indexed'}
            
        except Exception as e:
            logger.error(f"Error indexing resume {resume.id}: {e}")
            return {'success': False, 'error': str(e)}

# Initialize RAG service instance
rag_service = RAGTalentService()
