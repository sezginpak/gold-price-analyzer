"""
Gold Price Analyzer Web Interface
"""
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os
from pathlib import Path

from storage.sqlite_storage import SQLiteStorage
from services.harem_altin_service import HaremAltinPriceService
from config import settings

app = FastAPI(title="Gold Price Analyzer Dashboard")

# Templates
templates = Jinja2Templates(directory="templates")

# Storage
storage = SQLiteStorage()

# WebSocket clients
active_connections: List[WebSocket] = []

# Global stats
system_stats = {
    "start_time": datetime.now(),
    "last_price_update": None,
    "total_signals": 0,
    "active_connections": 0,
    "errors_today": 0
}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Ana dashboard sayfası"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/stats")
async def get_stats():
    """Sistem istatistikleri"""
    db_stats = storage.get_statistics()
    
    # Uptime hesapla
    uptime = datetime.now() - system_stats["start_time"]
    
    # Bugünkü sinyalleri say
    today_signals = 0
    signal_file = f"signals/signals_{datetime.now().strftime('%Y%m%d')}.log"
    if os.path.exists(signal_file):
        with open(signal_file, 'r') as f:
            today_signals = f.read().count("Type:")
    
    return {
        "system": {
            "uptime": str(uptime).split('.')[0],
            "last_update": system_stats["last_price_update"],
            "active_connections": len(active_connections),
            "errors_today": system_stats["errors_today"]
        },
        "database": {
            "total_records": db_stats.get("total_records", 0),
            "oldest_record": db_stats.get("oldest_record"),
            "newest_record": db_stats.get("newest_record"),
            "average_price": db_stats.get("average_price")
        },
        "signals": {
            "today": today_signals,
            "total": system_stats["total_signals"]
        }
    }


@app.get("/api/prices/latest")
async def get_latest_prices():
    """Son 100 fiyat verisi"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    prices = storage.get_price_range(start_time, end_time)
    
    return {
        "prices": [
            {
                "timestamp": p.timestamp.isoformat(),
                "ons_usd": float(p.ons_usd),
                "usd_try": float(p.usd_try),
                "ons_try": float(p.ons_try)
            }
            for p in prices[-100:]  # Son 100 kayıt
        ]
    }


@app.get("/api/candles/{interval}")
async def get_candles(interval: str):
    """OHLC mum verileri"""
    interval_map = {
        "15m": 15,
        "1h": 60,
        "4h": 240,
        "1d": 1440
    }
    
    minutes = interval_map.get(interval, 60)
    candles = storage.generate_candles(minutes, 100)
    
    return {
        "candles": [
            {
                "timestamp": c.timestamp.isoformat(),
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close)
            }
            for c in candles
        ]
    }


@app.get("/api/signals/today")
async def get_today_signals():
    """Bugünkü sinyaller"""
    signals = []
    signal_file = f"signals/signals_{datetime.now().strftime('%Y%m%d')}.log"
    
    if os.path.exists(signal_file):
        with open(signal_file, 'r') as f:
            content = f.read()
            
        # Parse signals (basit parser)
        signal_blocks = content.split('-' * 50)
        for block in signal_blocks:
            if "Type:" in block:
                lines = block.strip().split('\n')
                signal = {}
                for line in lines:
                    if line.startswith('Type:'):
                        signal['type'] = line.split(':')[1].strip()
                    elif line.startswith('Price:'):
                        signal['price'] = line.split(':')[1].strip()
                    elif line.startswith('Confidence:'):
                        signal['confidence'] = line.split(':')[1].strip()
                    elif line.startswith('Target:'):
                        signal['target'] = line.split(':')[1].strip()
                    elif line.startswith('Stop:'):
                        signal['stop_loss'] = line.split(':')[1].strip()
                    elif line and not line.startswith('Reasons:'):
                        try:
                            signal['timestamp'] = line
                        except:
                            pass
                if signal:
                    signals.append(signal)
    
    return {"signals": signals}


@app.get("/api/logs/recent")
async def get_recent_logs():
    """Son log satırları"""
    log_file = "logs/gold_analyzer.log"
    error_file = "logs/gold_analyzer_errors.log"
    
    logs = {"main": [], "errors": []}
    
    # Ana loglar
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            lines = f.readlines()
            logs["main"] = [line.strip() for line in lines[-50:]]  # Son 50 satır
    
    # Hata logları
    if os.path.exists(error_file):
        with open(error_file, 'r') as f:
            lines = f.readlines()
            logs["errors"] = [line.strip() for line in lines[-20:]]  # Son 20 hata
    
    return logs


@app.get("/menu")
async def get_menu(request: Request):
    """Menu component'i döndür"""
    return templates.TemplateResponse("menu.html", {"request": request})


@app.get("/analysis")
async def analysis_page(request: Request):
    """Analiz sayfası"""
    return templates.TemplateResponse("analysis.html", {"request": request})


@app.get("/api/analysis/config")
async def get_analysis_config():
    """Analiz konfigürasyonunu döndür"""
    return {
        "collection_interval": settings.collection_interval,
        "support_resistance_lookback": settings.support_resistance_lookback,
        "rsi_period": settings.rsi_period,
        "ma_short_period": settings.ma_short_period,
        "ma_long_period": settings.ma_long_period,
        "min_confidence_score": settings.min_confidence_score,
        "risk_tolerance": settings.risk_tolerance
    }


@app.get("/api/analysis/history")
async def get_analysis_history():
    """Son analiz sonuçlarını döndür"""
    # TODO: Gerçek analiz verilerini saklamak için bir sistem eklenecek
    # Şimdilik mock data
    mock_analyses = []
    
    # Son 10 analiz için mock data oluştur
    current_price = storage.get_latest_price()
    if current_price:
        base_price = float(current_price.ons_try)
        
        for i in range(10):
            timestamp = datetime.now() - timedelta(minutes=5*i)
            price_variation = base_price * (1 + (i * 0.001))
            
            # Trend belirleme
            if i < 3:
                trend = "BULLISH"
                signal = "BUY" if i == 0 else None
            elif i < 7:
                trend = "NEUTRAL"
                signal = None
            else:
                trend = "BEARISH"
                signal = "SELL" if i == 9 else None
            
            mock_analyses.append({
                "timestamp": timestamp.isoformat(),
                "price": price_variation,
                "trend": trend,
                "strength": "Güçlü" if signal else "Orta",
                "signal": signal,
                "confidence": 0.85 if signal else 0.65
            })
    
    return {"analyses": mock_analyses}


@app.get("/api/debug/candles")
async def debug_candles():
    """Mum verisi debug"""
    prices = storage.get_latest_prices(100)
    candles_15m = storage.generate_candles(15, 10)
    
    return {
        "total_prices": len(prices),
        "oldest_price": prices[0].timestamp.isoformat() if prices else None,
        "newest_price": prices[-1].timestamp.isoformat() if prices else None,
        "candles_15m_count": len(candles_15m),
        "first_candle": candles_15m[0].timestamp.isoformat() if candles_15m else None,
        "last_candle": candles_15m[-1].timestamp.isoformat() if candles_15m else None
    }


@app.get("/api/analysis/levels")
async def get_support_resistance():
    """Destek/Direnç seviyeleri"""
    try:
        # Son 100 veriyi al
        prices = storage.get_latest_prices(100)
        if len(prices) < 10:
            return {"support": [], "resistance": []}
        
        # Basit destek/direnç hesaplama
        price_values = [float(p.ons_try) for p in prices]
        avg_price = sum(price_values) / len(price_values)
        min_price = min(price_values)
        max_price = max(price_values)
        
        # Basit seviyeler
        support_levels = [
            {"level": min_price, "strength": "Güçlü"},
            {"level": min_price + (avg_price - min_price) * 0.382, "strength": "Orta"},
            {"level": avg_price * 0.98, "strength": "Zayıf"}
        ]
        
        resistance_levels = [
            {"level": max_price, "strength": "Güçlü"},
            {"level": avg_price + (max_price - avg_price) * 0.618, "strength": "Orta"},
            {"level": avg_price * 1.02, "strength": "Zayıf"}
        ]
        
        return {
            "support": sorted(support_levels, key=lambda x: x["level"], reverse=True),
            "resistance": sorted(resistance_levels, key=lambda x: x["level"])
        }
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return {"support": [], "resistance": []}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket bağlantısı - canlı güncellemeler"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Her 5 saniyede bir güncelleme gönder
            await asyncio.sleep(5)
            
            # Son fiyat
            latest_price = storage.get_latest_price()
            if latest_price:
                data = {
                    "type": "price_update",
                    "data": {
                        "timestamp": latest_price.timestamp.isoformat(),
                        "ons_usd": float(latest_price.ons_usd),
                        "usd_try": float(latest_price.usd_try),
                        "ons_try": float(latest_price.ons_try)
                    }
                }
                await websocket.send_json(data)
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)


# Ana uygulama ile birlikte çalıştırmak için
async def update_stats_periodically():
    """İstatistikleri periyodik güncelle"""
    while True:
        await asyncio.sleep(60)  # Her dakika
        
        latest = storage.get_latest_price()
        if latest:
            system_stats["last_price_update"] = latest.timestamp.isoformat()


# Startup event
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_stats_periodically())