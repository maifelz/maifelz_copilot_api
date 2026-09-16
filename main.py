"""
mAifelZ AI Odoo Copilot — FastAPI Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from routers import odoo, ai, reports, admin, auth

# ── App Setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="mAifelZ AI Odoo Copilot API",
    description="Connect any Odoo database and generate AI-powered reports via natural language prompts.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS (allow Next.js frontend & production domain) ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://copilot.maifelz.com",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(odoo.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")



# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "product": "mAifelZ AI Odoo Copilot",
        "version": "1.0.0",
        "company": "mAifelZ Technologies",
        "status": "operational",
        "docs": "/api/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "maifelz-odoo-copilot-api"}


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
