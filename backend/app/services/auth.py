from datetime import datetime
from typing import Optional, Dict
import uuid
import asyncio
from fastapi import HTTPException, status
from supabase import create_client, Client
from ..core.config import settings
from ..log_config import logger
from ..models.user import User
from ..models.bot import Bot

from threading import Lock

class AuthService:
    _instance = None
    _client: Optional[Client] = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AuthService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            if not self._initialized:
                logger.info(f"Initializing Supabase client with URL: {settings.VITE_SUPABASE_URL}")
                if not settings.VITE_SUPABASE_URL or not settings.VITE_SUPABASE_ANON_KEY:
                    raise ValueError("Supabase URL or Anon Key not set in environment variables")
                    
                # Initialize client in a clean state
                try:
                    self._client = create_client(settings.VITE_SUPABASE_URL, settings.VITE_SUPABASE_ANON_KEY)
                    # Clear any existing session
                    self._client.auth.sign_out()
                    logger.info("Supabase client initialized successfully")
                except Exception as e:
                    logger.error(f"Error initializing Supabase client: {str(e)}")
                    raise
                
                self._initialized = True

    @property
    def client(self) -> Client:
        return self._client

    async def sign_up(self, email: str, password: str) -> Dict:
        """Register a new user"""
        try:
            # Remove await as sign_up is not async
            auth_response = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            # Convert the response to match Token model format
            user_data = auth_response.user.model_dump() if auth_response.user else {}
            user = User(**user_data)
            
            data = {
                "access_token": auth_response.session.access_token if auth_response.session else None,
                "refresh_token": auth_response.session.refresh_token if auth_response.session else None,
                "user": user.model_dump()
            }
            return data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    async def sign_in(self, email: str, password: str) -> Dict:
        """Login an existing user"""
        try:
            logger.info(f"Attempting login for email: {email}")
            
            # Use a fresh client for sign-in to avoid overwriting the shared client's session
            login_client = create_client(settings.VITE_SUPABASE_URL, settings.VITE_SUPABASE_ANON_KEY)

            # Sign in with email/password
            auth_response = login_client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not auth_response or not auth_response.session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid login response"
                )
            
            # Validate session data
            session = auth_response.session
            if not session.access_token or not session.refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session tokens"
                )
            
            # Validate user data
            if not auth_response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User data missing from response"
                )
            
            user = User(**auth_response.user.model_dump())
            
            # Prepare response data (do NOT set session on the shared client)
            data = {
                "session": session.access_token,
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_in": session.expires_in,
                "expires_at": session.expires_at,
                "user": user.model_dump()
            }
            
            logger.info(f"Login successful for {email}")
            return data
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error for {email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )

    async def get_user_bots(self, user_id: str, token: str = None) -> list:
        """Get all bots for a user"""
        try:
            logger.info(f"Fetching bots for user {user_id}")
            
            # Use authenticated client with proper headers
            if token:
                try:
                    # Create a new client and set the authorization header directly on the postgrest client
                    auth_client = create_client(settings.VITE_SUPABASE_URL, settings.VITE_SUPABASE_ANON_KEY)
                    # Set the authorization header on the postgrest client
                    auth_client.postgrest.auth(token)
                    logger.info(f"Set auth token on postgrest client")
                    response = auth_client.table('bot_info').select('*').eq('user_id', user_id).execute()
                except Exception as e:
                    logger.error(f"Error with authenticated client: {str(e)}")
                    # Fallback to regular client
                    response = self.client.table('bot_info').select('*').eq('user_id', user_id).execute()
            else:
                response = self.client.table('bot_info').select('*').eq('user_id', user_id).execute()
            
            logger.info(f"Supabase query response: status_code={getattr(response, 'status_code', 'N/A')}")
            logger.info(f"Supabase query response data: {response.data}")
            logger.info(f"Supabase query response count: {getattr(response, 'count', 'N/A')}")
            
            if not response.data:
                logger.info(f"No bots found for user {user_id}")
                return []

            logger.info(f"Raw bot data: {response.data}")
            
            bots = []
            for bot in response.data:
                bots.append({
                    'id': bot.get('id', str(uuid.uuid4())),
                    'bot_id': bot.get('bot_id'),
                    'name': bot.get('name', 'Unnamed Bot'),
                    'company_name': bot.get('name', 'Unnamed Bot'),
                    'created_at': bot.get('created_at', datetime.utcnow().isoformat()),
                    'status': 'ready',
                    'user_id': user_id
                })
            
            logger.info(f"Mapped bot data: {bots}")
            return bots
            
        except Exception as e:
            logger.error(f"Error in get_user_bots: {str(e)}")
            return []

    async def verify_token(self, token: str):
        """Verify the JWT token and return the user data (stateless, no shared session mutation)"""
        try:
            # Use get_user(token) directly — this is stateless and does not
            # overwrite the shared client's session, so multiple users work.
            user_response = self.client.auth.get_user(token)
            if user_response and user_response.user:
                logger.info(f"Token verified successfully for user {user_response.user.id}")
                return user_response

            # If we get here, verification failed
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}"
            )

    async def create_bot(self, user_id: str, name: str = "My Bot") -> str:
        """Create a bot and return its ID"""
        try:

            # Create bot with retry mechanism
            max_retries = 3
            retry_delay = 1  # seconds
            bot_id = str(uuid.uuid4())
            last_error = None

            for attempt in range(max_retries):
                try:
                    # Use RPC to insert bot with proper RLS
                    response = self.client.rpc(
                        'create_bot',
                        {
                            'p_bot_id': bot_id,
                            'p_user_id': user_id,
                            'p_name': name,
                            'p_created_at': datetime.utcnow().isoformat()
                        }
                    ).execute()

                    if not response.data:
                        raise Exception("No data returned from bot creation")

                    logger.info(f"Successfully created bot {bot_id} for user {user_id}")
                    return bot_id

                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    
                    if "violates row-level security policy" in error_msg.lower():
                        # This is a permissions issue, no point in retrying
                        logger.error(f"RLS policy violation when creating bot: {error_msg}")
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="You don't have permission to create bots"
                        )
                        
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {retry_delay} seconds: {error_msg}")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        logger.error(f"All attempts to create bot failed: {error_msg}")
                        
            raise last_error

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating bot: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating bot: {str(e)}"
            )
            
    async def verify_session(self, session: str):
        """Verify the session and return the user data (stateless, no shared session mutation)"""
        try:
            # Use get_user(token) directly — stateless, does not overwrite shared client session
            user = self.client.auth.get_user(session)
            if user and user.user:
                logger.info(f"Session verified for user {user.user.id}")
                return user.user.model_dump()
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Session verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Session verification failed: {str(e)}"
            )