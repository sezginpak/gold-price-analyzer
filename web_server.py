"""
Gold Price Analyzer Web Interface
"""
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
import asyncio
import logging
from utils import timezone

from storage.sqlite_storage import SQLiteStorage
from utils.logger import setup_logger
from web import (
    dashboard_router,
    api_router,
    analysis_router,
    simulation_router,
    WebSocketManager,
    stats
)

# Web server için ayrı logger
logger = setup_logger(
    name="gold_analyzer_web",
    log_dir="logs",
    level="INFO"
)

# FastAPI app
app = FastAPI(title="Dezy - Gold Price Analyzer Dashboard")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Storage ve managers
storage = SQLiteStorage()
websocket_manager = WebSocketManager(storage)

# Route'ları ekle
app.include_router(dashboard_router)
app.include_router(api_router)
app.include_router(analysis_router)
app.include_router(simulation_router)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket bağlantısı - canlı güncellemeler"""
    await websocket_manager.handle_connection(websocket)

# Ana uygulama ile birlikte çalıştırmak için
async def update_stats_periodically():
    """İstatistikleri periyodik güncelle"""
    while True:
        await asyncio.sleep(60)  # Her dakika
        
        latest = storage.get_latest_price()
        if latest:
            stats.update("last_price_update", latest.timestamp.isoformat())
        
        # Aktif bağlantı sayısını güncelle
        stats.update("active_connections", websocket_manager.get_connection_count())

# Startup event
@app.on_event("startup")
async def startup_event():
    """Uygulama başlangıcında çalışacak işlemler"""
    logger.info("Web server başlatılıyor...")
    
    # İstatistik güncelleme task'ini başlat
    asyncio.create_task(update_stats_periodically())
    
    # Başlangıç istatistiklerini ayarla
    stats.update("start_time", timezone.now())
    stats.update("active_connections", 0)
    stats.update("errors_today", 0)
    stats.update("total_signals", 0)
    
    logger.info("Web server başlatıldı")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Uygulama kapanırken çalışacak işlemler"""
    logger.info("Web server kapatılıyor...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)