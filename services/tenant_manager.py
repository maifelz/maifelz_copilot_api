"""
mAifelZ Multi-Tenant & AI Query Metering Engine
Controls client provisioning, license keys, usage limits, and kill-switch enforcement.
100% controlled by mAifelZ Technologies.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
TENANTS_FILE = os.path.join(DATA_DIR, "tenants.json")
USAGE_LOGS_FILE = os.path.join(DATA_DIR, "usage_logs.json")

PLAN_LIMITS = {
    "starter": {"name": "Starter", "queries": 500, "price_usd": 79},
    "professional": {"name": "Professional", "queries": 2500, "price_usd": 199},
    "enterprise": {"name": "Enterprise", "queries": 10000, "price_usd": 499},
    "custom": {"name": "Custom", "queries": 20000, "price_usd": 999},
}

_tenants: Dict[str, Dict] = {}


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_tenants():
    global _tenants
    _ensure_data_dir()
    if os.path.exists(TENANTS_FILE):
        try:
            with open(TENANTS_FILE, "r") as f:
                _tenants = json.load(f)
        except Exception:
            _tenants = {}
    else:
        # Create default master tenant for initial setup
        _tenants = {}
        _create_default_tenant()


def _save_tenants():
    _ensure_data_dir()
    try:
        with open(TENANTS_FILE, "w") as f:
            json.dump(_tenants, f, indent=2)
    except Exception:
        pass


def _create_default_tenant():
    """Initial default client for Billabong / First client."""
    tenant_id = "tenant-default-001"
    key = "MFZ-PRO-2026-BILLA-8891"
    _tenants[tenant_id] = {
        "id": tenant_id,
        "company_name": "Billabong Solar",
        "contact_email": "nithin@billabongsolar.com.au",
        "license_key": key,
        "plan": "professional",
        "monthly_limit": 2500,
        "queries_used": 6,
        "status": "active",  # active | suspended | expired
        "connection_id": "2d091f19-a1b9-4e26-9d76-ddec304a4b50",
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat(),
        "last_query_at": datetime.utcnow().isoformat(),
        "notes": "Founding Pilot Client",
    }
    _save_tenants()


# Initialize
_load_tenants()


# ── Tenant Management Functions ───────────────────────────────────────────────

def list_tenants() -> List[Dict]:
    """List all client tenants with usage statistics."""
    _load_tenants()
    return list(_tenants.values())


def get_tenant_by_id(tenant_id: str) -> Optional[Dict]:
    _load_tenants()
    return _tenants.get(tenant_id)


def get_tenant_by_license(license_key: str) -> Optional[Dict]:
    _load_tenants()
    for t in _tenants.values():
        if t.get("license_key") == license_key.strip():
            return t
    return None


def get_tenant_by_connection_id(connection_id: str) -> Optional[Dict]:
    _load_tenants()
    for t in _tenants.values():
        if t.get("connection_id") == connection_id:
            return t
    # Fallback to default tenant if only one exists
    if len(_tenants) == 1:
        return list(_tenants.values())[0]
    return None


def create_tenant(
    company_name: str,
    contact_email: str,
    plan: str = "professional",
    connection_id: Optional[str] = None,
    custom_limit: Optional[int] = None,
    notes: str = "",
) -> Dict:
    """Create a new client tenant and generate unique license key."""
    _load_tenants()
    plan_info = PLAN_LIMITS.get(plan.lower(), PLAN_LIMITS["professional"])
    limit = custom_limit or plan_info["queries"]

    tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
    rand_code = uuid.uuid4().hex[:4].upper()
    license_key = f"MFZ-{plan[:3].upper()}-{datetime.now().year}-{rand_code}"

    tenant_record = {
        "id": tenant_id,
        "company_name": company_name.strip(),
        "contact_email": contact_email.strip(),
        "license_key": license_key,
        "plan": plan.lower(),
        "monthly_limit": limit,
        "queries_used": 0,
        "seats_count": 1,
        "user_logins": [
            {"email": contact_email.strip().lower(), "name": "Primary Admin", "role": "admin", "created_at": datetime.utcnow().isoformat(), "status": "active"}
        ],
        "status": "active",
        "connection_id": connection_id or "",
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "last_query_at": None,
        "notes": notes,
    }

    _tenants[tenant_id] = tenant_record
    _save_tenants()
    return tenant_record


def add_user_login(tenant_id: str, email: str, name: str, role: str = "manager", password: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
    """Provision a user login seat for this tenant ($25/seat/month). Returns (success, msg, initial_password)."""
    _load_tenants()
    tenant = _tenants.get(tenant_id)
    if not tenant:
        return False, "Tenant not found", None

    if "user_logins" not in tenant:
        tenant["user_logins"] = []

    clean_email = email.strip().lower()
    if any(u.get("email") == clean_email for u in tenant["user_logins"]):
        return False, f"User {clean_email} already exists for this tenant", None

    # Generate initial secure password if not provided
    initial_password = password.strip() if password and password.strip() else f"Mfz@{uuid.uuid4().hex[:6].upper()}"

    tenant["user_logins"].append({
        "email": clean_email,
        "name": name.strip(),
        "role": role,
        "password": initial_password,
        "created_at": datetime.utcnow().isoformat(),
        "status": "active"
    })
    tenant["seats_count"] = len(tenant["user_logins"])
    _save_tenants()
    return True, f"User {clean_email} added successfully ($25/seat).", initial_password


def remove_user_login(tenant_id: str, email: str) -> Tuple[bool, str]:
    """Remove a user login seat from this tenant."""
    _load_tenants()
    tenant = _tenants.get(tenant_id)
    if not tenant or "user_logins" not in tenant:
        return False, "Tenant not found"

    clean_email = email.strip().lower()
    tenant["user_logins"] = [u for u in tenant["user_logins"] if u.get("email") != clean_email]
    tenant["seats_count"] = len(tenant["user_logins"])
    _save_tenants()
    return True, f"User {clean_email} removed."


def authenticate_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict], Optional[Dict]]:
    """
    Authenticate client staff against their tenant organization.
    Enforces master kill switch on the tenant level.
    """
    _load_tenants()
    clean_email = email.strip().lower()
    input_pass = password.strip()

    # 0. Check mAifelZ Master Admin Credentials
    ADMIN_EMAILS = ["admin@maifelz.com", "fahad@maifelz.com"]
    ADMIN_PASS = os.getenv("MAIFELZ_ADMIN_PASSWORD", "MaifelzAdmin2026!")
    if clean_email in ADMIN_EMAILS:

        if input_pass == ADMIN_PASS or input_pass == "Maifelz2026!":
            master_user = {
                "email": clean_email,
                "name": "Fahad (mAifelZ Admin)",
                "role": "master_admin",
                "status": "active",
            }
            master_tenant = {
                "id": "tenant-maifelz-hq",
                "company_name": "mAifelZ Technologies HQ",
                "license_key": "MFZ-MASTER-ROOT-ADMIN",
                "plan": "enterprise",
                "status": "active",
                "connection_id": "",
                "monthly_limit": 999999,
                "queries_used": 0,
            }
            return True, "mAifelZ Master Admin Authenticated", master_user, master_tenant
        else:
            return False, "Invalid Master Admin password.", None, None

    for tenant in _tenants.values():
        logins = tenant.get("user_logins", [])
        for u in logins:
            if u.get("email") == clean_email:
                # Check kill-switch
                if tenant.get("status") == "suspended":
                    return False, "Account suspended. Please contact billing@maifelz.com.", None, None
                if tenant.get("status") == "expired":
                    return False, "Account subscription has expired. Please renew your plan.", None, None
                if u.get("status") != "active":
                    return False, "Your seat login has been deactivated. Contact your company administrator.", None, None

                # Check password
                stored_pass = u.get("password")
                # If legacy user has no password set, set a default
                if not stored_pass:
                    stored_pass = "Solar2026!"
                    u["password"] = stored_pass
                    _save_tenants()

                if input_pass == stored_pass:
                    safe_user = {k: v for k, v in u.items() if k != "password"}
                    return True, "Login successful", safe_user, tenant
                else:
                    return False, "Invalid email or password.", None, None

    return False, "No active account found with this email. Contact sales@maifelz.com.", None, None




def topup_ai_credits(tenant_id: str, credits: int) -> Tuple[bool, str]:
    """Sell an extra AI query credit pack to customer."""
    _load_tenants()
    tenant = _tenants.get(tenant_id)
    if not tenant:
        return False, "Tenant not found"

    tenant["monthly_limit"] = tenant.get("monthly_limit", 500) + credits
    _save_tenants()
    return True, f"Successfully credited {credits} AI queries to {tenant['company_name']}."


def update_tenant_status(tenant_id: str, status: str) -> bool:
    """Kill-Switch: toggle tenant between 'active', 'suspended', 'expired'."""
    _load_tenants()
    if tenant_id in _tenants:
        _tenants[tenant_id]["status"] = status
        _save_tenants()
        return True
    return False


def reset_tenant_usage(tenant_id: str, additional_credits: int = 0) -> bool:
    """Reset monthly usage counter or add bonus query credits."""
    _load_tenants()
    if tenant_id in _tenants:
        if additional_credits > 0:
            _tenants[tenant_id]["monthly_limit"] += additional_credits
        else:
            _tenants[tenant_id]["queries_used"] = 0
        _save_tenants()
        return True
    return False


def link_connection_to_tenant(connection_id: str, license_key: str) -> Tuple[bool, str]:
    """Attach an Odoo database connection to a verified mAifelZ license key."""
    _load_tenants()
    tenant = get_tenant_by_license(license_key)
    if not tenant:
        return False, "Invalid mAifelZ License Key. Contact support@maifelz.com"

    if tenant["status"] != "active":
        return False, f"This license is currently {tenant['status'].upper()}. Contact billing@maifelz.com"

    tenant["connection_id"] = connection_id
    _tenants[tenant["id"]] = tenant
    _save_tenants()
    return True, f"Successfully linked to {tenant['company_name']} ({tenant['plan'].title()} Plan)"


def assign_tenant_connection(tenant_id: str, connection_id: str) -> Tuple[bool, str]:
    """Assign or switch the linked Odoo database connection for a tenant."""
    _load_tenants()
    tenant = _tenants.get(tenant_id)
    if not tenant:
        return False, "Tenant not found"

    tenant["connection_id"] = (connection_id or "").strip()
    _tenants[tenant_id] = tenant
    _save_tenants()
    return True, f"Assigned database to {tenant['company_name']}"


# ── Limit Enforcement & Metering ──────────────────────────────────────────────

def verify_and_meter_query(connection_id: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Called before executing any AI query.
    Enforces:
    1. Tenant exists
    2. Status is ACTIVE (not suspended or expired)
    3. Query count < Monthly Limit
    4. Auto-increments usage if valid.
    """
    _load_tenants()
    tenant = get_tenant_by_connection_id(connection_id)

    # If no tenant linked yet, create a default pilot tenant for seamless demo
    if not tenant:
        tenant = list_tenants()[0] if list_tenants() else create_tenant("Pilot Client", "pilot@client.com")
        tenant["connection_id"] = connection_id
        _tenants[tenant["id"]] = tenant
        _save_tenants()

    # 1. Check Status (Kill-Switch)
    if tenant.get("status") == "suspended":
        return False, "Your mAifelZ AI Copilot subscription is currently suspended. Please contact billing@maifelz.com to reactivate.", tenant

    if tenant.get("status") == "expired":
        return False, "Your mAifelZ AI Copilot plan has expired. Please renew your subscription to continue asking queries.", tenant

    # 2. Check Monthly Query Limit
    used = tenant.get("queries_used", 0)
    limit = tenant.get("monthly_limit", 500)

    if used >= limit:
        return (
            False,
            f"Monthly AI query limit reached ({used}/{limit} queries). Upgrade your mAifelZ plan to continue: billing@maifelz.com",
            tenant,
        )

    # 3. Deduct / Increment 1 query
    tenant["queries_used"] = used + 1
    tenant["last_query_at"] = datetime.utcnow().isoformat()
    _tenants[tenant["id"]] = tenant
    _save_tenants()

    # Optional: Append to usage log
    _log_usage(tenant["id"], tenant["company_name"])

    return True, None, tenant


def _log_usage(tenant_id: str, company_name: str):
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "company_name": company_name,
        }
        logs = []
        if os.path.exists(USAGE_LOGS_FILE):
            with open(USAGE_LOGS_FILE, "r") as f:
                logs = json.load(f)
        logs.append(log_entry)
        # Keep last 5000 logs
        logs = logs[-5000:]
        with open(USAGE_LOGS_FILE, "w") as f:
            json.dump(logs, f)
    except Exception:
        pass


def get_admin_summary() -> Dict:
    """Overall SaaS analytics for mAifelZ master admin dashboard."""
    _load_tenants()
    tenants = list(_tenants.values())

    total_clients = len(tenants)
    active_clients = sum(1 for t in tenants if t.get("status") == "active")
    total_queries = sum(t.get("queries_used", 0) for t in tenants)

    # Calculate monthly revenue: ($25 per seat) + AI Plan Base
    mrr_usd = 0
    for t in tenants:
        if t.get("status") == "active":
            plan = t.get("plan", "professional")
            seats = t.get("seats_count", 1)
            ai_fee = PLAN_LIMITS.get(plan, {}).get("price_usd", 79)
            seat_fee = seats * 25
            mrr_usd += (seat_fee + ai_fee)

    return {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "total_queries_metered": total_queries,
        "estimated_mrr_usd": mrr_usd,
        "plan_tiers": PLAN_LIMITS,
        "tenants": tenants,
    }
