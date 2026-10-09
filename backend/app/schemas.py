from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    """Validate the email and password submitted during login."""

    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access: str
    refresh: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh: str


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class PostRead(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    author_username: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentRead(BaseModel):
    id: int
    content: str
    post_id: int
    author_id: int
    author_username: str
    created_at: datetime
