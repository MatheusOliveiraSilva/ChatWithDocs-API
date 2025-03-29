from typing import Optional
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    username: str
    email: Optional[EmailStr] = None

class Auth0TokenRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None
    state: Optional[str] = None

class Auth0TokenResponse(BaseModel):
    access_token: str
    id_token: str
    token_type: str
    expires_in: int

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    picture: Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None 