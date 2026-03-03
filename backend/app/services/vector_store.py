import uuid
import time
from typing import List, Dict, Optional
from threading import Lock
import logging
from datetime import datetime

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from sklearn.feature_extraction.text import HashingVectorizer

from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Tuning knobs ──────────────────────────────────────────────
VECTOR_DIM = 384               # fixed dimension (same as old model)
UPSERT_BATCH_SIZE = 50         # points per Qdrant upsert() call
ENCODE_BATCH_SIZE = 200        # texts per vectorizer batch
QDRANT_TIMEOUT = 120           # seconds – cloud free-tier can be slow
UPSERT_RETRY_COUNT = 4         # retries per micro-batch upsert
UPSERT_RETRY_DELAY = 2        # initial backoff in seconds
# ──────────────────────────────────────────────────────────────


class VectorStoreService:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VectorStoreService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Lightweight TF-IDF vectorizer — no model download needed
        self.vectorizer = HashingVectorizer(
            n_features=VECTOR_DIM,
            alternate_sign=False,   # all positive values
            norm="l2",              # unit-length vectors for cosine similarity
            ngram_range=(1, 2),     # unigrams + bigrams for better matching
            stop_words="english",
        )
        logger.info(f"Initialized HashingVectorizer (dim={VECTOR_DIM}, ngram_range=(1,2))")

        self._init_qdrant_client()
        self._initialized = True

    def _encode_texts(self, texts: List[str]) -> np.ndarray:
        """Convert texts to dense vectors using TF-IDF hashing."""
        sparse_matrix = self.vectorizer.transform(texts)
        return sparse_matrix.toarray().astype(np.float32)

    def _init_qdrant_client(self):
        """Initialize Qdrant client with generous timeout"""
        try:
            if settings.QDRANT_URL:
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                    timeout=QDRANT_TIMEOUT,
                )
                logger.info(f"Connected to Qdrant cloud: {settings.QDRANT_URL} (timeout={QDRANT_TIMEOUT}s)")
            else:
                self.client = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    api_key=settings.QDRANT_API_KEY,
                    timeout=QDRANT_TIMEOUT,
                )
                logger.info(f"Connected to local Qdrant: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
                
            collections = self.client.get_collections()
            logger.info(f"Qdrant OK – {len(collections.collections)} collections found")
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            raise Exception(f"Failed to initialize Qdrant client: {str(e)}")
        
    def create_collection(self, collection_name: str):
        """Create a new Qdrant collection (idempotent)"""
        try:
            try:
                self.client.get_collection(collection_name)
                logger.info(f"Collection {collection_name} already exists")
                return
            except Exception:
                pass
                
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=VECTOR_DIM,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {collection_name}")
            
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"Collection {collection_name} already exists (race condition)")
                return
            logger.error(f"Failed to create collection {collection_name}: {str(e)}")
            raise

    # ── Core: batched encode + batched upsert ──────────────────
    def add_texts(self, collection_name: str, texts: List[str], metadata: List[Dict] = None):
        """
        Add text chunks to the collection.

        Processes in two phases:
          1. Encode texts via TF-IDF hashing in batches
          2. Upsert points in batches of UPSERT_BATCH_SIZE
        Each upsert micro-batch is retried independently.
        """
        if not texts:
            logger.warning("No texts provided to add_texts")
            return

        total = len(texts)
        logger.info(f"add_texts: {total} texts → collection {collection_name}")

        # Ensure collection exists
        self.create_collection(collection_name)

        # ── Phase 1: generate embeddings in batches ────────────
        logger.info(f"Phase 1/2: encoding {total} texts (batch_size={ENCODE_BATCH_SIZE})")
        all_embeddings = []
        for start in range(0, total, ENCODE_BATCH_SIZE):
            end = min(start + ENCODE_BATCH_SIZE, total)
            batch_texts = texts[start:end]
            batch_embeddings = self._encode_texts(batch_texts)
            all_embeddings.append(batch_embeddings)
            logger.info(f"  Encoded batch {start}-{end} of {total}")

        all_embeddings = np.vstack(all_embeddings)

        # ── Phase 2: build points then upsert in batches ───────
        logger.info(f"Phase 2/2: upserting {total} points (batch_size={UPSERT_BATCH_SIZE})")
        points = []
        for i in range(total):
            payload = {
                "text": texts[i],
                "created_at": datetime.utcnow().isoformat(),
            }
            if metadata and i < len(metadata):
                payload.update(metadata[i])

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=all_embeddings[i].tolist(),
                    payload=payload,
                )
            )

        upserted = 0
        for start in range(0, len(points), UPSERT_BATCH_SIZE):
            end = min(start + UPSERT_BATCH_SIZE, len(points))
            batch = points[start:end]
            self._upsert_with_retry(collection_name, batch)
            upserted += len(batch)
            logger.info(f"  Upserted {upserted}/{total} points")

        logger.info(f"✓ add_texts complete: {total} texts → {collection_name}")

    def _upsert_with_retry(self, collection_name: str, points: List[PointStruct]):
        """Upsert a single micro-batch with exponential backoff retries."""
        delay = UPSERT_RETRY_DELAY
        for attempt in range(UPSERT_RETRY_COUNT):
            try:
                self.client.upsert(
                    collection_name=collection_name,
                    points=points,
                )
                return
            except Exception as e:
                if attempt < UPSERT_RETRY_COUNT - 1:
                    logger.warning(
                        f"Upsert batch failed (attempt {attempt + 1}/{UPSERT_RETRY_COUNT}), "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"Upsert batch failed after {UPSERT_RETRY_COUNT} attempts")
                    raise
    # ───────────────────────────────────────────────────────────

    def delete_collection(self, collection_name: str):
        """Delete a Qdrant collection"""
        try:
            result = self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return result
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "doesn't exist" in error_msg or "404" in error_msg:
                logger.info(f"Collection {collection_name} doesn't exist, nothing to delete")
                return
            logger.error(f"Failed to delete collection {collection_name}: {str(e)}")
            raise Exception(f"Failed to delete collection {collection_name}: {str(e)}")

    def search(self, collection_name: str, query: str, limit: int = 5) -> List[Dict]:
        """Search for similar text chunks"""
        try:
            query_vector = self._encode_texts([query])[0]
            
            search_result = self.client.query_points(
                collection_name=collection_name,
                query=query_vector.tolist(),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            ).points
            
            results = []
            for scored_point in search_result:
                score = float(scored_point.score)
                payload = scored_point.payload
                results.append({
                    "text": payload.get("text", ""),
                    "metadata": {k: v for k, v in payload.items() if k != "text"},
                    "score": score
                })
            
            logger.info(f"Found {len(results)} results for query in {collection_name}")
            for r in results:
                logger.debug(f"Score: {r['score']:.3f} | Text: {r['text'][:100]}...")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching collection {collection_name}: {str(e)}")
            return []

    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """Get information about a collection"""
        try:
            collection_info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": getattr(collection_info, 'vectors_count', 0),
                "points_count": getattr(collection_info, 'points_count', 0),
                "status": str(getattr(collection_info, 'status', 'unknown')),
            }
        except Exception as e:
            logger.error(f"Error getting collection info for {collection_name}: {str(e)}")
            return {
                "name": collection_name,
                "vectors_count": 0,
                "points_count": 0,
                "status": "error"
            }

    def list_collections(self) -> List[str]:
        """List all collections"""
        try:
            collections = self.client.get_collections()
            return [collection.name for collection in collections.collections]
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            return []

    def get_collection_stats(self, collection_name: str) -> Dict:
        """Get statistics for a collection"""
        try:
            collection_info = self.client.get_collection(collection_name)
            return {
                "total_points": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "status": collection_info.status.value if collection_info.status else "unknown"
            }
        except Exception as e:
            logger.error(f"Error getting stats for collection {collection_name}: {str(e)}")
            return {
                "total_points": 0,
                "vectors_count": 0,
                "indexed_vectors_count": 0,
                "status": "error"
            }

    def scroll_collection(self, collection_name: str, limit: int = 100, offset: Optional[str] = None) -> Dict:
        """Scroll through all points in a collection"""
        try:
            result = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            return {
                "points": [
                    {
                        "id": point.id,
                        "payload": point.payload
                    }
                    for point in result[0]
                ],
                "next_page_offset": result[1]
            }
        except Exception as e:
            logger.error(f"Error scrolling collection {collection_name}: {str(e)}")
            return {"points": [], "next_page_offset": None}

    def delete_points(self, collection_name: str, point_ids: List[str]) -> bool:
        """Delete specific points from a collection"""
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(
                    points=point_ids
                )
            )
            logger.info(f"Deleted {len(point_ids)} points from collection {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting points from collection {collection_name}: {str(e)}")
            return False

    def update_payload(self, collection_name: str, point_id: str, payload: Dict) -> bool:
        """Update payload for a specific point"""
        try:
            self.client.set_payload(
                collection_name=collection_name,
                payload=payload,
                points=[point_id]
            )
            logger.info(f"Updated payload for point {point_id} in collection {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating payload for point {point_id}: {str(e)}")
            return False

    def health_check(self) -> Dict:
        """Check Qdrant health and return status"""
        try:
            collections = self.client.get_collections()
            return {
                "status": "healthy",
                "collections_count": len(collections.collections),
                "message": "Qdrant is running and accessible"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "collections_count": 0,
                "message": f"Qdrant connection failed: {str(e)}"
            }
