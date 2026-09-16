"""
mAifelZ AI Odoo Copilot — Pydantic Data Models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from enum import Enum


class OdooConnectionRequest(BaseModel):
    url: str = Field(..., description="Odoo base URL e.g. https://erp.yourcompany.com")
    database: str = Field(..., description="Odoo database name")
    username: str = Field(..., description="Odoo user login email")
    password: str = Field(..., description="Odoo user password or API key")
    label: Optional[str] = Field(None, description="Friendly name for this connection")


class OdooConnectionResponse(BaseModel):
    success: bool
    connection_id: str
    label: str
    odoo_version: Optional[str] = None
    uid: Optional[int] = None
    company_name: Optional[str] = None
    error: Optional[str] = None


class PromptRequest(BaseModel):
    connection_id: str
    prompt: str
    context: Optional[str] = None


class ChartType(str, Enum):
    bar = "bar"
    line = "line"
    pie = "pie"
    donut = "donut"
    area = "area"
    scatter = "scatter"
    table = "table"
    kpi = "kpi"


class ChartDataPoint(BaseModel):
    label: str
    value: float
    secondary_value: Optional[float] = None
    color: Optional[str] = None


class KPICard(BaseModel):
    title: str
    value: str
    change: Optional[str] = None
    change_type: Optional[str] = None  # "up" | "down" | "neutral"
    icon: Optional[str] = None
    description: Optional[str] = None


class ReportSection(BaseModel):
    title: str
    chart_type: ChartType
    data: List[Dict[str, Any]]
    x_key: Optional[str] = None
    y_keys: Optional[List[str]] = None
    summary: Optional[str] = None
    color_scheme: Optional[str] = "default"


class TableColumn(BaseModel):
    key: str
    label: str
    type: Optional[str] = "text"  # text | currency | date | badge


class AIReportResponse(BaseModel):
    success: bool
    prompt: str
    report_title: str
    direct_answer: Optional[str] = None
    executive_summary: str
    kpi_cards: List[KPICard]
    sections: List[ReportSection]
    table_columns: Optional[List[TableColumn]] = None
    table_records: Optional[List[Dict[str, Any]]] = None
    insights: List[str]
    recommendations: List[str]
    raw_data_available: bool
    clarification_question: Optional[str] = None
    follow_up_suggestions: Optional[List[str]] = None
    language: Optional[str] = "en"
    error: Optional[str] = None


class ExportRequest(BaseModel):
    connection_id: str
    report_data: AIReportResponse
    format: str = "pdf"  # pdf | excel | csv
    branding: Optional[Dict[str, str]] = None


class OdooModelsResponse(BaseModel):
    models: List[Dict[str, Any]]


class ConnectionStatus(BaseModel):
    connection_id: str
    is_active: bool
    last_tested: Optional[str] = None
