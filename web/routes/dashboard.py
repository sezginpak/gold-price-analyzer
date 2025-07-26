"""
Dashboard (template) route'ları
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Ana dashboard sayfası"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/menu", response_class=HTMLResponse)
async def get_menu(request: Request):
    """Menu component'i döndür"""
    return templates.TemplateResponse("menu.html", {"request": request})

@router.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request):
    """Analiz sayfası"""
    return templates.TemplateResponse("analysis.html", {"request": request})

@router.get("/signals", response_class=HTMLResponse)
async def signals_page(request: Request):
    """Sinyaller sayfası"""
    return templates.TemplateResponse("signals.html", {"request": request})

@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Log görüntüleme sayfası"""
    return templates.TemplateResponse("logs.html", {"request": request})

@router.get("/simulations", response_class=HTMLResponse)
async def simulations_page(request: Request):
    """Simülasyon sayfası"""
    return templates.TemplateResponse("simulations.html", {"request": request})