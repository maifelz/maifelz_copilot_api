"""
mAifelZ AI Odoo Copilot — Odoo API Routes
Handles Odoo database connections, testing, and model exploration.
"""
from fastapi import APIRouter, HTTPException
from models.schemas import (
    OdooConnectionRequest,
    OdooConnectionResponse,
    OdooModelsResponse,
    ConnectionStatus,
)
from services.odoo_connector import (
    OdooConnector,
    save_connection,
    get_connection,
    list_connections,
    remove_connection,
)
import uuid

router = APIRouter(prefix="/odoo", tags=["Odoo Connection"])


@router.post("/connect", response_model=OdooConnectionResponse)
async def connect_odoo(request: OdooConnectionRequest):
    """
    Test and save a connection to an Odoo database.
    Works with Odoo v12–v18+, any hosting (Odoo.sh, SaaS, On-Prem).
    """
    connector = OdooConnector(
        url=request.url.strip(),
        database=request.database.strip(),  # Critical: remove trailing/leading spaces
        username=request.username.strip(),
        password=request.password.strip(),
    )
    
    success, message = connector.authenticate()
    
    if not success:
        return OdooConnectionResponse(
            success=False,
            connection_id="",
            label=request.label or request.url,
            error=message,
        )
    
    # Get company info
    company = connector.get_company_info()
    company_name = company.get("name", "Unknown Company") if company else "Unknown"
    
    # Save connection with the resolved working URL
    connection_id = save_connection(
        url=connector.url,
        database=request.database.strip(),
        username=request.username.strip(),
        password=request.password.strip(),
        label=request.label or company_name,
        uid=connector.uid,
        odoo_version=connector.odoo_version,
        company_name=company_name,
    )
    
    return OdooConnectionResponse(
        success=True,
        connection_id=connection_id,
        label=request.label or company_name,
        odoo_version=connector.odoo_version,
        uid=connector.uid,
        company_name=company_name,
    )


@router.get("/connections")
async def get_connections():
    """List all saved Odoo connections."""
    return {"connections": list_connections()}


@router.get("/connections/{connection_id}")
async def get_connection_detail(connection_id: str):
    """Get details of a specific connection."""
    conn = get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    # Don't expose password
    safe_conn = {k: v for k, v in conn.items() if k != "password"}
    return safe_conn


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str):
    """Remove a saved Odoo connection."""
    if remove_connection(connection_id):
        return {"success": True, "message": "Connection removed"}
    raise HTTPException(status_code=404, detail="Connection not found")


@router.get("/connections/{connection_id}/models", response_model=OdooModelsResponse)
async def get_odoo_models(connection_id: str):
    """List all available Odoo models for a connection."""
    conn = get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    connector = OdooConnector(
        url=conn["url"],
        database=conn["database"],
        username=conn["username"],
        password=conn["password"],
    )
    connector.uid = conn["uid"]
    
    try:
        models = connector.get_available_models()
        return OdooModelsResponse(models=models[:200])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


@router.get("/connections/{connection_id}/test", response_model=ConnectionStatus)
async def test_connection(connection_id: str):
    """Test if a saved connection is still active."""
    from datetime import datetime
    
    conn = get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    connector = OdooConnector(
        url=conn["url"],
        database=conn["database"],
        username=conn["username"],
        password=conn["password"],
    )
    
    success, _ = connector.authenticate()
    
    return ConnectionStatus(
        connection_id=connection_id,
        is_active=success,
        last_tested=datetime.utcnow().isoformat(),
    )
