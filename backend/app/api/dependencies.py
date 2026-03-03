from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Cookie, Header
from fastapi.security import OAuth2PasswordBearer
from ..services.auth import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
auth_service = AuthService()

async def get_current_user(
    session: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Depends(oauth2_scheme)
) -> dict:
    """
    Dependency to get the current authenticated user.
    Supports both session cookies (for Swagger/browser) and bearer tokens (for frontend).
    Returns the full user object from Supabase.
    """
    from ..log_config import logger
    
    auth_error = None
    
    # Try bearer token first (from Authorization header or oauth2_scheme)
    bearer_token = None
    if authorization and authorization.startswith("Bearer "):
        bearer_token = authorization.split(" ")[1]
        logger.debug("Using token from Authorization header")
    elif token:
        bearer_token = token
        logger.debug("Using token from oauth2_scheme")
        
    if bearer_token:
        try:
            response = await auth_service.verify_token(bearer_token)
            if response:
                # Handle different response types
                if hasattr(response, 'session') and response.session and response.session.user:
                    logger.info(f"Authenticated via session")
                    return response.session.user.model_dump()
                elif hasattr(response, 'user') and response.user:
                    logger.info(f"Authenticated via user data")
                    return response.user.model_dump()
        except Exception as e:
            auth_error = e
            logger.error(f"Bearer token authentication failed: {str(e)}")
            
    # Try session cookie
    if session:
        try:
            user_data = await auth_service.verify_session(session)
            if user_data:
                return user_data
        except Exception as e:
            if not auth_error:  # Only store if we don't already have a bearer token error
                auth_error = e
            logger.error(f"Session authentication failed: {str(e)}")
    
    # If we get here, both auth methods failed
    if auth_error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(auth_error)
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )

async def get_current_active_user(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    Dependency to get the current active user.
    Can be extended to check for user status, roles, etc.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    return current_user