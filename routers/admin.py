"""
mAifelZ Master Admin Router — Client Provisioning, Licensing & Metering
Exclusively for mAifelZ management.
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
import services.tenant_manager as tm

router = APIRouter(prefix="/admin", tags=["mAifelZ Master Admin"])


class CreateTenantRequest(BaseModel):
    company_name: str
    contact_email: str
    plan: str = "professional"  # starter | professional | enterprise
    connection_id: Optional[str] = None
    custom_limit: Optional[int] = None
    notes: Optional[str] = ""


class UpdateStatusRequest(BaseModel):
    status: str  # active | suspended | expired


class ResetUsageRequest(BaseModel):
    additional_credits: Optional[int] = 0


class LinkLicenseRequest(BaseModel):
    connection_id: str
    license_key: str


@router.get("/summary")
async def get_saas_summary():
    """Get high-level SaaS business metrics: MRR, clients, total queries."""
    return tm.get_admin_summary()


@router.get("/tenants")
async def get_all_tenants():
    """List all client tenants with license keys and query counters."""
    return {"tenants": tm.list_tenants()}


@router.post("/tenants")
async def provision_new_tenant(req: CreateTenantRequest):
    """Provision a new paying customer and generate unique mAifelZ license key."""
    tenant = tm.create_tenant(
        company_name=req.company_name,
        contact_email=req.contact_email,
        plan=req.plan,
        connection_id=req.connection_id,
        custom_limit=req.custom_limit,
        notes=req.notes or "",
    )
    return {"success": True, "tenant": tenant}


@router.post("/tenants/{tenant_id}/status")
async def set_tenant_status(tenant_id: str, req: UpdateStatusRequest):
    """The Kill-Switch: suspend or activate a customer's access instantly."""
    if req.status not in ["active", "suspended", "expired"]:
        raise HTTPException(status_code=400, detail="Status must be 'active', 'suspended', or 'expired'")

    ok = tm.update_tenant_status(tenant_id, req.status)
    if not ok:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {"success": True, "status": req.status}


@router.post("/tenants/{tenant_id}/reset")
async def reset_tenant_credits(tenant_id: str, req: ResetUsageRequest):
    """Reset query count or top-up extra query credits."""
    ok = tm.reset_tenant_usage(tenant_id, req.additional_credits or 0)
    if not ok:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {"success": True, "message": "Usage reset / credits updated"}


class AddUserRequest(BaseModel):
    email: str
    name: str
    role: Optional[str] = "manager"
    password: Optional[str] = None


@router.post("/tenants/{tenant_id}/users")
async def add_tenant_user(tenant_id: str, req: AddUserRequest):
    """Provision a user login seat for this client tenant ($25/seat/mo)."""
    ok, msg, initial_password = tm.add_user_login(
        tenant_id, req.email, req.name, req.role or "manager", req.password
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {
        "success": True,
        "message": msg,
        "initial_password": initial_password,
        "tenant": tm.get_tenant_by_id(tenant_id),
    }


@router.delete("/tenants/{tenant_id}/users/{email}")
async def delete_tenant_user(tenant_id: str, email: str):
    """Remove a user login seat from this tenant."""
    ok, msg = tm.remove_user_login(tenant_id, email)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg, "tenant": tm.get_tenant_by_id(tenant_id)}


class TopupCreditsRequest(BaseModel):
    credits: int


@router.post("/tenants/{tenant_id}/topup")
async def topup_client_credits(tenant_id: str, req: TopupCreditsRequest):
    """Sell and add extra query pack credits to a client."""
    ok, msg = tm.topup_ai_credits(tenant_id, req.credits)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg, "tenant": tm.get_tenant_by_id(tenant_id)}


class VerifyLicenseRequest(BaseModel):
    license_key: str


@router.post("/verify-license")
async def verify_license_endpoint(req: VerifyLicenseRequest):
    """Verify license key called from Odoo addon."""
    tenant = tm.get_tenant_by_license(req.license_key)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid mAifelZ License Key.")

    if tenant.get("status") != "active":
        raise HTTPException(status_code=403, detail=f"Subscription is currently {tenant.get('status').upper()}. Contact billing@maifelz.com")

    return {
        "valid": True,
        "company_name": tenant.get("company_name"),
        "plan": tenant.get("plan"),
        "monthly_limit": tenant.get("monthly_limit"),
        "status": tenant.get("status"),
    }


class OdooHandshakeRequest(BaseModel):
    license_key: str
    odoo_url: str
    db_name: Optional[str] = ""
    company_name: Optional[str] = ""


@router.post("/odoo-handshake")
async def odoo_handshake_endpoint(req: OdooHandshakeRequest):
    """
    Called by Odoo addon when client clicks 'Connect to mAifelZ Cloud'.
    Binds their Odoo instance URL to their license.
    """
    tenant = tm.get_tenant_by_license(req.license_key)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid mAifelZ License Key.")

    if tenant.get("status") != "active":
        raise HTTPException(status_code=403, detail=f"License is currently {tenant.get('status').upper()}. Contact billing@maifelz.com")

    # Update tenant notes/metadata with live Odoo URL
    tenant["odoo_instance_url"] = req.odoo_url
    if req.db_name:
        tenant["odoo_database"] = req.db_name
    tm._save_tenants()

    return {
        "success": True,
        "message": f"Successfully connected {tenant['company_name']} to mAifelZ AI Cloud",
        "company_name": tenant["company_name"],
        "plan": tenant["plan"],
        "monthly_limit": tenant["monthly_limit"],
        "copilot_web_url": "https://copilot.maifelz.com",
    }


class LinkLicenseRequest(BaseModel):
    connection_id: str
    license_key: str


@router.post("/link-license")
async def link_license_to_connection(req: LinkLicenseRequest):
    """Customer enters their mAifelZ license key to activate their Odoo connection."""
    ok, msg = tm.link_connection_to_tenant(req.connection_id, req.license_key)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    return {"success": True, "message": msg}


class AssignConnectionRequest(BaseModel):
    connection_id: str


@router.post("/tenants/{tenant_id}/connection")
async def assign_tenant_connection_endpoint(tenant_id: str, req: AssignConnectionRequest):
    """Assign or switch the Odoo database connection for this client tenant."""
    ok, msg = tm.assign_tenant_connection(tenant_id, req.connection_id)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return {"success": True, "message": msg, "tenant": tm.get_tenant_by_id(tenant_id)}


class ConnectAndAssignRequest(BaseModel):
    url: str
    database: str
    username: str
    password: str
    label: Optional[str] = None


@router.post("/tenants/{tenant_id}/connect-odoo")
async def connect_and_assign_odoo(tenant_id: str, req: ConnectAndAssignRequest):
    """Connect a client's Odoo instance directly from Admin and bind to the tenant."""
    tenant = tm.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    from services.odoo_connector import OdooConnector, save_connection
    connector = OdooConnector(
        url=req.url.strip(),
        database=req.database.strip(),
        username=req.username.strip(),
        password=req.password.strip(),
    )
    success, message = connector.authenticate()
    if not success:
        raise HTTPException(status_code=400, detail=f"Odoo Connection Failed: {message}")

    company = connector.get_company_info()
    company_name = company.get("name", req.label or tenant["company_name"]) if company else (req.label or tenant["company_name"])

    conn_id = save_connection(
        url=connector.url,
        database=req.database.strip(),
        username=req.username.strip(),
        password=req.password.strip(),
        label=req.label or company_name,
        uid=connector.uid,
        odoo_version=connector.odoo_version,
        company_name=company_name,
    )

    tm.assign_tenant_connection(tenant_id, conn_id)
    return {
        "success": True,
        "message": f"Successfully connected to Odoo ({company_name}) and assigned to {tenant['company_name']}",
        "connection_id": conn_id,
        "tenant": tm.get_tenant_by_id(tenant_id),
    }


@router.get("/download-odoo-module")
async def download_odoo_module():
    """Download the official mAifelZ AI Odoo 19 Addon (.zip)."""
    import os
    from fastapi.responses import FileResponse
    zip_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "maifelz_odoo_ai_module.zip")
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Module package not found on server.")
    return FileResponse(
        zip_path,
        filename="maifelz_ai_copilot_v19.zip",
        media_type="application/zip"
    )





