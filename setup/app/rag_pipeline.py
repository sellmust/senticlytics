"""
RAG Pipeline
Retrieval-Augmented Generation for customer feedback intelligence
"""

import os
import json
import logging
import hashlib
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Configuration
QDRANT_HOST = os.getenv('QDRANT_HOST', 'localhost')
QDRANT_PORT = int(os.getenv('QDRANT_PORT', 6333))
QDRANT_PROTOCOL = os.getenv('QDRANT_PROTOCOL', 'http')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 500))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 100))
TOP_K = int(os.getenv('TOP_K', 5))
COLLECTION_NAME = os.getenv('VECTOR_COLLECTION_NAME', 'feedback_embeddings')

# RAG Pipeline Class
class RAGPipeline:
    """Retrieval-Augmented Generation pipeline for feedback analysis"""
    
    def __init__(self):
        """Initialize RAG pipeline"""
        logger.info("Initializing RAG Pipeline...")
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"✓ Embedding model loaded: {EMBEDDING_MODEL}")
            logger.info(f"✓ Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {str(e)}")
            raise
        
        # Initialize Qdrant client
        try:
            self.qdrant_client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                prefer_grpc=False,
                timeout=30
            )
            logger.info(f"✓ Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {str(e)}")
            raise
        
        # Create or get collection
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Create or verify Qdrant collection"""
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            existing_collections = [c.name for c in collections.collections]
            
            if COLLECTION_NAME not in existing_collections:
                logger.info(f"Creating collection: {COLLECTION_NAME}")
                self.qdrant_client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✓ Collection created: {COLLECTION_NAME}")
            else:
                logger.info(f"✓ Collection already exists: {COLLECTION_NAME}")
                
        except Exception as e:
            logger.error(f"❌ Error initializing collection: {str(e)}")
            raise
    
    # Chunk Processing
    def _chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, 
                    overlap: int = CHUNK_OVERLAP) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text to chunk
            chunk_size: Size of each chunk
            overlap: Overlap between chunks
            
        Returns:
            List of chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        
        return chunks
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for embedding
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Truncate if too long
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    # Indexing
    def index_feedback(self, feedback_id: int, text: str, metadata: Dict = None) -> str:
        """
        Index a feedback item in RAG database
        
        Args:
            feedback_id: Unique feedback ID
            text: Feedback text content
            metadata: Additional metadata (sentiment, category, etc)
            
        Returns:
            Vector ID of indexed item
        """
        try:
            # Preprocess text
            text = self._preprocess_text(text)
            
            # Generate embedding
            embedding = self.embedding_model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            
            # Prepare point data
            vector_id = str(feedback_id)
            point_metadata = metadata or {}
            point_metadata.update({
                'feedback_id': feedback_id,
                'text': text,
                'indexed_at': datetime.utcnow().isoformat(),
                'embedding_model': EMBEDDING_MODEL
            })
            
            # Create point
            point = PointStruct(
                id=int(vector_id),
                vector=embedding.tolist(),
                payload=point_metadata
            )
            
            # Upsert to Qdrant
            self.qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=[point]
            )
            
            logger.info(f"✓ Indexed feedback {feedback_id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"❌ Error indexing feedback {feedback_id}: {str(e)}")
            raise
    
    def batch_index_feedbacks(self, feedbacks: List[Dict]) -> Tuple[int, int]:
        """
        Index multiple feedbacks in batch
        
        Args:
            feedbacks: List of feedback dicts with 'id', 'text', 'metadata'
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0
        batch_size = 32
        
        logger.info(f"Starting batch indexing of {len(feedbacks)} feedbacks")
        
        for i in range(0, len(feedbacks), batch_size):
            batch = feedbacks[i:i + batch_size]
            points = []
            
            for feedback in batch:
                try:
                    # Preprocess and embed
                    text = self._preprocess_text(feedback['text'])
                    embedding = self.embedding_model.encode(
                        text,
                        convert_to_numpy=True,
                        normalize_embeddings=True
                    )
                    
                    # Prepare metadata
                    metadata = feedback.get('metadata', {})
                    metadata.update({
                        'feedback_id': feedback['id'],
                        'text': text,
                        'indexed_at': datetime.utcnow().isoformat()
                    })
                    
                    # Create point
                    point = PointStruct(
                        id=feedback['id'],
                        vector=embedding.tolist(),
                        payload=metadata
                    )
                    points.append(point)
                    successful += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process feedback {feedback['id']}: {str(e)}")
                    failed += 1
            
            # Upsert batch
            if points:
                try:
                    self.qdrant_client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=points
                    )
                    logger.info(f"✓ Indexed batch {i//batch_size + 1} ({len(points)} items)")
                except Exception as e:
                    logger.error(f"❌ Batch upsert failed: {str(e)}")
                    failed += len(points)
                    successful -= len(points)
        
        logger.info(f"✓ Batch indexing complete: {successful} successful, {failed} failed")
        return successful, failed
    
    # Retrieval/Search
    def query(self, query_text: str, top_k: int = TOP_K, 
              filters: Dict = None, min_score: float = 0.0) -> List[Dict]:
        """
        Retrieve relevant feedbacks for a query
        
        Args:
            query_text: Search query
            top_k: Number of results to return
            filters: Metadata filters (sentiment, category, etc)
            min_score: Minimum similarity score threshold
            
        Returns:
            List of relevant feedbacks with scores
        """
        try:
            # Encode query
            query_embedding = self.embedding_model.encode(
                self._preprocess_text(query_text),
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            
            # Search in Qdrant
            search_result = self.qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_embedding.tolist(),
                limit=top_k,
                query_filter=self._build_filter(filters) if filters else None,
                with_payload=True
            )
            
            # Format results
            results = []
            for hit in search_result.points:
                result = {
                    'feedback_id': hit.payload.get('feedback_id'),
                    'text': hit.payload.get('text'),
                    'similarity_score': hit.score,
                    'metadata': {k: v for k, v in hit.payload.items() 
                                if k not in ['text', 'feedback_id']}
                }
                
                if result['similarity_score'] >= min_score:
                    results.append(result)
            
            logger.info(f"✓ Query returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Query error: {str(e)}")
            raise
    
    def similarity_search(self, query_text: str, top_k: int = TOP_K) -> List[Dict]:
        """
        Semantic similarity search
        
        Args:
            query_text: Search query
            top_k: Number of results
            
        Returns:
            Similar feedbacks
        """
        return self.query(query_text, top_k=top_k, min_score=0.3)
    
    # Delete/Update
    def delete_feedback(self, feedback_id: int) -> bool:
        """Delete indexed feedback"""
        try:
            self.qdrant_client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=[int(feedback_id)]
            )
            logger.info(f"✓ Deleted feedback {feedback_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error deleting feedback: {str(e)}")
            return False
    
    def reindex_feedback(self, feedback_id: int, text: str, metadata: Dict = None) -> str:
        """Reindex feedback (delete and recreate)"""
        self.delete_feedback(feedback_id)
        return self.index_feedback(feedback_id, text, metadata)
    
    # Analytics
    def get_collection_stats(self) -> Dict:
        """Get RAG collection statistics"""
        try:
            collection_info = self.qdrant_client.get_collection(COLLECTION_NAME)
            
            stats = {
                'collection_name': COLLECTION_NAME,
                'points_count': collection_info.points_count,
                'vectors_count': collection_info.vectors_count,
                'segments_count': len(collection_info.segments),
                'embedding_dimension': self.embedding_dim,
                'embedding_model': EMBEDDING_MODEL
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {}
    
    def get_most_similar(self, feedback_id: int, top_k: int = 5) -> List[Dict]:
        """Get feedbacks most similar to a specific feedback"""
        try:
            # Get feedback vector
            point = self.qdrant_client.retrieve(
                collection_name=COLLECTION_NAME,
                ids=[feedback_id],
                with_vectors=True
            )
            if not point:
                return []
            vector = point[0].vector
            
            # Search similar
            search_result = self.qdrant_client.search(
                collection_name=COLLECTION_NAME,
                vector=vector,
                limit=top_k + 1  # +1 to exclude itself
            )
            
            results = []
            for hit in search_result:
                if hit.id != feedback_id:  # Exclude the query feedback itself
                    results.append({
                        'feedback_id': hit.payload.get('feedback_id'),
                        'similarity_score': hit.score,
                        'text': hit.payload.get('text')[:100] + '...'  # Truncate
                    })
            
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error getting similar feedbacks: {str(e)}")
            return []
    
    # Helper Methods
    def _build_filter(self, filters: Dict):
        """Build Qdrant filter from metadata filters"""
        # Simplified filter building
        # In production, use proper Qdrant filter DSL
        return None
    
    def health_check(self) -> bool:
        """Check RAG pipeline health"""
        try:
            self.qdrant_client.get_collection(COLLECTION_NAME)
            return True
        except Exception as e:
            logger.error(f"RAG health check failed: {str(e)}")
            return False

# Global RAG Instance
_rag_instance: Optional[RAGPipeline] = None

def get_rag_pipeline() -> RAGPipeline:
    """Get or initialize global RAG pipeline instance"""
    global _rag_instance
    
    if _rag_instance is None:
        _rag_instance = RAGPipeline()
    
    return _rag_instance

if __name__ == "__main__":
    # Test RAG pipeline
    rag = RAGPipeline()
    print("RAG Pipeline initialized successfully")
    print(f"Stats: {rag.get_collection_stats()}")