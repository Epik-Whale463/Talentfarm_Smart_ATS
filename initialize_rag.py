#!/usr/bin/env python3
"""
RAG System Initialization Script for Talent Search

This script initializes the RAG system by:
1. Testing Qdrant connection
2. Creating necessary collections
3. Indexing existing resumes
4. Running a test search

Run this script after setting up the RAG service to ensure everything works correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from services.rag_service import rag_service
from models import Resume
import logging

# Create Flask app
app = create_app()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_qdrant_connection():
    """Test connection to Qdrant"""
    try:
        collections = rag_service.qdrant_client.get_collections()
        logger.info(f"✅ Qdrant connection successful. Found {len(collections.collections)} collections.")
        return True
    except Exception as e:
        logger.error(f"❌ Qdrant connection failed: {e}")
        return False

def initialize_collections():
    """Initialize Qdrant collections"""
    try:
        rag_service._initialize_collections()
        logger.info("✅ Collections initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize collections: {e}")
        return False

def check_resume_data():
    """Check if there are resumes in the database"""
    try:
        with app.app_context():
            total_resumes = Resume.query.count()
            parsed_resumes = Resume.query.filter(Resume.parsed_data.isnot(None)).count()
            
            logger.info(f"📊 Database stats:")
            logger.info(f"   - Total resumes: {total_resumes}")
            logger.info(f"   - Parsed resumes: {parsed_resumes}")
            
            if total_resumes == 0:
                logger.warning("⚠️  No resumes found in database. Please upload some resumes first.")
                return False
            
            if parsed_resumes == 0:
                logger.warning("⚠️  No parsed resumes found. Resume parsing may not be working.")
                return False
                
            return True
    except Exception as e:
        logger.error(f"❌ Failed to check resume data: {e}")
        return False

def index_resumes():
    """Index all resumes into RAG system"""
    try:
        with app.app_context():
            logger.info("🔄 Starting resume indexing...")
            results = rag_service.index_all_resumes()
            
            logger.info(f"✅ Indexing completed:")
            logger.info(f"   - Success: {results['success']}")
            logger.info(f"   - Failed: {results['failed']}")
            logger.info(f"   - Total: {results['total']}")
            
            return results['success'] > 0
    except Exception as e:
        logger.error(f"❌ Failed to index resumes: {e}")
        return False

def test_search():
    """Test semantic search functionality"""
    try:
        logger.info("🔍 Testing semantic search...")
        
        # Test queries
        test_queries = [
            "Python developer",
            "Machine learning engineer",
            "Full stack developer",
            "Data scientist with experience in AI"
        ]
        
        for query in test_queries:
            results = rag_service.semantic_search(query, {}, top_k=3)
            logger.info(f"   Query: '{query}' -> Found {len(results)} results")
            
            if results:
                top_result = results[0]
                logger.info(f"   Top match: {top_result['name']} (score: {top_result['final_score']:.3f})")
        
        logger.info("✅ Search test completed successfully.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Search test failed: {e}")
        return False

def get_collection_stats():
    """Display collection statistics"""
    try:
        stats = rag_service.get_collection_stats()
        
        logger.info("📈 Collection Statistics:")
        for collection_type, collection_stats in stats.items():
            if 'error' not in collection_stats:
                logger.info(f"   {collection_type}: {collection_stats['points_count']} points")
            else:
                logger.error(f"   {collection_type}: Error - {collection_stats['error']}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to get collection stats: {e}")
        return False

def main():
    """Main initialization function"""
    
    logger.info("🚀 Starting RAG System Initialization")
    logger.info("=" * 50)
    
    # Step 1: Test Qdrant connection
    logger.info("1. Testing Qdrant connection...")
    if not test_qdrant_connection():
        logger.error("❌ Initialization failed at connection test.")
        return False
    
    # Step 2: Initialize collections
    logger.info("\n2. Initializing collections...")
    if not initialize_collections():
        logger.error("❌ Initialization failed at collection setup.")
        return False
    
    # Step 3: Check resume data
    logger.info("\n3. Checking resume data...")
    if not check_resume_data():
        logger.error("❌ Initialization failed at data check.")
        return False
    
    # Step 4: Index resumes
    logger.info("\n4. Indexing resumes...")
    if not index_resumes():
        logger.error("❌ Initialization failed at indexing.")
        return False
    
    # Step 5: Get collection stats
    logger.info("\n5. Getting collection statistics...")
    get_collection_stats()
    
    # Step 6: Test search
    logger.info("\n6. Testing search functionality...")
    if not test_search():
        logger.error("❌ Initialization failed at search test.")
        return False
    
    logger.info("\n" + "=" * 50)
    logger.info("🎉 RAG System Initialization Completed Successfully!")
    logger.info("\nYour RAG-powered talent search is now ready to use!")
    logger.info("\nNext steps:")
    logger.info("1. Start your Flask application")
    logger.info("2. Go to HR Dashboard")
    logger.info("3. Click 'Search Your Talent' to test the feature")
    logger.info("4. Try queries like 'Python developer with 3 years experience'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
