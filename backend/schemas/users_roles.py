"""
Pydantic v2 schemas for Users & Roles RBAC administration.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PermissionOut(BaseModel):
    id: uuid.UUID
    name: str
    module: str
    description: str


class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    is_system: bool
    permissions: List[str] = Field(default_factory=list)
    user_count: int = 0
    created_at: datetime
    updated_at: datetime


class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    description: str = Field(..., min_length=3, max_length=500)
    permissions: List[str] = Field(default_factory=list)


class RolePermissionsUpdateRequest(BaseModel):
    permissions: List[str] = Field(..., description="List of permission names to assign to this role")
    description: Optional[str] = Field(default=None, max_length=500)


class UserAdminOut(BaseModel):
    id: uuid.UUID
    username: Optional[str] = None
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    auth_provider: str
    primary_role: str
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PaginatedUsersOut(BaseModel):
    items: List[UserAdminOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    preferences: Optional[Dict[str, Any]] = None


class UserStatusUpdateRequest(BaseModel):
    is_active: bool
    reason: Optional[str] = Field(default=None, max_length=500)


class UserRolesUpdateRequest(BaseModel):
    roles: List[str] = Field(..., min_length=1, description="Role names to assign to the user")
    reason: Optional[str] = Field(default=None, max_length=500)

