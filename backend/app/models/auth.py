from pydantic import BaseModel, EmailStr
from .user import User

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    message: str
    user: User

class Token(BaseModel):
    access_token: str
    refresh_token: str
    user: dict