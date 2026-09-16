"""
mAifelZ AI Odoo Copilot — PDF & Excel Report Generator
Generates branded executive reports from AI report data.
"""
import io
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime


HTML_REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
  
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  
  body {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
    color: #1a1a2e;
    background: #ffffff;
    font-size: 12px;
    line-height: 1.6;
  }}
  
  .header {{
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    color: white;
    padding: 40px 50px 30px;
    position: relative;
    overflow: hidden;
  }}
  
  .header::before {{
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.3) 0%, transparent 70%);
    border-radius: 50%;
  }}
  
  .brand-name {{
    font-size: 28px;
    font-weight: 800;
    background: linear-gradient(90deg, #8b5cf6, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.5px;
    margin-bottom: 4px;
  }}
  
  .brand-tagline {{
    font-size: 11px;
    color: rgba(255,255,255,0.6);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 30px;
  }}
  
  .report-title {{
    font-size: 24px;
    font-weight: 700;
    color: white;
    margin-bottom: 8px;
  }}
  
  .report-meta {{
    font-size: 11px;
    color: rgba(255,255,255,0.5);
    display: flex;
    gap: 20px;
  }}
  
  .content {{
    padding: 40px 50px;
  }}
  
  .section-title {{
    font-size: 14px;
    font-weight: 700;
    color: #1a1a2e;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid #8b5cf6;
    display: inline-block;
  }}
  
  .executive-summary {{
    background: linear-gradient(135deg, #f0f4ff, #faf5ff);
    border-left: 4px solid #8b5cf6;
    padding: 20px 24px;
    border-radius: 8px;
    margin-bottom: 32px;
    font-size: 13px;
    color: #374151;
    line-height: 1.8;
  }}
  
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 32px;
  }}
  
  .kpi-card {{
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }}
  
  .kpi-value {{
    font-size: 22px;
    font-weight: 800;
    color: #8b5cf6;
    margin-bottom: 4px;
  }}
  
  .kpi-title {{
    font-size: 10px;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  
  .data-table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 32px;
    font-size: 11px;
  }}
  
  .data-table th {{
    background: linear-gradient(135deg, #8b5cf6, #6366f1);
    color: white;
    padding: 12px 16px;
    text-align: left;
    font-weight: 600;
    font-size: 10px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }}
  
  .data-table td {{
    padding: 10px 16px;
    border-bottom: 1px solid #f3f4f6;
    color: #374151;
  }}
  
  .data-table tr:nth-child(even) td {{
    background: #fafafa;
  }}
  
  .data-table tr:hover td {{
    background: #f0f4ff;
  }}
  
  .insights-section {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 32px;
  }}
  
  .insights-box {{
    background: #f8faff;
    border: 1px solid #e0e7ff;
    border-radius: 12px;
    padding: 20px;
  }}
  
  .insights-box h4 {{
    font-size: 12px;
    font-weight: 700;
    color: #4c1d95;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  
  .insights-box ul {{
    list-style: none;
    padding: 0;
  }}
  
  .insights-box li {{
    padding: 6px 0;
    font-size: 11px;
    color: #374151;
    padding-left: 20px;
    position: relative;
  }}
  
  .insights-box li::before {{
    content: '▸';
    color: #8b5cf6;
    position: absolute;
    left: 0;
  }}
  
  .footer {{
    background: #1a1a2e;
    color: rgba(255,255,255,0.5);
    padding: 20px 50px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 10px;
    letter-spacing: 0.5px;
  }}
  
  .footer-brand {{
    font-weight: 700;
    color: #8b5cf6;
  }}
  
  .confidential {{
    background: #fee2e2;
    color: #991b1b;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
</style>
</head>
<body>

<div class="header">
  <div class="brand-name">mAifelZ</div>
  <div class="brand-tagline">AI Odoo Copilot · Powered by Artificial Intelligence</div>
  <div class="report-title">{report_title}</div>
  <div class="report-meta">
    <span>📅 Generated: {generated_at}</span>
    <span>🔒 Confidential</span>
  </div>
</div>

<div class="content">
  
  <div class="executive-summary">
    <div class="section-title">Executive Summary</div><br>
    {executive_summary}
  </div>
  
  {kpi_section}
  
  {data_table}
  
  {insights_section}
  
</div>

<div class="footer">
  <span><span class="footer-brand">mAifelZ Technologies</span> · AI-Powered ERP Intelligence</span>
  <span class="confidential">Confidential</span>
  <span>Page 1 of 1</span>
</div>

</body>
</html>"""


def generate_html_report(report_data: Dict[str, Any], branding: Optional[Dict] = None) -> str:
    """Generate an HTML report from AI report data."""
    
    generated_at = datetime.now().strftime("%B %d, %Y at %H:%M")
    
    # KPI section
    kpi_html = ""
    kpis = report_data.get("kpi_cards", [])
    if kpis:
        kpi_cards_html = ""
        for kpi in kpis[:4]:
            kpi_cards_html += f"""
            <div class="kpi-card">
              <div class="kpi-value">{kpi.get('value', 'N/A')}</div>
              <div class="kpi-title">{kpi.get('title', '')}</div>
            </div>"""
        kpi_html = f'<div class="kpi-grid">{kpi_cards_html}</div>'
    
    # Data table section
    table_html = ""
    sections = report_data.get("sections", [])
    if sections:
        section = sections[0]
        data = section.get("data", [])
        if data:
            headers = list(data[0].keys()) if data else []
            rows_html = ""
            for row in data[:50]:  # Max 50 rows
                cells = "".join(
                    f"<td>{v if v is not None else ''}</td>"
                    for k, v in row.items()
                    if k in headers
                )
                rows_html += f"<tr>{cells}</tr>"
            
            header_row = "".join(f"<th>{h.replace('_', ' ').title()}</th>" for h in headers)
            table_html = f"""
            <div class="section-title">Data Breakdown</div>
            <table class="data-table">
              <thead><tr>{header_row}</tr></thead>
              <tbody>{rows_html}</tbody>
            </table>"""
    
    # Insights section
    insights = report_data.get("insights", [])
    recommendations = report_data.get("recommendations", [])
    insights_html = ""
    if insights or recommendations:
        ins_items = "".join(f"<li>{i}</li>" for i in insights[:6])
        rec_items = "".join(f"<li>{r}</li>" for r in recommendations[:6])
        insights_html = f"""
        <div class="insights-section">
          <div class="insights-box">
            <h4>🔍 Key Insights</h4>
            <ul>{ins_items}</ul>
          </div>
          <div class="insights-box">
            <h4>💡 Recommendations</h4>
            <ul>{rec_items}</ul>
          </div>
        </div>"""
    
    return HTML_REPORT_TEMPLATE.format(
        report_title=report_data.get("report_title", "AI Report"),
        generated_at=generated_at,
        executive_summary=report_data.get("executive_summary", ""),
        kpi_section=kpi_html,
        data_table=table_html,
        insights_section=insights_html,
    )


def generate_excel_report(report_data: Dict[str, Any]) -> bytes:
    """Generate an Excel file from report data."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Report"

        # Title row
        title = report_data.get("report_title", "Report")
        ws["A1"] = f"mAifelZ AI Copilot — {title}"
        ws["A1"].font = Font(bold=True, size=15, color="5A165D")
        ws["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ws["A2"].font = Font(color="6B7280", size=10)

        # Summary / Direct Answer
        direct_ans = report_data.get("direct_answer") or report_data.get("executive_summary") or ""
        row = 4
        if direct_ans:
            ws.cell(row=row, column=1, value="EXECUTIVE SUMMARY").font = Font(bold=True, size=11, color="5A165D")
            row += 1
            ws.cell(row=row, column=1, value=direct_ans)
            ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
            row += 2

        # Detailed Records Table
        records = report_data.get("table_records") or []
        columns = report_data.get("table_columns") or []

        # Fallback to sections data if table_records is empty
        if not records and report_data.get("sections"):
            sec_data = report_data["sections"][0].get("data", [])
            if sec_data:
                records = sec_data
                columns = [{"field": k, "label": k.replace("_", " ").title()} for k in sec_data[0].keys()]

        if records and columns:
            ws.cell(row=row, column=1, value="DATA RECORDS").font = Font(bold=True, size=11, color="5A165D")
            row += 1
            headers = [c.get("label", c.get("field", "")) for c in columns]
            fields = [c.get("field", "") for c in columns]

            # Header row
            for col_idx, h in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col_idx, value=str(h))
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="5A165D")
                cell.alignment = Alignment(horizontal="center")
            row += 1

            # Record rows
            for record in records:
                for col_idx, f in enumerate(fields, 1):
                    val = record.get(f, "")
                    if isinstance(val, (list, tuple)) and len(val) == 2:
                        val = val[1]
                    ws.cell(row=row, column=col_idx, value=val)
                row += 1

        # Auto-fit columns
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 45)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    except Exception:
        # Fallback to simple CSV bytes
        records = report_data.get("table_records") or []
        if records:
            headers = list(records[0].keys())
            lines = [",".join(headers)]
            for row in records:
                lines.append(",".join(str(row.get(h, "")) for h in headers))
            return "\n".join(lines).encode()
        return b"No data"

