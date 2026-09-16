"""
mAifelZ Customer Authentication Router
Handles per-seat logins ($25/seat) configured in mAifelZ Master Admin.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
import services.tenant_manager as tm

router = APIRouter(prefix="/auth", tags=["mAifelZ Customer Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(req: LoginRequest):
    """Authenticate customer user login and return tenant workspace details."""
    success, message, user, tenant = tm.authenticate_user(req.email, req.password)
    if not success:
        raise HTTPException(status_code=401, detail=message)

    return {
        "success": True,
        "message": "Welcome to mAifelZ AI Copilot",
        "user": user,
        "tenant": {
            "id": tenant["id"],
            "company_name": tenant["company_name"],
            "license_key": tenant["license_key"],
            "plan": tenant["plan"],
            "status": tenant["status"],
            "connection_id": tenant.get("connection_id", ""),
            "monthly_limit": tenant.get("monthly_limit", 500),
            "queries_used": tenant.get("queries_used", 0),
        },
    }
