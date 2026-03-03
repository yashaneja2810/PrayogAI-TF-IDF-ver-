from datetime import datetime
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from ..models.auth import UserCreate, UserLogin
from ..models.user import User
from ..services.auth import AuthService
from ..log_config import logger

router = APIRouter()
auth_service = AuthService()

@router.post("/register")
async def register(user: UserCreate, response: Response):
    """Register a new user and set session cookie"""
    auth_data = await auth_service.sign_up(user.email, user.password)
    
    # Convert user data to our User model
    user_data = auth_data["user"]
    user_model = User(**user_data)
    
    # Create response with serialized user data
    response_data = {
        "message": "Registration successful",
        "user": user_model.dict()
    }
    
    # Set session cookie
    response = JSONResponse(content=response_data)
    response.set_cookie(
        key="session",
        value=auth_data["session"],
        httponly=True,
        secure=True,
        samesite='strict'
    )
    return response

@router.post("/login")
async def login(user: UserLogin, response: Response):
    """Login user and set session cookie"""
    auth_data = await auth_service.sign_in(user.email, user.password)
    
    # Convert user data to our User model
    user_data = auth_data["user"]
    user_model = User(**user_data)
    
    # Fetch user's bots with the access token
    user_bots = await auth_service.get_user_bots(user_model.id, auth_data["access_token"])
    
    # Create response with user data and access token
    response_data = {
        "message": "Login successful",
        "user": user_model.dict(),
        "bots": user_bots,
        "access_token": auth_data["access_token"],
        "refresh_token": auth_data.get("refresh_token"),
        "token_type": "bearer"
    }
    
    # Set session cookie if available
    response = JSONResponse(content=response_data)
    if "session" in auth_data and auth_data["session"]:
        response.set_cookie(
            key="session",
            value=auth_data["session"],
            httponly=True,
            secure=True,
            samesite='strict',
            max_age=1800  # 30 minutes
        )
    return response

@router.post("/logout")
async def logout(response: Response):
    """Clear session cookie and sign out from Supabase"""
    try:
        # Sign out from Supabase
        auth_service.client.auth.sign_out()
    except Exception as e:
        logger.error(f"Error during Supabase sign out: {str(e)}")
    
    # Clear session cookie
    response = JSONResponse(content={"message": "Logout successful"})
    response.delete_cookie(key="session", secure=True, httponly=True, samesite='strict')
    return response