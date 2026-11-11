"""
Authentication and session schemas for ParallaxAI.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: Optional[str] = Field(default=None)
    accept_terms: bool = Field(default=True)
    username: Optional[str] = Field(default=None, min_length=3, max_length=64)

    @model_validator(mode="after")
    def validate_registration(self) -> "RegisterRequest":
        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not self.accept_terms:
            raise ValueError("Terms of service must be accepted")
        return self


class LoginRequest(BaseModel):
    email: Optional[str] = Field(default=None)
    username: Optional[str] = Field(default=None)
    identifier_field: Optional[str] = Field(default=None, alias="identifier")
    password: str = Field(..., min_length=1)
    remember_me: bool = Field(default=False)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def check_identifier(self) -> "LoginRequest":
        identifier = (self.email or self.username or self.identifier_field or "").strip()
        if not identifier:
            raise ValueError("Email or username is required")
        return self

    @property
    def identifier(self) -> str:
        return (self.email or self.username or self.identifier_field or "").strip()


class UserAuthOut(BaseModel):
    id: uuid.UUID
    username: Optional[str] = None
    email: str
    full_name: str
    role: str
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    is_active: bool = True
    is_verified: bool = False
    auth_provider: str = "local"
    preferences: Dict[str, Any] = Field(default_factory=dict)
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    token: str  # Legacy compatibility field for existing Streamlit frontend
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: UserAuthOut


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: Optional[str] = None

    @model_validator(mode="after")
    def check_match(self) -> "ChangePasswordRequest":
        if self.confirm_password is not None and self.new_password != self.confirm_password:
            raise ValueError("New passwords do not match")
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")
        return self


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    status: str
    email_provider_configured: bool
    message: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: Optional[str] = None

    @model_validator(mode="after")
    def check_passwords(self) -> "ResetPasswordRequest":
        if self.confirm_password is not None and self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class SessionInfoOut(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    is_revoked: bool
    expires_at: datetime
    created_at: datetime


class AuthProvidersStatusOut(BaseModel):
    local_enabled: bool = True
    google_oauth_enabled: bool = False
    google_oauth_message: str
    password_reset_email_enabled: bool = False
    password_reset_message: str

