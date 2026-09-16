"""
mAifelZ AI Odoo Copilot — Report Export Routes
Generates PDF, Excel, and CSV exports from AI report data.
"""
import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import ExportRequest
from services.report_generator import generate_html_report, generate_excel_report

router = APIRouter(prefix="/reports", tags=["Report Export"])


@router.post("/export/html")
async def export_html(request: ExportRequest):
    """Export report as branded HTML (for preview and PDF generation)."""
    try:
        data = request.report_data if isinstance(request.report_data, dict) else request.report_data.dict()
        html = generate_html_report(data, request.branding)
        return {"html": html}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/excel")
async def export_excel(request: ExportRequest):
    """Export report data as Excel spreadsheet."""
    try:
        data = request.report_data if isinstance(request.report_data, dict) else request.report_data.dict()
        excel_bytes = generate_excel_report(data)
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="maifelz_report.xlsx"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/csv")
async def export_csv(request: ExportRequest):
    """Export raw data as CSV."""
    try:
        sections = request.report_data.sections
        if not sections or not sections[0].data:
            raise HTTPException(status_code=400, detail="No data to export")
        
        data = sections[0].data
        headers = list(data[0].keys()) if data else []
        
        lines = [",".join(headers)]
        for row in data:
            lines.append(",".join(str(row.get(h, "")) for h in headers))
        
        csv_content = "\n".join(lines)
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="maifelz_report.csv"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
