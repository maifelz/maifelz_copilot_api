"""
mAifelZ AI Odoo Copilot — Universal Odoo XML-RPC Connector

Works with ANY Odoo version (v12 through v18+), any hosting:
- Odoo.sh, Odoo Online (SaaS), on-premise, AWS, Azure, etc.
No module installation required on the client's Odoo instance.
"""
import xmlrpc.client
import ssl
import hashlib
import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime


# In-memory connection store (replace with DB in production)
_connections: Dict[str, Dict] = {}


class OdooConnector:
    """
    Thin, stateless XML-RPC gateway for any Odoo instance.
    All communication uses Odoo's native XML-RPC endpoints:
      /xmlrpc/2/common  -> authentication, version
      /xmlrpc/2/object  -> model operations (search, read, write, etc.)
    """

    def __init__(self, url: str, database: str, username: str, password: str):
        self.url = url.rstrip("/")
        self.database = database
        self.username = username
        self.password = password
        self.uid: Optional[int] = None
        self._common_proxy = None
        self._object_proxy = None

    def _build_proxy(self, endpoint: str) -> xmlrpc.client.ServerProxy:
        """Build an XML-RPC proxy, accepting all SSL certificates for flexibility."""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        transport = xmlrpc.client.SafeTransport(context=context)
        return xmlrpc.client.ServerProxy(
            f"{self.url}{endpoint}",
            transport=transport,
            allow_none=True
        )

    @property
    def common(self) -> xmlrpc.client.ServerProxy:
        if not self._common_proxy:
            self._common_proxy = self._build_proxy("/xmlrpc/2/common")
        return self._common_proxy

    @property
    def models(self) -> xmlrpc.client.ServerProxy:
        if not self._object_proxy:
            self._object_proxy = self._build_proxy("/xmlrpc/2/object")
        return self._object_proxy

    def authenticate(self) -> Tuple[bool, str]:
        """Authenticate with Odoo and store the user ID. Returns (success, message)."""
        # Smart Odoo.sh fallback: if user provided .odoo.com but it is a dev branch, try .dev.odoo.com
        urls_to_try = [self.url]
        if ".odoo.com" in self.url and ".dev.odoo.com" not in self.url and ".staging.odoo.com" not in self.url:
            urls_to_try.append(self.url.replace(".odoo.com", ".dev.odoo.com"))
            urls_to_try.append(self.url.replace(".odoo.com", ".staging.odoo.com"))

        last_error = ""
        for test_url in urls_to_try:
            try:
                self.url = test_url
                self._common_proxy = None
                self._object_proxy = None
                version_info = self.common.version()
                self.odoo_version = version_info.get("server_version", "Unknown")
                
                uid = self.common.authenticate(
                    self.database, self.username, self.password, {}
                )
                if not uid:
                    return False, "Invalid credentials or database name"
                
                self.uid = uid
                return True, f"Connected to Odoo {self.odoo_version}"
            except Exception as e:
                last_error = str(e)
                if "404" in last_error or "Not Found" in last_error:
                    continue
                elif "Connection refused" in last_error or "Name or service not known" in last_error:
                    continue
                else:
                    return False, f"Connection error: {last_error}"

        return False, f"Cannot reach Odoo server at {self.url} (Error: {last_error})"

    def execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """Execute any Odoo model method via XML-RPC."""
        if not self.uid:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        return self.models.execute_kw(
            self.database, self.uid, self.password,
            model, method, list(args), kwargs
        )

    def search_read(
        self,
        model: str,
        domain: list,
        fields: List[str],
        limit: int = 1000,
        order: str = "",
        offset: int = 0,
    ) -> List[Dict]:
        """Convenience wrapper for search_read."""
        kwargs = {"fields": fields, "limit": limit, "offset": offset}
        if order:
            kwargs["order"] = order
        return self.execute(model, "search_read", domain, **kwargs)

    def read_group(
        self,
        model: str,
        domain: list,
        fields: List[str],
        groupby: List[str],
        lazy: bool = False,
        orderby: str = "",
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """Convenience wrapper for read_group (aggregations)."""
        kwargs = {"lazy": lazy}
        if orderby:
            kwargs["orderby"] = orderby
        if limit:
            kwargs["limit"] = limit
        return self.execute(model, "read_group", domain, fields, groupby, **kwargs)

    def create_record(self, model: str, values: Dict[str, Any]) -> int:
        """Create a new record in Odoo and return its new integer ID."""
        return self.execute(model, "create", values)

    def write_record(self, model: str, record_id: int, values: Dict[str, Any]) -> bool:
        """Update an existing record in Odoo."""
        return self.execute(model, "write", [record_id], values)

    def call_action(self, model: str, method: str, record_ids: List[int], *args, **kwargs) -> Any:
        """Call a business method on one or more records (e.g. action_confirm)."""
        return self.execute(model, method, record_ids, *args, **kwargs)

    def get_model_fields(self, model: str) -> Dict[str, Dict]:
        """Get field definitions for a model (introspection)."""
        return self.execute(model, "fields_get", [], attributes=["string", "type", "relation", "required"])

    def get_company_info(self) -> Dict:
        """Get the connected company info."""
        try:
            companies = self.search_read(
                "res.company", [], ["name", "currency_id", "country_id"], limit=1
            )
            if companies:
                return companies[0]
        except Exception:
            pass
        return {}

    def get_available_models(self) -> List[Dict]:
        """List all accessible Odoo models."""
        return self.search_read(
            "ir.model",
            [["transient", "=", False]],
            ["name", "model", "info"],
            limit=500,
            order="name asc"
        )


import json
import os

CONNECTIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "connections.json")

def _load_connections():
    global _connections
    try:
        if os.path.exists(CONNECTIONS_FILE):
            with open(CONNECTIONS_FILE, "r") as f:
                _connections = json.load(f)
    except Exception:
        pass

def _save_connections():
    try:
        os.makedirs(os.path.dirname(CONNECTIONS_FILE), exist_ok=True)
        with open(CONNECTIONS_FILE, "w") as f:
            json.dump(_connections, f, indent=2)
    except Exception:
        pass

_load_connections()


def save_connection(
    url: str,
    database: str,
    username: str,
    password: str,
    label: str,
    uid: int,
    odoo_version: str,
    company_name: str,
) -> str:
    """Persist a verified connection in memory and on disk."""
    connection_id = str(uuid.uuid4())
    _connections[connection_id] = {
        "id": connection_id,
        "url": url,
        "database": database,
        "username": username,
        "password": password,
        "label": label or f"{url.split('//')[1].split('/')[0]}",
        "uid": uid,
        "odoo_version": odoo_version,
        "company_name": company_name,
        "created_at": datetime.utcnow().isoformat(),
        "last_used": datetime.utcnow().isoformat(),
    }
    _save_connections()
    return connection_id


def get_connection(connection_id: str) -> Optional[Dict]:
    """Retrieve a stored connection by ID."""
    _load_connections()
    return _connections.get(connection_id)


def list_connections() -> List[Dict]:
    """List all stored connections (without exposing passwords)."""
    _load_connections()
    return [
        {k: v for k, v in conn.items() if k != "password"}
        for conn in _connections.values()
    ]


def remove_connection(connection_id: str) -> bool:
    """Remove a stored connection."""
    _load_connections()
    if connection_id in _connections:
        del _connections[connection_id]
        _save_connections()
        return True
    return False


def get_connector(connection_id: str) -> Optional[OdooConnector]:
    """Build and return an authenticated OdooConnector from a stored connection."""
    conn = get_connection(connection_id)
    if not conn:
        return None

    url = conn.get("url", "")
    # Auto-repair URL if .dev was missing
    if ".odoo.com" in url and ".dev.odoo.com" not in url and ".staging.odoo.com" not in url:
        url = url.replace(".odoo.com", ".dev.odoo.com")
        conn["url"] = url
        _connections[connection_id] = conn
        _save_connections()

    connector = OdooConnector(
        url=url,
        database=conn["database"],
        username=conn["username"],
        password=conn["password"],
    )
    connector.uid = conn["uid"]
    connector.odoo_version = conn.get("odoo_version", "Unknown")
    
    # Auto-resolve company name if Unknown
    if conn.get("company_name") in ["Unknown", "Unknown Company", "", None]:
        try:
            comp = connector.get_company_info()
            if comp and comp.get("name"):
                conn["company_name"] = comp["name"]
                _connections[connection_id] = conn
                _save_connections()
        except Exception:
            pass
            
    return connector
