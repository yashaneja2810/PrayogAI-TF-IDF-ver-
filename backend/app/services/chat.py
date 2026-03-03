from typing import List, Optional
import pickle
import asyncio
from datetime import datetime
from fastapi import HTTPException, status
from ..log_config import logger
from ..core.config import get_settings
from .vector_store import VectorStoreService
from .auth import AuthService
from .ai_service import AIService
from threading import Lock

settings = get_settings()

class ChatService:
    _instance = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ChatService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            if not self._initialized:
                self.vector_store = VectorStoreService()
                self.auth_service = AuthService()
                self.ai_service = AIService()
                self._initialized = True
    
    def _get_collection_name(self, bot_id: str) -> str:
        """Generate collection name for a bot"""
        return f"bot_{bot_id}"
    
    async def verify_bot_access(self, bot_id: str, user_id: Optional[str], token: str = None) -> dict:
        """Verify user has access to the bot"""
        from ..log_config import logger
        try:
            logger.info(f"Verifying access for bot {bot_id} and user {user_id}")
            
            # Skip ownership check for anonymous users (public widget access)
            if user_id is None:
                logger.info(f"Anonymous access - skipping ownership check for bot {bot_id}")
                return {"bot_id": bot_id}  # Return minimal bot info
            
            # Get all user's bots first
            bots = await self.auth_service.get_user_bots(user_id, token)
            logger.info(f"Found {len(bots)} bots for user. Bot IDs: {[b.get('id', 'N/A') for b in bots]}")
            
            # Try both bot_id and id fields for matching, and normalize UUIDs
            matching_bot = next(
                (bot for bot in bots if 
                 str(bot.get('bot_id', '')).replace('-', '').lower() == str(bot_id).replace('-', '').lower() or
                 str(bot.get('id', '')).replace('-', '').lower() == str(bot_id).replace('-', '').lower()
                ), None)
            
            if not matching_bot:
                logger.error(f"Bot {bot_id} not found in user's bots. Available bots: {[b.get('bot_id', 'N/A') for b in bots]}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied for this bot"
                )
                
            logger.info(f"Access verified for bot {bot_id}. Bot details: {matching_bot}")
            return matching_bot
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during bot access verification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error verifying bot access: {str(e)}"
            )

    async def get_bot_documents(self, bot_id: str, user_id: str, token: str = None) -> dict:
        """Get all documents associated with a bot from the vector store"""
        from ..log_config import logger
        try:
            # Verify bot access
            await self.verify_bot_access(bot_id, user_id, token)
            
            # Get the collection name for this bot
            collection_name = self._get_collection_name(bot_id)
            logger.info(f"Looking for documents in collection: {collection_name}")
            
            # Get collection info from Qdrant
            collection_info = self.vector_store.get_collection_info(collection_name)
            
            if not collection_info:
                logger.info(f"No collection found for bot {bot_id}")
                return {"documents": []}
            
            try:
                scroll_result = self.vector_store.scroll_collection(collection_name, limit=100)
                points = scroll_result.get("points", [])
                
                if not points:
                    logger.info(f"No documents found in collection {collection_name}")
                    return {"documents": []}
                
                # Group points by filename
                file_groups = {}
                for point in points:
                    payload = point.get("payload", {})
                    filename = payload.get("filename", "unknown_document.txt")
                    
                    if filename not in file_groups:
                        file_groups[filename] = {
                            "chunks": [],
                            "total_length": 0,
                            "original_file_size": payload.get("original_file_size", 0),
                            "created_at": payload.get("created_at", datetime.now().isoformat())
                        }
                    
                    file_groups[filename]["chunks"].append(payload.get("text", ""))
                    file_groups[filename]["total_length"] += payload.get("chunk_length", 0)
                
                documents = []
                for i, (filename, data) in enumerate(file_groups.items()):
                    file_size = data["original_file_size"] if data["original_file_size"] > 0 else data["total_length"]
                    preview_text = ""
                    if data["chunks"]:
                        preview_text = data["chunks"][0][:100] + "..." if len(data["chunks"][0]) > 100 else data["chunks"][0]
                    
                    documents.append({
                        "id": str(i),
                        "bot_id": bot_id,
                        "filename": filename,
                        "file_size": file_size,
                        "created_at": data["created_at"],
                        "text": preview_text,
                        "chunk_count": len(data["chunks"])
                    })
                
                logger.info(f"Successfully retrieved {len(documents)} documents for bot {bot_id}")
                return {"documents": documents}
                
            except Exception as e:
                logger.error(f"Error getting documents from Qdrant for bot {bot_id}: {str(e)}")
                stats = self.vector_store.get_collection_stats(collection_name)
                documents = [{
                    "id": "collection_info",
                    "bot_id": bot_id,
                    "filename": f"Documents ({stats.get('total_points', 0)} chunks)",
                    "file_size": stats.get("total_points", 0) * 500,
                    "created_at": datetime.now().isoformat(),
                    "text": f"This bot contains {stats.get('total_points', 0)} text chunks from uploaded documents.",
                    "chunk_count": stats.get("total_points", 0)
                }]
                return {"documents": documents}
                
        except Exception as e:
            logger.error(f"Error in get_bot_documents: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving documents: {str(e)}"
            )

    async def get_response(self, bot_id: str, user_id: Optional[str], query: str, token: str = None) -> str:
        """Get response from Gemini based on context from vector store"""
        try:
            bot = await self.verify_bot_access(bot_id, user_id, token)
            collection_name = self._get_collection_name(bot_id)
            
            # 🔹 Improved retrieval
            # Retrieve top-5 chunks — enough context, minimal tokens
            results = self.vector_store.search(collection_name, query, limit=5)

            if not results:
                return "I don't have any relevant information to answer your question right now."

            # Deduplicate, filter low-score noise, truncate each chunk to 500 chars
            seen = set()
            context_chunks = []
            for result in results:
                text = result.get("text", "").strip()
                score = result.get("score", 0)
                if score >= 0.10 and text and text not in seen:
                    seen.add(text)
                    context_chunks.append(text[:500])

            if not context_chunks:
                # Use top-3 results regardless of score instead of a second Qdrant call
                context_chunks = [
                    r.get("text", "").strip()[:500]
                    for r in results[:3]
                    if r.get("text", "").strip()
                ]

            context = "\n".join(f"- {chunk}" for chunk in context_chunks[:5])
            bot_name = bot.get('name', 'an AI assistant')

            # Compact prompt (~120 tokens vs old ~700) — same quality, far fewer tokens
            prompt = f"""You are {bot_name}, a knowledgeable assistant. Answer using ONLY the knowledge below.
- Speak naturally like a human expert. Be concise: 2-4 sentences for simple questions.
- Never mention "documents", "files", "context", "data", or any internal mechanism.
- Understand synonyms: owner=seller, phone=contact, price=cost, available=in stock.
- Skip garbled/broken characters — describe elements in plain words instead.
- If not in the knowledge, say "I don't have that information right now."
- Use **bold** only for names/prices. Lists only for 3+ distinct items. Never repeat the question.

Knowledge:
{context}

Question: {query}
Answer:"""
            try:
                response_text = await self.ai_service.generate_response(prompt)
                if not response_text or len(response_text.strip()) == 0:
                    return "I'm sorry, I couldn't generate a meaningful response at this time. Please try again."
                return response_text.strip()
            except Exception as e:
                logger.error(f"Gemini API error for bot {bot_id}: {e}", exc_info=True)
                return "I apologize, but I'm having trouble generating a response right now. Please try again later."
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating response: {str(e)}"
            )

    async def process_documents(self, bot_id: str, user_id: str, texts: List[str], filenames: List[str] = None, file_sizes: List[int] = None):
        """
        Process and store document chunks in vector store.

        Sends chunks in batches of PROCESS_BATCH to add_texts, which
        itself handles micro-batch upserts and per-batch retries.
        """
        PROCESS_BATCH = 100  # chunks per add_texts call

        try:
            collection_name = self._get_collection_name(bot_id)
            total = len(texts)
            logger.info(f"process_documents: {total} chunks for bot {bot_id}")

            # Ensure collection exists
            try:
                self.vector_store.create_collection(collection_name)
                logger.info(f"Created collection {collection_name}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    raise
                logger.info(f"Collection {collection_name} already exists")

            # Build full metadata list
            metadata = []
            for i, text in enumerate(texts):
                chunk_meta = {
                    "bot_id": bot_id,
                    "user_id": user_id,
                    "chunk_index": i,
                    "chunk_length": len(text),
                }
                if filenames and i < len(filenames):
                    chunk_meta["filename"] = filenames[i]
                elif filenames and len(filenames) == 1:
                    chunk_meta["filename"] = filenames[0]
                else:
                    chunk_meta["filename"] = f"document_chunk_{i}"

                if file_sizes and i < len(file_sizes):
                    chunk_meta["original_file_size"] = file_sizes[i]

                metadata.append(chunk_meta)

            # Feed to vector store in manageable batches
            for start in range(0, total, PROCESS_BATCH):
                end = min(start + PROCESS_BATCH, total)
                batch_texts = texts[start:end]
                batch_meta = metadata[start:end]
                logger.info(f"  Sending batch {start}-{end} of {total} to add_texts")
                self.vector_store.add_texts(collection_name, batch_texts, batch_meta)

            logger.info(f"✓ process_documents complete: {total} chunks stored for bot {bot_id}")

        except Exception as e:
            logger.error(f"Error processing documents for bot {bot_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing documents: {str(e)}"
            )
