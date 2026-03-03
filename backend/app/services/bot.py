from fastapi import HTTPException, status
from .auth import AuthService
from .vector_store import VectorStoreService
from ..log_config import logger

from threading import Lock

class BotService:
    _instance = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BotService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            if not self._initialized:
                self.auth_service = AuthService()
                self.vector_store = VectorStoreService()
                self._initialized = True

    async def delete_bot(self, bot_id: str, user_id: str, token: str = None) -> None:
        """Delete a bot and all its associated data"""
        try:
            # First verify the user owns this bot
            bots = await self.auth_service.get_user_bots(user_id, token)
            if not any(bot["bot_id"] == bot_id for bot in bots):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this bot"
                )
            
            # Delete vector store collection first
            collection_name = f"bot_{bot_id}"
            try:
                self.vector_store.delete_collection(collection_name)
                logger.info(f"Successfully deleted Qdrant collection: {collection_name}")
            except Exception as e:
                logger.error(f"Error deleting vector store collection: {str(e)}")
                # Continue with database deletion even if vector store deletion fails
            
            # Delete bot from database using authenticated client
            if token:
                from supabase import create_client
                from ..core.config import settings
                auth_client = create_client(settings.VITE_SUPABASE_URL, settings.VITE_SUPABASE_ANON_KEY)
                auth_client.postgrest.auth(token)
                response = auth_client.table('bot_info').delete().eq('bot_id', bot_id).execute()
            else:
                response = self.auth_service.client.table('bot_info').delete().eq('bot_id', bot_id).execute()
            
            if not response.data:
                logger.warning(f"No bot found with bot_id {bot_id} in database")
                # Don't raise error since Qdrant collection was already deleted
            else:
                logger.info(f"Successfully deleted bot {bot_id} from database")
                
            logger.info(f"Successfully deleted bot {bot_id} and its data")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting bot: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting bot: {str(e)}"
            )