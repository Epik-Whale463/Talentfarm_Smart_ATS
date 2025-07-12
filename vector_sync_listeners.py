"""
Database Event Listeners for Auto-Sync to Vector Database
This module sets up SQLAlchemy event listeners to automatically sync changes to Qdrant
"""

from sqlalchemy import event
from models import Resume, Job
import logging

logger = logging.getLogger(__name__)

def setup_vector_sync_listeners():
    """Set up event listeners for automatic vector database synchronization"""
    
    # Resume listeners
    @event.listens_for(Resume, 'after_insert')
    def resume_inserted(mapper, connection, target):
        """Auto-sync when a resume is inserted"""
        try:
            from services.rag_service import RAGTalentService
            rag_service = RAGTalentService()
            rag_service.auto_sync_resume(target, 'create')
            logger.info(f"Auto-synced new resume {target.id} to vector database")
        except Exception as e:
            logger.error(f"Failed to auto-sync new resume {target.id}: {e}")
    
    @event.listens_for(Resume, 'after_update')
    def resume_updated(mapper, connection, target):
        """Auto-sync when a resume is updated"""
        try:
            from services.rag_service import RAGTalentService
            rag_service = RAGTalentService()
            rag_service.auto_sync_resume(target, 'update')
            logger.info(f"Auto-synced updated resume {target.id} to vector database")
        except Exception as e:
            logger.error(f"Failed to auto-sync updated resume {target.id}: {e}")
    
    @event.listens_for(Resume, 'after_delete')
    def resume_deleted(mapper, connection, target):
        """Auto-sync when a resume is deleted"""
        try:
            from services.rag_service import RAGTalentService
            rag_service = RAGTalentService()
            rag_service.delete_resume_from_index(target.id)
            logger.info(f"Auto-removed deleted resume {target.id} from vector database")
        except Exception as e:
            logger.error(f"Failed to auto-remove deleted resume {target.id}: {e}")
    
    # Job listeners
    @event.listens_for(Job, 'after_insert')
    def job_inserted(mapper, connection, target):
        """Auto-sync when a job is inserted"""
        try:
            from services.rag_service import RAGTalentService
            rag_service = RAGTalentService()
            rag_service.auto_sync_job(target, 'create')
            logger.info(f"Auto-synced new job {target.id} to vector database")
        except Exception as e:
            logger.error(f"Failed to auto-sync new job {target.id}: {e}")
    
    @event.listens_for(Job, 'after_update')
    def job_updated(mapper, connection, target):
        """Auto-sync when a job is updated"""
        try:
            from services.rag_service import RAGTalentService
            rag_service = RAGTalentService()
            rag_service.auto_sync_job(target, 'update')
            logger.info(f"Auto-synced updated job {target.id} to vector database")
        except Exception as e:
            logger.error(f"Failed to auto-sync updated job {target.id}: {e}")
    
    @event.listens_for(Job, 'after_delete')
    def job_deleted(mapper, connection, target):
        """Auto-sync when a job is deleted"""
        try:
            from services.rag_service import RAGTalentService
            rag_service = RAGTalentService()
            rag_service.delete_job_from_index(target.id)
            logger.info(f"Auto-removed deleted job {target.id} from vector database")
        except Exception as e:
            logger.error(f"Failed to auto-remove deleted job {target.id}: {e}")
    
    logger.info("Vector database sync event listeners registered")

# Call this function when the app starts
def init_vector_sync():
    """Initialize vector database synchronization"""
    setup_vector_sync_listeners()
