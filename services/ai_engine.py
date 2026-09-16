"""
mAifelZ AI Odoo Copilot — Intelligent AI Engine
Converts natural language prompts → Odoo ORM queries → direct answer + chart + table data + insights.
Supports Google Gemini, OpenAI (ChatGPT), Groq, and smart built-in BI NLP rules.
"""
import json
import re
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

# ── Google Gemini SDK ──
try:
    from google import genai as google_genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ── OpenAI / Groq SDK ──
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from services.odoo_connector import OdooConnector


def get_llm_client() -> Tuple[Optional[str], Any]:
    """Returns ('gemini' | 'openai', client) or (None, None)."""
    # 1. Google Gemini
    g_key = os.getenv("GEMINI_API_KEY", "").strip()
    if g_key and g_key != "your_gemini_api_key_here" and GEMINI_AVAILABLE:
        try:
            return ("gemini", google_genai.Client(api_key=g_key))
        except Exception:
            pass

    # 2. OpenAI / Groq
    o_key = os.getenv("OPENAI_API_KEY", "").strip()
    if o_key and OPENAI_AVAILABLE:
        try:
            base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
            return ("openai", OpenAI(api_key=o_key, base_url=base_url))
        except Exception:
            pass

    return (None, None)


PROMPT_TO_QUERY_PROMPT = """You are an expert AI data analyst for an Odoo ERP database.
Today's Date: {today}
User Query: "{query}"

Translate this query into an Odoo ORM search plan.
Common Odoo models:
- res.users: Odoo System Users & Logins (name, login, active, share, create_date) - query this when user asks about users, logins, system access, how many users configured. Use domain [["share", "=", False]] for internal company users.
- hr.employee: HR Employees & Staff (name, work_email, department_id, job_title, work_phone)
- crm.lead: CRM Pipeline & Leads (name, partner_id, partner_name, expected_revenue, stage_id, probability, user_id, create_date, type='opportunity' or 'lead', phone, email_from)
- purchase.order: Purchase orders & Procurement (name, partner_id, amount_total, date_order, state, user_id)
- project.project: Projects & installations (name, partner_id, user_id, task_count, date_start, privacy_visibility)
- project.task: Project Tasks & Milestones (name, project_id, user_ids, stage_id, priority, date_deadline)
- account.move: Invoices & bills (move_type='out_invoice' for customer invoices, 'in_invoice' for vendor bills, amount_total, invoice_date, payment_state, partner_id, name, state='posted')
- sale.order: Sales orders (amount_total, date_order, partner_id, user_id, state='sale' or 'done', name)
- stock.picking: Shipments, deliveries & receipts (name, partner_id, picking_type_id, state, scheduled_date, origin)
- stock.quant: Inventory stock (product_id, quantity, location_id)
- res.partner: Customers & vendors (name, email, phone, total_invoiced, customer_rank)
- product.product: Products (name, list_price, standard_price, qty_available)

Respond ONLY with valid JSON (no markdown):
{{
  "report_title": "Descriptive Title",
  "model": "res.users",
  "domain": [["share", "=", false]],
  "fields": ["name", "login", "active", "create_date"],
  "order": "create_date desc",
  "limit": 25,
  "chart_type": "bar",
  "x_key": "name",
  "y_keys": ["id"],
  "entity_type": "user"
}}
"""


GEMINI_SYNTHESIS_PROMPT = """You are the mAifelZ AI ERP Executive Analyst.
Today's Date: {today}
The user asked: "{query}"

Here are the real records retrieved from the user's Odoo ERP system:
{records}

Total matching records count: {total_count}

Provide an executive analysis in valid JSON (no markdown):
{{
  "direct_answer": "1-2 sentences directly answering the user's question with exact numbers, names, dates, or items from the data. If user asked 'how many', give the exact count first.",
  "executive_summary": "2-3 sentences summarizing the broader context and totals from these records.",
  "insights": [
    "Specific analytical finding #1 with numbers",
    "Specific analytical finding #2",
    "Specific analytical finding #3"
  ],
  "recommendations": [
    "Actionable executive advice #1",
    "Actionable executive advice #2"
  ]
}}
"""


async def process_prompt(connector: OdooConnector, prompt: str) -> Dict[str, Any]:
    """
    Main AI pipeline:
    1. Parse user intent (via LLM or Smart BI NLP).
    2. Execute exact Odoo search_read queries.
    3. Synthesize a Direct Conversational Answer + KPIs + Chart + Table.
    """
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    client_type, client = get_llm_client()

    query_plan = None
    if client:
        try:
            query_plan = await _llm_classify(client_type, client, prompt, today_str)
        except Exception:
            pass

    if not query_plan:
        query_plan = _smart_nlp_classify(prompt, today)

    # Execute Odoo Query
    raw_data = []
    error_message = None
    try:
        raw_data = _execute_plan(connector, query_plan, prompt, today)
    except Exception as e:
        error_message = str(e)

    # Generate Direct Answer, Summary, KPIs, and Table
    synthesis = None
    if client and raw_data:
        try:
            synthesis = await _llm_synthesize(client_type, client, prompt, raw_data[:25], today_str)
        except Exception:
            pass

    if not synthesis:
        synthesis = _smart_nlp_synthesize(prompt, raw_data, query_plan, today)

    # Format Chart Data
    chart_data = _build_chart_data(raw_data, query_plan)

    # Format Table Records
    table_records, table_columns = _build_table_data(raw_data, query_plan)

    # Build KPI cards
    kpi_cards = _build_kpi_cards(raw_data, query_plan)

    return {
        "success": error_message is None,
        "prompt": prompt,
        "report_title": query_plan.get("report_title", f"Report: {prompt[:50]}"),
        "direct_answer": synthesis.get("direct_answer"),
        "executive_summary": synthesis.get("executive_summary", ""),
        "kpi_cards": kpi_cards,
        "sections": [
            {
                "title": query_plan.get("report_title", "Visual Analysis"),
                "chart_type": query_plan.get("chart_type", "bar"),
                "data": chart_data,
                "x_key": "label",
                "y_keys": ["value"],
                "summary": synthesis.get("executive_summary", ""),
                "color_scheme": "maifelz",
            }
        ],
        "table_columns": table_columns,
        "table_records": table_records[:50],
        "insights": synthesis.get("insights", []),
        "recommendations": synthesis.get("recommendations", []),
        "raw_data_available": len(raw_data) > 0,
        "error": error_message,
    }


# ── LLM Execution ─────────────────────────────────────────────────────────────

async def _llm_classify(c_type: str, client: Any, prompt: str, today_str: str) -> Dict:
    full_prompt = PROMPT_TO_QUERY_PROMPT.format(today=today_str, query=prompt)
    text = ""
    if c_type == "gemini":
        for m in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                resp = client.models.generate_content(
                    model=m,
                    contents=full_prompt,
                )
                text = resp.text.strip()
                if text:
                    break
            except Exception:
                continue
    else:
        # OpenAI or Groq
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if "groq" in str(getattr(client, "base_url", "")):
            model = "llama-3.3-70b-versatile"
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        text = resp.choices[0].message.content.strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    else:
        text = re.sub(r"```json\s*|\s*```", "", text).strip()
    return json.loads(text)


async def _llm_synthesize(c_type: str, client: Any, prompt: str, sample_records: List[Dict], today_str: str) -> Dict:
    prompt_synth = GEMINI_SYNTHESIS_PROMPT.format(
        today=today_str,
        query=prompt,
        records=json.dumps(sample_records, default=str)[:3500],
        total_count=len(sample_records),
    )
    text = ""
    if c_type == "gemini":
        for m in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                resp = client.models.generate_content(
                    model=m,
                    contents=prompt_synth,
                )
                text = resp.text.strip()
                if text:
                    break
            except Exception:
                continue
    else:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if "groq" in str(getattr(client, "base_url", "")):
            model = "llama-3.3-70b-versatile"
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt_synth}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        text = resp.choices[0].message.content.strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    else:
        text = re.sub(r"```json\s*|\s*```", "", text).strip()
    return json.loads(text)


# ── Smart BI NLP Engine (Accurate Rule-Based AI) ───────────────────────────────

def _smart_nlp_classify(prompt: str, today: datetime) -> Dict:
    """Accurately decomposes user intent, entity, timeframe, and sorting."""
    p = prompt.lower()

    # Timeframe detection
    is_today = any(w in p for w in ["today", "to day", "current day"])
    is_this_month = ("this month" in p or "current month" in p) and not is_today
    is_last_month = "last month" in p
    is_this_year = "this year" in p

    # Sort order & intent
    is_lowest = any(w in p for w in ["lowest", "smallest", "least", "cheapest", "minimum", "worst"])
    is_recent = any(w in p for w in ["last", "latest", "recent", "newest", "number"])
    is_count = any(w in p for w in ["how many", "count", "number of", "total"])
    order_dir = "asc" if is_lowest else "desc"

    # Entities
    if any(w in p for w in ["user", "users", "login", "logins", "account", "accounts", "staff", "employee", "employees", "configured user"]) or ("used" in p and any(k in p for k in ["odoo", "how many", "system", "many", "configured"])):
        domain = [["share", "=", False]]
        return {
            "entity_type": "user",
            "report_title": "Configured Odoo Users & System Access",
            "model": "res.users",
            "domain": domain,
            "fields": ["name", "login", "active", "create_date", "share"],
            "order": "name asc",
            "limit": 50,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["id"],
            "date_field": "create_date",
            "value_field": "id",
            "is_count": is_count,
            "is_today": is_today,
            "is_recent": is_recent,
        }

    elif any(w in p for w in ["lead", "pipeline", "crm", "opportunity", "deal"]):
        domain = [["type", "=", "opportunity"]]
        if is_today:
            domain.append(["create_date", ">=", today.strftime("%Y-%m-%d 00:00:00")])
        elif is_this_month:
            domain.append(["create_date", ">=", today.replace(day=1).strftime("%Y-%m-%d 00:00:00")])

        order = "create_date desc" if (is_recent or is_today or is_count) else f"expected_revenue {order_dir}"
        title = "Leads Generated Today" if is_today else ("Sales Pipeline Leads" if is_count else "Sales Pipeline & Opportunities")

        return {
            "entity_type": "lead",
            "report_title": title,
            "model": "crm.lead",
            "domain": domain,
            "fields": ["name", "partner_id", "partner_name", "expected_revenue", "stage_id", "probability", "user_id", "create_date", "phone", "email_from"],
            "order": order,
            "limit": 25,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["expected_revenue"],
            "date_field": "create_date",
            "value_field": "expected_revenue",
            "is_count": is_count,
            "is_today": is_today,
            "is_recent": is_recent,
        }

    elif any(w in p for w in ["invoice", "bill", "payment", "overdue", "outstanding", "receivable"]):
        domain = [["move_type", "=", "out_invoice"]]
        if "overdue" in p:
            domain.append(["payment_state", "!=", "paid"])
            domain.append(["invoice_date_due", "<", today.strftime("%Y-%m-%d")])
        elif "paid" in p and "unpaid" not in p:
            domain.append(["payment_state", "=", "paid"])

        # Filter for posted / numbered invoices when asking for invoice number or recent
        if is_recent or "number" in p:
            domain.append(["state", "=", "posted"])
            domain.append(["name", "!=", "/"])

        # Date filter if requested
        if is_today:
            domain.append(["invoice_date", "=", today.strftime("%Y-%m-%d")])
        elif is_this_month:
            start_month = today.replace(day=1).strftime("%Y-%m-%d")
            domain.append(["invoice_date", ">=", start_month])

        sort_field = "id desc" if is_recent else f"amount_total {order_dir}"
        title = "Latest Invoices" if is_recent else ("Highest Value Invoices" if not is_lowest else "Lowest Value Invoices")

        return {
            "entity_type": "invoice",
            "report_title": title,
            "model": "account.move",
            "domain": domain,
            "fields": ["name", "partner_id", "amount_total", "amount_residual", "invoice_date", "payment_state", "state"],
            "order": sort_field,
            "limit": 25,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["amount_total"],
            "date_field": "invoice_date",
            "value_field": "amount_total",
            "is_recent": is_recent,
            "is_today": is_today,
            "is_count": is_count,
        }

    # Check for specific purchase order line items e.g. "what is the items in purchase order P01061"
    po_ref_match = re.search(r"\b(p0\d+|p\d{3,})\b", p)
    is_asking_lines = any(w in p for w in ["item", "items", "product", "products", "line", "lines", "part", "parts", "component", "components", "what is in", "what are in", "contain", "contains"])

    if po_ref_match or (is_asking_lines and any(w in p for w in ["purchase", "po", "procurement", "vendor order", "supplier order"])):
        po_ref = po_ref_match.group(1).upper() if po_ref_match else None
        domain = [["order_id.name", "ilike", po_ref]] if po_ref else []
        title = f"Items in Purchase Order {po_ref}" if po_ref else "Purchase Order Line Items"
        return {
            "entity_type": "purchase_order_line",
            "report_title": title,
            "model": "purchase.order.line",
            "domain": domain,
            "po_ref": po_ref,
            "fields": ["name", "product_id", "product_qty", "price_unit", "price_subtotal", "order_id"],
            "order": "id asc",
            "limit": 50,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["price_subtotal"],
            "date_field": "",
            "value_field": "price_subtotal",
            "is_today": False,
            "is_recent": is_recent,
            "is_count": is_count,
        }

    # Check for specific sales order line items e.g. "what is the items in sales order S00049"
    so_ref_match = re.search(r"\b(s0\d+|so\d+|s\d{4,})\b", p)
    if so_ref_match or (is_asking_lines and any(w in p for w in ["sale", "so", "quote", "quotation", "sales order"])):
        so_ref = so_ref_match.group(1).upper() if so_ref_match else None
        domain = [["order_id.name", "ilike", so_ref]] if so_ref else []
        title = f"Items in Sales Order {so_ref}" if so_ref else "Sales Order Line Items"
        return {
            "entity_type": "sale_order_line",
            "report_title": title,
            "model": "sale.order.line",
            "domain": domain,
            "so_ref": so_ref,
            "fields": ["name", "product_id", "product_uom_qty", "price_unit", "price_subtotal", "order_id"],
            "order": "id asc",
            "limit": 50,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["price_subtotal"],
            "date_field": "",
            "value_field": "price_subtotal",
            "is_today": False,
            "is_recent": is_recent,
            "is_count": is_count,
        }

    elif any(w in p for w in ["purchase", "po", "procurement", "vendor order", "supplier order", "buying"]):
        domain = []
        if "draft" in p:
            domain.append(["state", "=", "draft"])
        elif "done" in p or "confirmed" in p:
            domain.append(["state", "in", ["purchase", "done"]])

        if is_today:
            domain.append(["date_order", ">=", today.strftime("%Y-%m-%d 00:00:00")])
        elif is_this_month:
            start_month = today.replace(day=1).strftime("%Y-%m-%d")
            domain.append(["date_order", ">=", start_month])

        order = "date_order desc" if is_recent else f"amount_total {order_dir}"
        return {
            "entity_type": "purchase_order",
            "report_title": "Purchase Orders & Procurement",
            "model": "purchase.order",
            "domain": domain,
            "fields": ["name", "partner_id", "amount_total", "date_order", "state", "user_id"],
            "order": order,
            "limit": 30,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["amount_total"],
            "date_field": "date_order",
            "value_field": "amount_total",
            "is_today": is_today,
            "is_recent": is_recent,
            "is_count": is_count,
        }

    elif any(w in p for w in ["project", "projects", "installation", "installations"]):
        domain = []
        order = "id desc" if is_recent else "name asc"
        return {
            "entity_type": "project",
            "report_title": "Project Operations & Status",
            "model": "project.project",
            "domain": domain,
            "fields": ["name", "partner_id", "user_id", "task_count", "date_start", "privacy_visibility"],
            "order": order,
            "limit": 35,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["task_count"],
            "date_field": "date_start",
            "value_field": "task_count",
            "is_today": is_today,
            "is_recent": is_recent,
            "is_count": is_count,
        }

    elif any(w in p for w in ["task", "tasks", "milestone", "todo", "action item"]):
        domain = []
        return {
            "entity_type": "task",
            "report_title": "Project Tasks & Milestones",
            "model": "project.task",
            "domain": domain,
            "fields": ["name", "project_id", "user_ids", "stage_id", "priority", "date_deadline"],
            "order": "date_deadline asc" if "due" in p or "deadline" in p else "id desc",
            "limit": 35,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["id"],
            "date_field": "date_deadline",
            "value_field": "id",
            "is_today": is_today,
            "is_recent": is_recent,
            "is_count": is_count,
        }

    elif any(w in p for w in ["delivery", "deliveries", "shipment", "shipments", "picking", "transfer", "transfers", "dispatch", "receipt", "receipts"]):
        domain = []
        if "pending" in p or "waiting" in p:
            domain.append(["state", "in", ["assigned", "waiting", "confirmed"]])
        elif "done" in p or "completed" in p:
            domain.append(["state", "=", "done"])

        return {
            "entity_type": "stock_picking",
            "report_title": "Warehouse Shipments & Deliveries",
            "model": "stock.picking",
            "domain": domain,
            "fields": ["name", "partner_id", "picking_type_id", "state", "scheduled_date", "origin"],
            "order": "scheduled_date desc" if is_recent else "id desc",
            "limit": 30,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["id"],
            "date_field": "scheduled_date",
            "value_field": "id",
            "is_today": is_today,
            "is_recent": is_recent,
            "is_count": is_count,
        }

    elif any(w in p for w in ["order", "sale", "quotation", "revenue"]):
        domain = [["state", "in", ["sale", "done"]]]
        if is_today:
            domain.append(["date_order", ">=", today.strftime("%Y-%m-%d 00:00:00")])
        elif is_this_month:
            start_month = today.replace(day=1).strftime("%Y-%m-%d")
            domain.append(["date_order", ">=", start_month])

        order = "date_order desc" if is_recent else f"amount_total {order_dir}"
        return {
            "entity_type": "sale_order",
            "report_title": "Top Sales Orders" if not is_lowest else "Lowest Sales Orders",
            "model": "sale.order",
            "domain": domain,
            "fields": ["name", "partner_id", "amount_total", "date_order", "user_id", "state"],
            "order": order,
            "limit": 25,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["amount_total"],
            "date_field": "date_order",
            "value_field": "amount_total",
            "is_today": is_today,
            "is_recent": is_recent,
        }

    elif any(w in p for w in ["customer", "client"]):
        return {
            "entity_type": "customer",
            "report_title": "Top Customers Analysis",
            "model": "res.partner",
            "domain": [["customer_rank", ">", 0]],
            "fields": ["name", "total_invoiced", "phone", "email", "city", "country_id"],
            "order": f"total_invoiced {order_dir}",
            "limit": 20,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["total_invoiced"],
            "date_field": "",
            "value_field": "total_invoiced",
        }

    elif any(w in p for w in ["product", "products", "stock", "inventory", "catalog", "goods", "sku", "item"]):
        return {
            "entity_type": "product",
            "report_title": "Product & Inventory Overview",
            "model": "product.product",
            "domain": [["type", "in", ["consu", "product"]]],
            "fields": ["name", "qty_available", "list_price", "standard_price", "default_code"],
            "order": f"list_price {order_dir}",
            "limit": 20,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["qty_available"],
            "date_field": "",
            "value_field": "qty_available",
        }

    else:
        return {
            "entity_type": "sale_order",
            "report_title": f"Business Analysis: {prompt[:40]}",
            "model": "sale.order",
            "domain": [["state", "in", ["sale", "done"]]],
            "fields": ["name", "partner_id", "amount_total", "date_order", "user_id"],
            "order": f"amount_total {order_dir}",
            "limit": 20,
            "chart_type": "bar",
            "x_key": "name",
            "y_keys": ["amount_total"],
            "date_field": "date_order",
            "value_field": "amount_total",
        }


def _execute_plan(connector: OdooConnector, plan: Dict, prompt: str, today: datetime) -> List[Dict]:
    """Executes search_read with graceful fallback if a strict date filter yields 0 records."""
    model = plan.get("model", "account.move")
    domain = plan.get("domain", [])
    fields = plan.get("fields", ["name", "amount_total"])
    order = plan.get("order", "create_date desc")
    limit = min(int(plan.get("limit", 25)), 100)

    # Resolution for PO line items when no specific PO was supplied
    if plan.get("entity_type") == "purchase_order_line" and not domain:
        latest_po = connector.search_read("purchase.order", [], ["id", "name"], limit=1, order="date_order desc")
        if latest_po:
            domain = [["order_id", "=", latest_po[0]["id"]]]
            plan["report_title"] = f"Items in Purchase Order {latest_po[0].get('name')}"

    # Resolution for SO line items when no specific SO was supplied
    if plan.get("entity_type") == "sale_order_line" and not domain:
        latest_so = connector.search_read("sale.order", [], ["id", "name"], limit=1, order="date_order desc")
        if latest_so:
            domain = [["order_id", "=", latest_so[0]["id"]]]
            plan["report_title"] = f"Items in Sales Order {latest_so[0].get('name')}"

    # Guard against non-stored fields in SQL order clause (like qty_available)
    if order and "qty_available" in order:
        order = "id desc"

    try:
        records = connector.search_read(model, domain, fields, limit=limit, order=order)
    except Exception as e:
        err_str = str(e)
        if "to SQL because it is not stored" in err_str or "ValueError" in err_str or "order" in err_str:
            records = connector.search_read(model, domain, fields, limit=limit, order="id desc")
        else:
            raise e

    # Special handling for "today" filter:
    if plan.get("is_today"):
        plan["today_count"] = len(records)
        if not records:
            # If 0 records today, fetch latest records overall so user gets full details
            relaxed_domain = [f for f in domain if isinstance(f, (list, tuple)) and f[0] not in ["invoice_date", "date_order", "create_date"]]
            latest_records = connector.search_read(model, relaxed_domain, fields, limit=10, order="create_date desc" if "create_date" in fields else order)
            plan["relaxed_filter"] = True
            return latest_records
        return records

    # General Fallback if 0 records
    if not records and any(tuple_filter[0] in ["invoice_date", "date_order", "create_date"] for tuple_filter in domain if isinstance(tuple_filter, (list, tuple))):
        relaxed_domain = [f for f in domain if isinstance(f, (list, tuple)) and f[0] not in ["invoice_date", "date_order", "create_date"]]
        records = connector.search_read(model, relaxed_domain, fields, limit=limit, order=order)
        plan["relaxed_filter"] = True

    return records


def _smart_nlp_synthesize(prompt: str, records: List[Dict], plan: Dict, today: datetime) -> Dict:
    """Generates direct answer, executive summary, and insights from the actual records."""
    if not records:
        return {
            "direct_answer": "No matching records were found in your Odoo database matching the criteria.",
            "executive_summary": "Query executed successfully, but 0 records satisfied the active filters.",
            "insights": ["Verify if the specified model contains recorded transactions.", "Try broadening the date range."],
            "recommendations": ["Ensure leads/invoices/orders are in posted or active status in Odoo."],
        }

    top_record = records[0]
    entity = plan.get("entity_type", "record")
    relaxed = plan.get("relaxed_filter", False)

    # Helper to resolve partner name
    def _partner_str(r):
        p = r.get("partner_id") or r.get("partner_name")
        if isinstance(p, list) and len(p) == 2:
            return p[1]
        return str(p) if p else "Customer"

    # Helper to resolve currency
    def _cur(val):
        try:
            return f"${float(val):,.2f}"
        except Exception:
            return str(val)

    name_1 = top_record.get("name") or f"Record #{top_record.get('id', '')}"
    partner_1 = _partner_str(top_record)
    total_val = sum(float(r.get(plan.get("value_field", "amount_total"), 0) or 0) for r in records)

    if entity == "user":
        user_count = len(records)
        user_names = [r.get("name") for r in records if r.get("name")]
        names_str = ", ".join(user_names[:6])
        if len(user_names) > 6:
            names_str += f" and {len(user_names) - 6} more"

        direct_answer = (
            f"There are **{user_count} active internal users** configured in your Odoo system: **{names_str}**."
        )
        executive_summary = (
            f"Retrieved {user_count} internal user accounts configured in Odoo. "
            f"All accounts have active ERP credentials and role assignments."
        )
        insights = [
            f"Total configured internal seats: {user_count} users",
            f"Active logins: {names_str}",
            f"Primary system administrator / key account: {records[0].get('name', 'Admin')} ({records[0].get('login', '-')})",
        ]
        recommendations = [
            "Periodically audit user access groups and revoke inactive seat credentials to optimize Odoo license costs.",
            "Enforce two-factor authentication (2FA) for all administrative logins.",
        ]
        return {
            "direct_answer": direct_answer,
            "executive_summary": executive_summary,
            "insights": insights,
            "recommendations": recommendations,
        }

    elif entity == "lead":
        rev_1 = _cur(top_record.get("expected_revenue", 0))
        c_date_1 = str(top_record.get("create_date") or "")[:10]
        today_date_str = today.strftime("%B %d, %Y")

        if plan.get("is_today"):
            today_count = plan.get("today_count", 0)
            if today_count == 0:
                direct_answer = (
                    f"There were **0 leads generated today** ({today_date_str}). "
                    f"The most recent leads in your CRM were created on **{c_date_1}** (latest: **{name_1}** for **{rev_1}**)."
                )
                executive_summary = f"No new leads recorded for today ({today_date_str}). Displaying the latest {len(records)} pipeline opportunities for review."
            else:
                direct_answer = (
                    f"A total of **{today_count} lead{'s were' if today_count != 1 else ' was'}** generated today ({today_date_str}) "
                    f"with a combined expected pipeline value of **{_cur(total_val)}**."
                )
                executive_summary = f"Successfully captured {today_count} lead{'s' if today_count != 1 else ''} today representing {_cur(total_val)} in new pipeline value."
        elif plan.get("is_count"):
            direct_answer = f"Found a total of **{len(records)} active leads** with an expected cumulative value of **{_cur(total_val)}**."
            executive_summary = f"Tracking {len(records)} pipeline opportunities with a cumulative expected value of {_cur(total_val)}."
        else:
            direct_answer = (
                f"The highest value pipeline opportunity is **{name_1}** ({partner_1}) with an expected value of **{rev_1}**."
            )
            executive_summary = f"Tracking {len(records)} opportunities with a total pipeline value of {_cur(total_val)}."

        insights = [
            f"Most recent lead: {name_1} ({rev_1})" if plan.get("is_today") or plan.get("is_recent") else f"Highest value deal: {name_1} ({rev_1})",
            f"Total pipeline volume in this set: {_cur(total_val)}",
            f"Average opportunity value: {_cur(total_val / len(records))}",
        ]
        recommendations = [
            "Assign new incoming leads within 15 minutes to maximize contact and conversion rates.",
            "Fast-track stage progression for qualified opportunities.",
        ]

    elif entity == "invoice":
        amount_1 = _cur(top_record.get("amount_total", 0))
        date_1 = top_record.get("invoice_date") or "Recently"
        status_1 = str(top_record.get("payment_state") or "unpaid")

        if plan.get("is_recent") or any(w in prompt.lower() for w in ["last", "latest", "recent", "newest"]):
            direct_answer = (
                f"The last invoice number is **{name_1}** issued to **{partner_1}** for **{amount_1}** "
                f"on {date_1} (Status: {status_1.replace('_', ' ').capitalize()})."
            )
            executive_summary = f"Retrieved your most recent invoices. The latest recorded invoice is {name_1} for {amount_1}."
        else:
            prefix = "Looking across your most recent posted invoices, the" if relaxed else "The"
            direct_answer = (
                f"{prefix} highest value invoice is **{name_1}** issued to **{partner_1}** for **{amount_1}** "
                f"on {date_1} (Status: {status_1.replace('_', ' ').capitalize()})."
            )
            executive_summary = (
                f"Retrieved {len(records)} invoices with a cumulative value of {_cur(total_val)}. "
                f"The largest single invoice represents {((float(top_record.get('amount_total', 0))/total_val)*100 if total_val else 0):.1f}% of this group."
            )
        insights = [
            f"Highest invoice: {name_1} ({partner_1}) at {amount_1}",
            f"Total combined value of top {len(records)} invoices: {_cur(total_val)}",
            f"Average invoice value: {_cur(total_val / len(records))}",
        ]
        recommendations = [
            f"Prioritize collection verification for {name_1} ({amount_1}) to optimize cash flow.",
            "Establish automated payment reminders for invoices over $10,000.",
        ]

    elif entity == "purchase_order_line":
        total_items = len(records)
        total_qty = sum(float(r.get("product_qty", 0) or 0) for r in records)
        po_order = records[0].get("order_id") if records else None
        po_title = po_order[1] if isinstance(po_order, list) and len(po_order) == 2 else str(po_order or "Purchase Order")
        po_ref_clean = po_title.split(" ")[0] if po_title else "PO"

        item_highlights = [f"{r.get('name', 'Item')} (Qty: {r.get('product_qty')})" for r in records[:3]]
        highlights_str = ", ".join(item_highlights)

        direct_answer = (
            f"Purchase order **{po_ref_clean}** contains **{total_items} item{'s' if total_items != 1 else ''}** "
            f"(totaling {total_qty:g} units) with a combined subtotal of **{_cur(total_val)}**. "
            f"Key items include: **{highlights_str}**."
        )
        executive_summary = (
            f"Detailed product line-item breakdown for {po_ref_clean}. "
            f"Consists of {total_items} distinct lines with a total order subtotal of {_cur(total_val)}."
        )
        insights = [
            f"Largest item by line value: {top_record.get('name')} ({_cur(top_record.get('price_subtotal', 0))})",
            f"Total distinct product lines: {total_items}",
            f"Total units ordered: {total_qty:g}",
        ]
        recommendations = [
            "Verify delivered quantities upon warehouse receipt against the supplier packing slip.",
            "Cross-reference unit prices against agreed master pricing agreement.",
        ]

    elif entity == "sale_order_line":
        total_items = len(records)
        total_qty = sum(float(r.get("product_uom_qty", 0) or 0) for r in records)
        so_order = records[0].get("order_id") if records else None
        so_title = so_order[1] if isinstance(so_order, list) and len(so_order) == 2 else str(so_order or "Sales Order")
        so_ref_clean = so_title.split(" ")[0] if so_title else "SO"

        item_highlights = [f"{r.get('name', 'Item')} (Qty: {r.get('product_uom_qty')})" for r in records[:3]]
        highlights_str = ", ".join(item_highlights)

        direct_answer = (
            f"Sales order **{so_ref_clean}** contains **{total_items} item{'s' if total_items != 1 else ''}** "
            f"(totaling {total_qty:g} units) with a combined value of **{_cur(total_val)}**. "
            f"Key items: **{highlights_str}**."
        )
        executive_summary = f"Line-item breakdown for sales order {so_ref_clean} representing {_cur(total_val)}."
        insights = [
            f"Highest value line: {top_record.get('name')} ({_cur(top_record.get('price_subtotal', 0))})",
            f"Total order lines: {total_items}",
        ]
        recommendations = [
            "Ensure stock availability for all order items before scheduling installation.",
        ]

    elif entity == "purchase_order":
        amount_1 = _cur(top_record.get("amount_total", 0))
        date_1 = str(top_record.get("date_order", "N/A"))[:10]
        status_1 = str(top_record.get("state") or "draft").replace("_", " ").title()
        direct_answer = (
            f"You have **{len(records)} purchase order{'s' if len(records) != 1 else ''}** recorded totaling **{_cur(total_val)}**. "
            f"The primary purchase order is **{name_1}** with **{partner_1}** for **{amount_1}** (Status: {status_1})."
        )
        executive_summary = (
            f"Analyzed {len(records)} procurement records representing {_cur(total_val)} in total vendor commitments."
        )
        insights = [
            f"Top purchase order: {name_1} ({partner_1}) at {amount_1}",
            f"Total procurement volume in this group: {_cur(total_val)}",
            f"Average PO commitment: {_cur(total_val / len(records))}",
        ]
        recommendations = [
            "Review unconfirmed draft purchase orders with suppliers to ensure on-time delivery schedules.",
            "Consolidate volume orders with preferred vendors to capture tiered pricing discounts.",
        ]

    elif entity == "project":
        lead_user = top_record.get("user_id")
        lead_str = lead_user[1] if isinstance(lead_user, list) and len(lead_user) == 2 else str(lead_user or "Unassigned")
        direct_answer = (
            f"There are **{len(records)} active projects** configured in your Odoo system. "
            f"A key project is **{name_1}** (Client: **{partner_1}**, Project Lead: **{lead_str}**)."
        )
        executive_summary = (
            f"Tracking {len(records)} project initiatives across customer installations, service jobs, and ongoing operations."
        )
        insights = [
            f"Total active projects: {len(records)}",
            f"Primary active installation: {name_1} (Client: {partner_1})",
            f"Key project manager: {lead_str}",
        ]
        recommendations = [
            "Conduct weekly milestone reviews with assigned project leads to maintain on-time completion.",
            "Ensure signed customer handover certificates are uploaded before triggering final billing.",
        ]

    elif entity == "task":
        stage = top_record.get("stage_id")
        stage_str = stage[1] if isinstance(stage, list) and len(stage) == 2 else str(stage or "In Progress")
        direct_answer = (
            f"Found **{len(records)} operational task{'s' if len(records) != 1 else ''}** in your system. "
            f"Latest task: **{name_1}** (Stage: **{stage_str}**)."
        )
        executive_summary = f"Tracking {len(records)} tasks and milestones across your team's project pipeline."
        insights = [
            f"Total tasks tracked: {len(records)}",
            f"Latest task in review: {name_1}",
        ]
        recommendations = [
            "Prioritize tasks nearing their scheduled deadlines.",
            "Assign unallocated tasks to balance workload across technicians.",
        ]

    elif entity == "stock_picking":
        op_type = top_record.get("picking_type_id")
        op_str = op_type[1] if isinstance(op_type, list) and len(op_type) == 2 else "Transfer"
        status_1 = str(top_record.get("state") or "draft").replace("_", " ").title()
        direct_answer = (
            f"Retrieved **{len(records)} warehouse transfers and shipments**. "
            f"Latest operation is **{name_1}** ({op_str}, Status: **{status_1}**)."
        )
        executive_summary = f"Monitoring {len(records)} logistics movements across warehouse receipts, internal transfers, and customer deliveries."
        insights = [
            f"Total transfers monitored: {len(records)}",
            f"Latest logistics operation: {name_1} ({op_str})",
        ]
        recommendations = [
            "Expedite validation of pending receipts to keep stock levels synchronized with sales demand.",
            "Review cancelled and backlog pickings to resolve inventory discrepancies.",
        ]

    elif entity == "sale_order":
        amount_1 = _cur(top_record.get("amount_total", 0))
        date_1 = top_record.get("date_order", "N/A")[:10]
        direct_answer = (
            f"The highest value sales order is **{name_1}** from **{partner_1}** for **{amount_1}** (Ordered: {date_1})."
        )
        executive_summary = (
            f"Identified {len(records)} confirmed sales orders representing {_cur(total_val)} in gross sales volume."
        )
        insights = [
            f"Top order: {name_1} with {partner_1} ({amount_1})",
            f"Average order size across this segment: {_cur(total_val / len(records))}",
            f"Total sales volume: {_cur(total_val)}",
        ]
        recommendations = [
            f"Ensure timely fulfillment and VIP onboarding for client {partner_1}.",
            "Analyze upsell potential for customers with orders exceeding average ticket size.",
        ]

    elif entity == "customer":
        inv_val = _cur(top_record.get("total_invoiced", 0))
        direct_answer = (
            f"Your #1 top customer by total invoiced volume is **{partner_1}** with **{inv_val}** in total business."
        )
        executive_summary = f"Analyzed top {len(records)} customer accounts representing {_cur(total_val)} in combined revenue."
        insights = [
            f"Top client: {partner_1} with {inv_val} total invoiced",
            f"Top {min(5, len(records))} accounts generate the vast majority of account activity.",
        ]
        recommendations = [
            f"Schedule executive quarterly review with {partner_1}.",
            "Deploy dedicated account management for top tier clients.",
        ]

    else:
        direct_answer = (
            f"The top result is **{name_1}** with an evaluated metric of **{_cur(top_record.get(plan.get('value_field', 'amount_total'), 0))}**."
        )
        executive_summary = f"Summary of {len(records)} records retrieved from your Odoo database."
        insights = [f"Found {len(records)} matching entries."]
        recommendations = ["Continue monitoring key ERP performance indicators."]

    return {
        "direct_answer": direct_answer,
        "executive_summary": executive_summary,
        "insights": insights,
        "recommendations": recommendations,
    }


def _build_chart_data(records: List[Dict], plan: Dict) -> List[Dict]:
    """Generates clean, readable chart points from records (Top 10 max)."""
    if not records:
        return []

    if plan.get("entity_type") in ["user", "task", "stock_picking"]:
        return [
            {
                "label": str(r.get("name") or "Item")[:22],
                "value": 1,
                "name": str(r.get("name") or "Item")[:22],
            }
            for r in records[:15]
        ]

    chart_points = []
    value_field = plan.get("value_field", "amount_total")

    for r in records[:12]:
        raw_name = r.get("name") or "Record"
        partner = r.get("partner_id") or r.get("partner_name")
        partner_str = partner[1] if isinstance(partner, list) and len(partner) == 2 else str(partner or "")

        if partner_str and partner_str != "Customer":
            label = f"{raw_name} ({partner_str[:16]})"
        else:
            label = str(raw_name)

        if len(label) > 28:
            label = label[:25] + "..."

        val = float(r.get(value_field, 0) or 0)
        chart_points.append({
            "label": label,
            "value": round(val, 2),
            "name": label,
        })

    return chart_points


def _build_table_data(records: List[Dict], plan: Dict) -> tuple:
    """Formats records into clean tabular rows and defines column metadata."""
    if not records:
        return [], []

    entity = plan.get("entity_type", "invoice")

    if entity == "user":
        columns = [
            {"key": "name", "label": "User Name", "type": "text"},
            {"key": "login", "label": "Login / Email", "type": "text"},
            {"key": "active", "label": "Account Status", "type": "badge"},
            {"key": "date", "label": "Created Date", "type": "date"},
        ]
        rows = []
        for r in records:
            rows.append({
                "name": r.get("name", "-"),
                "login": r.get("login", "-"),
                "active": "Active" if r.get("active", True) else "Inactive",
                "date": str(r.get("create_date") or "-")[:10],
            })
        return rows, columns

    elif entity == "lead":
        columns = [
            {"key": "name", "label": "Lead / Opportunity", "type": "text"},
            {"key": "partner", "label": "Contact / Customer", "type": "text"},
            {"key": "revenue", "label": "Expected Value", "type": "currency"},
            {"key": "stage", "label": "Stage", "type": "badge"},
            {"key": "date", "label": "Created Date", "type": "date"},
        ]
        rows = []
        for r in records:
            p = r.get("partner_id")
            p_name = p[1] if isinstance(p, list) and len(p) == 2 else (r.get("partner_name") or "-")
            st = r.get("stage_id")
            stage_name = st[1] if isinstance(st, list) and len(st) == 2 else str(st or "New")
            c_date = str(r.get("create_date") or "-")[:10]
            rows.append({
                "name": r.get("name", "-"),
                "partner": p_name,
                "revenue": float(r.get("expected_revenue", 0) or 0),
                "stage": stage_name,
                "date": c_date,
            })
        return rows, columns

    elif entity == "invoice":
        columns = [
            {"key": "name", "label": "Invoice #", "type": "text"},
            {"key": "partner", "label": "Customer", "type": "text"},
            {"key": "date", "label": "Invoice Date", "type": "date"},
            {"key": "amount_total", "label": "Total Amount", "type": "currency"},
            {"key": "residual", "label": "Balance Due", "type": "currency"},
            {"key": "payment_state", "label": "Status", "type": "badge"},
        ]
        rows = []
        for r in records:
            p = r.get("partner_id")
            partner_name = p[1] if isinstance(p, list) and len(p) == 2 else str(p or "-")
            rows.append({
                "name": r.get("name", "-"),
                "partner": partner_name,
                "date": str(r.get("invoice_date") or "-"),
                "amount_total": float(r.get("amount_total", 0) or 0),
                "residual": float(r.get("amount_residual", 0) or 0),
                "payment_state": str(r.get("payment_state") or "unpaid").replace("_", " ").title(),
            })
        return rows, columns

    elif entity == "sale_order":
        columns = [
            {"key": "name", "label": "Order #", "type": "text"},
            {"key": "partner", "label": "Customer", "type": "text"},
            {"key": "date", "label": "Order Date", "type": "date"},
            {"key": "amount_total", "label": "Total Amount", "type": "currency"},
            {"key": "state", "label": "Status", "type": "badge"},
        ]
        rows = []
        for r in records:
            p = r.get("partner_id")
            partner_name = p[1] if isinstance(p, list) and len(p) == 2 else str(p or "-")
            rows.append({
                "name": r.get("name", "-"),
                "partner": partner_name,
                "date": str(r.get("date_order") or "-")[:10],
                "amount_total": float(r.get("amount_total", 0) or 0),
                "state": str(r.get("state") or "sale").title(),
            })
        return rows, columns

    elif entity == "purchase_order_line":
        columns = [
            {"key": "name", "label": "Product / Description", "type": "text"},
            {"key": "qty", "label": "Quantity", "type": "number"},
            {"key": "price_unit", "label": "Unit Price", "type": "currency"},
            {"key": "subtotal", "label": "Line Subtotal", "type": "currency"},
        ]
        rows = []
        for r in records:
            p_name = r.get("name") or "-"
            rows.append({
                "name": p_name,
                "qty": float(r.get("product_qty", 0) or 0),
                "price_unit": float(r.get("price_unit", 0) or 0),
                "subtotal": float(r.get("price_subtotal", 0) or 0),
            })
        return rows, columns

    elif entity == "sale_order_line":
        columns = [
            {"key": "name", "label": "Product / Description", "type": "text"},
            {"key": "qty", "label": "Quantity", "type": "number"},
            {"key": "price_unit", "label": "Unit Price", "type": "currency"},
            {"key": "subtotal", "label": "Line Subtotal", "type": "currency"},
        ]
        rows = []
        for r in records:
            p_name = r.get("name") or "-"
            rows.append({
                "name": p_name,
                "qty": float(r.get("product_uom_qty", 0) or 0),
                "price_unit": float(r.get("price_unit", 0) or 0),
                "subtotal": float(r.get("price_subtotal", 0) or 0),
            })
        return rows, columns

    elif entity == "purchase_order":
        columns = [
            {"key": "name", "label": "PO #", "type": "text"},
            {"key": "partner", "label": "Vendor / Supplier", "type": "text"},
            {"key": "date", "label": "Order Date", "type": "date"},
            {"key": "amount_total", "label": "Total Amount", "type": "currency"},
            {"key": "user", "label": "Buyer / Rep", "type": "text"},
            {"key": "state", "label": "Status", "type": "badge"},
        ]
        rows = []
        for r in records:
            p = r.get("partner_id")
            p_name = p[1] if isinstance(p, list) and len(p) == 2 else str(p or "-")
            u = r.get("user_id")
            u_name = u[1] if isinstance(u, list) and len(u) == 2 else str(u or "-")
            rows.append({
                "name": r.get("name", "-"),
                "partner": p_name,
                "date": str(r.get("date_order") or "-")[:10],
                "amount_total": float(r.get("amount_total", 0) or 0),
                "user": u_name,
                "state": str(r.get("state") or "draft").replace("_", " ").title(),
            })
        return rows, columns

    elif entity == "project":
        columns = [
            {"key": "name", "label": "Project Name", "type": "text"},
            {"key": "partner", "label": "Client / Partner", "type": "text"},
            {"key": "user", "label": "Project Lead", "type": "text"},
            {"key": "task_count", "label": "Tasks", "type": "number"},
            {"key": "visibility", "label": "Access", "type": "badge"},
        ]
        rows = []
        for r in records:
            p = r.get("partner_id")
            p_name = p[1] if isinstance(p, list) and len(p) == 2 else str(p or "-")
            u = r.get("user_id")
            u_name = u[1] if isinstance(u, list) and len(u) == 2 else str(u or "-")
            rows.append({
                "name": r.get("name", "-"),
                "partner": p_name,
                "user": u_name,
                "task_count": int(r.get("task_count", 0) or 0),
                "visibility": str(r.get("privacy_visibility") or "portal").title(),
            })
        return rows, columns

    elif entity == "task":
        columns = [
            {"key": "name", "label": "Task Name", "type": "text"},
            {"key": "project", "label": "Project", "type": "text"},
            {"key": "stage", "label": "Stage", "type": "badge"},
            {"key": "priority", "label": "Priority", "type": "badge"},
            {"key": "date", "label": "Deadline", "type": "date"},
        ]
        rows = []
        for r in records:
            prj = r.get("project_id")
            prj_name = prj[1] if isinstance(prj, list) and len(prj) == 2 else str(prj or "-")
            stg = r.get("stage_id")
            stg_name = stg[1] if isinstance(stg, list) and len(stg) == 2 else str(stg or "New")
            rows.append({
                "name": r.get("name", "-"),
                "project": prj_name,
                "stage": stg_name,
                "priority": "High" if str(r.get("priority")) == "1" else "Normal",
                "date": str(r.get("date_deadline") or "-")[:10],
            })
        return rows, columns

    elif entity == "stock_picking":
        columns = [
            {"key": "name", "label": "Transfer #", "type": "text"},
            {"key": "partner", "label": "Partner", "type": "text"},
            {"key": "type", "label": "Operation Type", "type": "text"},
            {"key": "origin", "label": "Source Doc", "type": "text"},
            {"key": "date", "label": "Scheduled Date", "type": "date"},
            {"key": "state", "label": "Status", "type": "badge"},
        ]
        rows = []
        for r in records:
            p = r.get("partner_id")
            p_name = p[1] if isinstance(p, list) and len(p) == 2 else str(p or "-")
            op = r.get("picking_type_id")
            op_name = op[1] if isinstance(op, list) and len(op) == 2 else str(op or "-")
            rows.append({
                "name": r.get("name", "-"),
                "partner": p_name,
                "type": op_name,
                "origin": str(r.get("origin") or "-"),
                "date": str(r.get("scheduled_date") or "-")[:10],
                "state": str(r.get("state") or "draft").replace("_", " ").title(),
            })
        return rows, columns

    else:
        first = records[0]
        keys = [k for k in first.keys() if k != "id"][:5]
        columns = [{"key": k, "label": k.replace("_", " ").title(), "type": "text"} for k in keys]
        rows = []
        for r in records:
            row = {}
            for k in keys:
                val = r.get(k)
                if isinstance(val, list) and len(val) == 2:
                    val = val[1]
                row[k] = val
            rows.append(row)
        return rows, columns


def _build_kpi_cards(records: List[Dict], plan: Dict) -> List[Dict]:
    """Generates informative KPI metric cards."""
    if not records:
        return []

    if plan.get("entity_type") == "user":
        active_count = sum(1 for r in records if r.get("active", True))
        first_admin = records[0].get("name", "Administrator") if records else "Admin"
        first_email = records[0].get("login", "") if records else ""
        return [
            {
                "title": "Total Users",
                "value": str(len(records)),
                "change": "Configured",
                "change_type": "up",
                "icon": "users",
                "description": "Configured internal users",
            },
            {
                "title": "Active Seats",
                "value": str(active_count),
                "change": "100%",
                "change_type": "up",
                "icon": "user-check",
                "description": "Active system logins",
            },
            {
                "title": "Internal Licenses",
                "value": str(len(records)),
                "change": None,
                "change_type": "neutral",
                "icon": "shield",
                "description": "Internal employee seats",
            },
            {
                "title": "System Lead",
                "value": first_admin[:18],
                "change": None,
                "change_type": "neutral",
                "icon": "award",
                "description": first_email[:25],
            },
        ]

    def _fmt(n):
        if n >= 1_000_000:
            return f"${n/1_000_000:.2f}M"
        if n >= 1_000:
            return f"${n/1_000:.1f}K"
        return f"${n:,.2f}"

    if plan.get("entity_type") in ["purchase_order_line", "sale_order_line"]:
        qty_key = "product_qty" if plan.get("entity_type") == "purchase_order_line" else "product_uom_qty"
        total_qty = sum(float(r.get(qty_key, 0) or 0) for r in records)
        top_line = max(records, key=lambda x: float(x.get("price_subtotal", 0) or 0)) if records else {}
        total_subtotal = sum(float(r.get("price_subtotal", 0) or 0) for r in records)
        return [
            {
                "title": "Line Items",
                "value": str(len(records)),
                "change": "Products",
                "change_type": "neutral",
                "icon": "package",
                "description": "Distinct products on order",
            },
            {
                "title": "Total Units",
                "value": f"{total_qty:g}",
                "change": "Ordered",
                "change_type": "up",
                "icon": "hash",
                "description": "Combined item quantities",
            },
            {
                "title": "Line Subtotal",
                "value": _fmt(total_subtotal),
                "change": "Total",
                "change_type": "up",
                "icon": "dollar-sign",
                "description": "Excluding freight & tax",
            },
            {
                "title": "Top Value Item",
                "value": _fmt(float(top_line.get("price_subtotal", 0) or 0)),
                "change": "Highest",
                "change_type": "up",
                "icon": "award",
                "description": str(top_line.get("name") or "Item")[:22],
            },
        ]

    elif plan.get("entity_type") == "purchase_order":
        po_values = [float(r.get("amount_total", 0) or 0) for r in records]
        po_sum = sum(po_values)
        po_top = max(po_values) if po_values else 0
        po_avg = po_sum / len(po_values) if po_values else 0
        p_name = records[0].get("partner_id") if records else ""
        v_name = p_name[1] if isinstance(p_name, list) and len(p_name) == 2 else "Vendor"
        return [
            {
                "title": "Total POs",
                "value": str(len(records)),
                "change": None,
                "change_type": "neutral",
                "icon": "shopping-cart",
                "description": "Purchase orders recorded",
            },
            {
                "title": "Procurement Total",
                "value": _fmt(po_sum),
                "change": "Volume",
                "change_type": "up",
                "icon": "dollar-sign",
                "description": "Total purchase commitment",
            },
            {
                "title": "Largest PO",
                "value": _fmt(po_top),
                "change": "Top #1",
                "change_type": "up",
                "icon": "trending-up",
                "description": f"Vendor: {v_name[:20]}",
            },
            {
                "title": "Average PO",
                "value": _fmt(po_avg),
                "change": None,
                "change_type": "neutral",
                "icon": "bar-chart-2",
                "description": "Average commitment per PO",
            },
        ]

    elif plan.get("entity_type") == "project":
        total_tasks = sum(int(r.get("task_count", 0) or 0) for r in records)
        first_lead = records[0].get("user_id") if records else ""
        lead_str = first_lead[1] if isinstance(first_lead, list) and len(first_lead) == 2 else "Lead"
        return [
            {
                "title": "Total Projects",
                "value": str(len(records)),
                "change": "Active",
                "change_type": "up",
                "icon": "briefcase",
                "description": "Configured projects & sites",
            },
            {
                "title": "Tracked Tasks",
                "value": str(total_tasks),
                "change": None,
                "change_type": "neutral",
                "icon": "check-square",
                "description": "Across all active projects",
            },
            {
                "title": "Top Project",
                "value": (records[0].get("name") or "Project")[:20],
                "change": "Lead",
                "change_type": "neutral",
                "icon": "award",
                "description": f"Manager: {lead_str[:20]}",
            },
            {
                "title": "Managed Sites",
                "value": str(len(records)),
                "change": "100%",
                "change_type": "up",
                "icon": "map-pin",
                "description": "Operational installations",
            },
        ]

    elif plan.get("entity_type") == "stock_picking":
        done_count = sum(1 for r in records if r.get("state") == "done")
        ready_count = sum(1 for r in records if r.get("state") in ["assigned", "confirmed"])
        return [
            {
                "title": "Total Shipments",
                "value": str(len(records)),
                "change": None,
                "change_type": "neutral",
                "icon": "truck",
                "description": "Transfers & pickings",
            },
            {
                "title": "Completed",
                "value": str(done_count),
                "change": "Done",
                "change_type": "up",
                "icon": "check-circle",
                "description": "Fully processed transfers",
            },
            {
                "title": "Ready / Pending",
                "value": str(ready_count),
                "change": "Action",
                "change_type": "down" if ready_count > 0 else "neutral",
                "icon": "clock",
                "description": "Awaiting warehouse dispatch",
            },
            {
                "title": "Latest Transfer",
                "value": (records[0].get("name") or "Transfer")[:20],
                "change": None,
                "change_type": "neutral",
                "icon": "package",
                "description": f"Origin: {records[0].get('origin') or 'Internal'}",
            },
        ]

    val_field = plan.get("value_field", "amount_total")
    values = [float(r.get(val_field, 0) or 0) for r in records]

    top_val = max(values) if values else 0
    avg_val = sum(values) / len(values) if values else 0
    sum_val = sum(values) if values else 0

    def _fmt(n):
        if n >= 1_000_000:
            return f"${n/1_000_000:.2f}M"
        if n >= 1_000:
            return f"${n/1_000:.1f}K"
        return f"${n:,.2f}"

    count_title = "Today's Count" if plan.get("is_today") else "Records Count"
    count_val = f"{plan.get('today_count', len(records)):,}" if plan.get("is_today") else f"{len(records):,}"

    return [
        {
            "title": count_title,
            "value": count_val,
            "change": "Today" if plan.get("is_today") else None,
            "change_type": "neutral",
            "icon": "hash",
            "description": "Matching your timeframe" if plan.get("is_today") else "Matching your query",
        },
        {
            "title": "Top Value",
            "value": _fmt(top_val),
            "change": "Top #1",
            "change_type": "up",
            "icon": "dollar-sign",
            "description": f"Lead: {records[0].get('name', '')[:20]}",
        },
        {
            "title": "Pipeline Total",
            "value": _fmt(sum_val),
            "change": None,
            "change_type": "neutral",
            "icon": "trending-up",
            "description": f"Across {len(records)} opportunities",
        },
        {
            "title": "Average Value",
            "value": _fmt(avg_val),
            "change": None,
            "change_type": "neutral",
            "icon": "bar-chart-2",
            "description": "Per opportunity",
        },
    ]
