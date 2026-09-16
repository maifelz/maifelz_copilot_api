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


@router.get("/quota")
async def get_live_quota(connection_id: Optional[str] = None):
    """Retrieve live quota and query usage for the active workspace."""
    tm._load_tenants()
    tenant = None
    if connection_id:
        tenant = tm.get_tenant_by_connection_id(connection_id)
    if not tenant:
        tenants = tm.list_tenants()
        tenant = tenants[0] if tenants else None

    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant workspace configured")

    limit = tenant.get("monthly_limit", 2500)
    used = tenant.get("queries_used", 0)

    return {
        "success": True,
        "tenant": {
            "id": tenant["id"],
            "company_name": tenant["company_name"],
            "plan": tenant["plan"],
            "license_key": tenant["license_key"],
            "status": tenant["status"],
            "connection_id": tenant.get("connection_id", ""),
            "monthly_limit": limit,
            "queries_used": used,
            "remaining_queries": max(0, limit - used),
            "pct_used": min(100, round((used / limit) * 100, 1)) if limit > 0 else 0,
        }
    }
