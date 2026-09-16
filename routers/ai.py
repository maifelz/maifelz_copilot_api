"""
mAifelZ AI Odoo Copilot — AI Report Routes
Natural language → Odoo query → AI analysis → structured report.
"""
from fastapi import APIRouter, HTTPException
from models.schemas import PromptRequest, AIReportResponse
from services.odoo_connector import get_connection, get_connector
from services.ai_engine import process_prompt
import services.tenant_manager as tm

from pydantic import BaseModel
import os

router = APIRouter(prefix="/ai", tags=["AI Reports"])


class ApiKeyRequest(BaseModel):
    api_key: str


@router.get("/status")
async def get_ai_status():
    """Check AI engine status and whether an LLM (Gemini, OpenAI, or Groq) is active."""
    g_key = os.getenv("GEMINI_API_KEY", "").strip()
    o_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    if g_key and g_key != "your_gemini_api_key_here":
        return {
            "gemini_active": True,
            "engine": "Google Gemini 2.0 Flash Active",
            "provider": "gemini",
            "key_preview": f"{g_key[:6]}...{g_key[-4:]}"
        }
    elif o_key:
        provider_name = "Groq Llama 3" if "gsk" in o_key else "OpenAI GPT-4o"
        return {
            "gemini_active": True,
            "engine": f"{provider_name} Active",
            "provider": "openai",
            "key_preview": f"{o_key[:6]}...{o_key[-4:]}"
        }
    else:
        return {
            "gemini_active": False,
            "engine": "Smart BI Rules (Connect Gemini or OpenAI for Conversational AI)",
            "provider": "rules",
            "key_preview": None
        }


@router.post("/api-key")
async def save_api_key(req: ApiKeyRequest):
    """Save or update LLM API key (auto-detects Gemini vs OpenAI vs Groq)."""
    clean_key = req.api_key.strip()
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    
    if clean_key.startswith("sk-"):
        # OpenAI Key
        os.environ["OPENAI_API_KEY"] = clean_key
        var_name = "OPENAI_API_KEY"
        provider = "OpenAI GPT-4o"
    elif clean_key.startswith("gsk_"):
        # Groq Key
        os.environ["OPENAI_API_KEY"] = clean_key
        os.environ["OPENAI_BASE_URL"] = "https://api.groq.com/openai/v1"
        var_name = "OPENAI_API_KEY"
        provider = "Groq Llama 3"
    else:
        # Google Gemini Key
        os.environ["GEMINI_API_KEY"] = clean_key
        var_name = "GEMINI_API_KEY"
        provider = "Google Gemini"

    # Save to .env
    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = [l for l in f.readlines() if not l.startswith(f"{var_name}=")]
        lines.insert(0, f"{var_name}={clean_key}\n")
        with open(env_path, "w") as f:
            f.writelines(lines)
    except Exception:
        pass
        
    return {"success": True, "message": f"{provider} activated successfully!"}


@router.post("/report", response_model=AIReportResponse)
async def generate_ai_report(request: PromptRequest):
    """
    Core endpoint: Convert a natural language prompt to a full AI report.
    
    Example prompts:
    - "Show me top 10 customers by revenue this year"
    - "What are our overdue invoices?"
    - "Compare sales performance by salesperson this quarter"
    - "Which products have the lowest stock levels?"
    """
    conn = get_connection(request.connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Odoo connection not found. Please add a connection first.")
    
    connector = get_connector(request.connection_id)
    if not connector:
        raise HTTPException(status_code=500, detail="Failed to build Odoo connector")

    # ── mAifelZ License & AI Query Limit Enforcement ──
    allowed, error_msg, tenant = tm.verify_and_meter_query(request.connection_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=error_msg)

    try:
        result = await process_prompt(connector, request.prompt)
        return AIReportResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing error: {str(e)}")


@router.get("/suggestions/{connection_id}")
async def get_prompt_suggestions(connection_id: str):
    """Return smart prompt suggestions based on the connected Odoo instance."""
    conn = get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # These are universal smart suggestions that work on any Odoo
    suggestions = [
        {
            "category": "Sales",
            "icon": "trending-up",
            "prompts": [
                "Top 10 customers by total revenue this year",
                "Sales performance by salesperson this quarter",
                "Monthly revenue trend for the past 6 months",
                "Quotations pending confirmation",
            ]
        },
        {
            "category": "Finance",
            "icon": "dollar-sign",
            "prompts": [
                "Outstanding invoices and overdue amounts",
                "Cash collection status by customer",
                "Invoice payment rate analysis",
                "Monthly cash inflow vs outflow",
            ]
        },
        {
            "category": "CRM & Pipeline",
            "icon": "users",
            "prompts": [
                "Sales pipeline by stage overview",
                "Leads by salesperson and expected revenue",
                "Win rate analysis by product category",
                "Deals closing this month",
            ]
        },
        {
            "category": "Inventory",
            "icon": "package",
            "prompts": [
                "Products with critically low stock levels",
                "Top 20 products by stock value",
                "Incoming shipments expected this week",
                "Slow-moving inventory analysis",
            ]
        },
        {
            "category": "Purchasing",
            "icon": "shopping-cart",
            "prompts": [
                "Top 10 vendors by purchase volume",
                "Purchase orders pending approval",
                "Monthly procurement spend trend",
                "Vendor payment terms analysis",
            ]
        },
    ]
    
    return {"connection_id": connection_id, "suggestions": suggestions}


@router.get("/quick-stats/{connection_id}")
async def get_quick_stats(connection_id: str):
    """Get quick KPI stats for the dashboard overview."""
    connector = get_connector(connection_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    stats = {}
    
    # Try each stat, gracefully skip if model unavailable
    try:
        orders = connector.search_read(
            "sale.order", [["state", "in", ["sale", "done"]]], ["amount_total"], limit=1000
        )
        total_revenue = sum(o.get("amount_total", 0) for o in orders)
        stats["total_revenue"] = {
            "value": f"${total_revenue:,.0f}",
            "count": len(orders),
            "label": "Total Sales Revenue"
        }
    except Exception:
        pass
    
    try:
        invoices = connector.search_read(
            "account.move",
            [["move_type", "=", "out_invoice"], ["payment_state", "!=", "paid"], ["state", "=", "posted"]],
            ["amount_residual"], limit=500
        )
        outstanding = sum(i.get("amount_residual", 0) for i in invoices)
        stats["outstanding_invoices"] = {
            "value": f"${outstanding:,.0f}",
            "count": len(invoices),
            "label": "Outstanding Invoices"
        }
    except Exception:
        pass
    
    try:
        leads = connector.search_read(
            "crm.lead", [["type", "=", "opportunity"]], ["expected_revenue"], limit=500
        )
        pipeline_value = sum(l.get("expected_revenue", 0) for l in leads)
        stats["pipeline_value"] = {
            "value": f"${pipeline_value:,.0f}",
            "count": len(leads),
            "label": "Pipeline Value"
        }
    except Exception:
        pass
    
    try:
        customers = connector.search_read(
            "res.partner", [["customer_rank", ">", 0], ["active", "=", True]], ["id"], limit=1
        )
        # Just count
        total_customers = connector.execute("res.partner", "search_count", [["customer_rank", ">", 0]])
        stats["total_customers"] = {
            "value": f"{total_customers:,}",
            "count": total_customers,
            "label": "Active Customers"
        }
    except Exception:
        pass
    
    return {"stats": stats}
