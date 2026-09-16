"""
MCP Tools Package - Intelligent Field Selection and Data Formatting for Odoo ORM.
Derived from the Odoo MCP Server module to guarantee accurate, LLM-optimized payloads.
"""
from .smart_fields import (
    get_smart_default_fields,
    score_field_importance,
    is_sensitive_field_name,
    ESSENTIAL_FIELDS,
)
from .formatters import (
    RecordFormatter,
    DatasetFormatter,
)

__all__ = [
    "get_smart_default_fields",
    "score_field_importance",
    "is_sensitive_field_name",
    "ESSENTIAL_FIELDS",
    "RecordFormatter",
    "DatasetFormatter",
]
