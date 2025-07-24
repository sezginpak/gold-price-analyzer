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
import logging

from storage.sqlite_storage import SQLiteStorage
from services.harem_altin_service import HaremAltinPriceService
from config import settings
from utils.log_manager import LogManager
from utils.logger import setup_logger
from simulation.simulation_manager import SimulationManager
from models.simulation import SimulationStatus, StrategyType

# Web server için ayrı logger
logger = setup_logger(
    name="gold_analyzer_web",
    log_dir="logs",
    level="INFO"
)

app = FastAPI(title="Gold Price Analyzer Dashboard")

# Templates
templates = Jinja2Templates(directory="templates")

# Storage
storage = SQLiteStorage()
log_manager = LogManager()
simulation_manager = SimulationManager(storage)

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
    """Son 30 dakikalık gram altın fiyat verisi"""
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=30)  # 30 dakika geriye git
    
    prices = storage.get_price_range(start_time, end_time)
    
    return {
        "prices": [
            {
                "timestamp": p.timestamp.isoformat(),
                "ons_usd": float(p.ons_usd),
                "usd_try": float(p.usd_try),
                "ons_try": float(p.ons_try),
                "gram_altin": float(p.gram_altin) if p.gram_altin else float(p.ons_try / 31.1035)
            }
            for p in prices  # Tüm 30 dakikalık veriyi al
        ]
    }


@app.get("/api/gram-candles/{interval}")
async def get_gram_candles(interval: str):
    """Gram altın OHLC mum verileri"""
    interval_map = {
        "15m": 15,
        "1h": 60,
        "4h": 240,
        "1d": 1440
    }
    
    minutes = interval_map.get(interval, 60)
    candles = storage.generate_gram_candles(minutes, 100)
    
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
async def get_recent_logs(category: str = "all", lines: int = 50):
    """Kategoriye göre log satırları"""
    log_categories = {
        "analyzer": "logs/gold_analyzer.log",
        "web": "logs/gold_analyzer_web.log",
        "errors": "logs/gold_analyzer_errors.log",
        "critical": "logs/gold_analyzer_critical.log"
    }
    
    result = {}
    
    if category == "all":
        # Tüm kategorileri getir
        for cat, path in log_categories.items():
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        file_lines = f.readlines()
                        result[cat] = [
                            parse_log_line(line.strip()) 
                            for line in file_lines[-lines:]
                        ]
                except Exception as e:
                    logger.error(f"Error reading {path}: {e}")
                    result[cat] = []
            else:
                result[cat] = []
    else:
        # Sadece belirtilen kategori
        if category in log_categories:
            path = log_categories[category]
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        file_lines = f.readlines()
                        result[category] = [
                            parse_log_line(line.strip()) 
                            for line in file_lines[-lines:]
                        ]
                except Exception as e:
                    logger.error(f"Error reading {path}: {e}")
                    result[category] = []
            else:
                result[category] = []
    
    return result


def parse_log_line(line: str) -> Dict[str, str]:
    """Log satırını parse et"""
    # Format: 2024-01-17 15:30:45 - module - LEVEL - message
    parts = line.split(' - ', 3)
    
    if len(parts) >= 4:
        return {
            "timestamp": parts[0],
            "module": parts[1],
            "level": parts[2],
            "message": parts[3],
            "raw": line
        }
    else:
        return {
            "timestamp": "",
            "module": "",
            "level": "INFO",
            "message": line,
            "raw": line
        }


@app.get("/menu")
async def get_menu(request: Request):
    """Menu component'i döndür"""
    return templates.TemplateResponse("menu.html", {"request": request})


@app.get("/analysis")
async def analysis_page(request: Request):
    """Analiz sayfası"""
    return templates.TemplateResponse("analysis.html", {"request": request})


@app.get("/signals")
async def signals_page(request: Request):
    """Sinyaller sayfası"""
    return templates.TemplateResponse("signals.html", {"request": request})


@app.get("/logs")
async def logs_page(request: Request):
    """Log görüntüleme sayfası"""
    return templates.TemplateResponse("logs.html", {"request": request})


@app.get("/simulations")
async def simulations_page(request: Request):
    """Simülasyon sayfası"""
    return templates.TemplateResponse("simulations.html", {"request": request})


@app.get("/api/analysis/config")
async def get_analysis_config():
    """Analiz konfigürasyonunu döndür"""
    return {
        "collection_interval": settings.collection_interval,
        "analysis_interval_15m": settings.analysis_interval_15m,
        "analysis_interval_1h": settings.analysis_interval_1h,
        "analysis_interval_4h": settings.analysis_interval_4h,
        "analysis_interval_daily": settings.analysis_interval_daily,
        "support_resistance_lookback": settings.support_resistance_lookback,
        "rsi_period": settings.rsi_period,
        "ma_short_period": settings.ma_short_period,
        "ma_long_period": settings.ma_long_period,
        "min_confidence_score": settings.min_confidence_score,
        "risk_tolerance": settings.risk_tolerance
    }


@app.get("/api/logs/stats")
async def get_log_stats():
    """Log istatistiklerini döndür"""
    try:
        stats = log_manager.get_log_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting log stats: {e}")
        return {"error": str(e)}


@app.get("/api/logs/recent-errors")
async def get_recent_errors(count: int = 10):
    """Son hataları döndür"""
    try:
        errors = log_manager.get_recent_errors(count)
        return {"errors": errors, "count": len(errors)}
    except Exception as e:
        logger.error(f"Error getting recent errors: {e}")
        return {"error": str(e)}


@app.get("/api/simulations/list")
async def get_simulations():
    """Tüm simülasyonları listele"""
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, strategy_type, status, current_capital, 
                       total_profit_loss, total_profit_loss_pct, win_rate,
                       total_trades, winning_trades, losing_trades,
                       created_at
                FROM simulations
                ORDER BY id
            """)
            
            simulations = []
            
            # Güncel fiyatı al
            current_price = None
            latest = storage.get_latest_price()
            if latest and latest.gram_altin:
                current_price = float(latest.gram_altin)
            
            for row in cursor.fetchall():
                total_pnl_tl = row[5]
                total_pnl_gram = total_pnl_tl / current_price if current_price else 0
                
                simulations.append({
                    "id": row[0],
                    "name": row[1],
                    "strategy_type": row[2],
                    "status": row[3],
                    "current_capital": row[4],
                    "total_profit_loss": total_pnl_tl,
                    "total_profit_loss_gram": total_pnl_gram,
                    "total_profit_loss_pct": row[6],
                    "win_rate": row[7],
                    "total_trades": row[8],
                    "winning_trades": row[9],
                    "losing_trades": row[10],
                    "created_at": row[11]
                })
            
            return {"simulations": simulations, "current_price": current_price}
    except Exception as e:
        logger.error(f"Error getting simulations: {e}")
        return {"error": str(e)}


@app.get("/api/simulations/{sim_id}/positions")
async def get_simulation_positions(sim_id: int, status: str = "all"):
    """Simülasyon pozisyonlarını getir"""
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            if status == "all":
                query = """
                    SELECT * FROM sim_positions 
                    WHERE simulation_id = ?
                    ORDER BY entry_time DESC
                    LIMIT 50
                """
                params = (sim_id,)
            else:
                query = """
                    SELECT * FROM sim_positions 
                    WHERE simulation_id = ? AND status = ?
                    ORDER BY entry_time DESC
                    LIMIT 50
                """
                params = (sim_id, status.upper())
            
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            
            positions = []
            
            # Anlık fiyatı al
            current_price = None
            latest = storage.get_latest_price()
            if latest and latest.gram_altin:
                current_price = float(latest.gram_altin)
            
            for row in cursor.fetchall():
                pos = dict(zip(columns, row))
                
                # Açık pozisyonlar için anlık kar/zarar hesapla
                if pos['status'] == 'OPEN' and current_price:
                    entry_price = float(pos['entry_price'])
                    position_size = float(pos['position_size'])
                    
                    if pos['position_type'] == 'LONG':
                        pnl_tl = (current_price - entry_price) * position_size
                    else:
                        pnl_tl = (entry_price - current_price) * position_size
                    
                    # Maliyetleri çıkar
                    total_costs = float(pos['entry_spread']) + float(pos['entry_commission'])
                    pnl_tl -= total_costs
                    
                    # Gram cinsinden kar/zarar
                    pnl_gram = pnl_tl / current_price
                    
                    pos['current_price'] = current_price
                    pos['current_pnl_tl'] = pnl_tl
                    pos['current_pnl_gram'] = pnl_gram
                    pos['current_pnl_pct'] = (pnl_tl / float(pos['allocated_capital'])) * 100
                
                # Kapalı pozisyonlar için gram cinsinden kar/zarar ekle
                elif pos['status'] == 'CLOSED' and pos.get('net_profit_loss'):
                    # TL cinsinden kar/zarar zaten var
                    # Çıkış fiyatını kullanarak gram'a çevir
                    exit_price = float(pos.get('exit_price', entry_price))
                    pos['net_profit_loss_gram'] = float(pos['net_profit_loss']) / exit_price
                
                positions.append(pos)
            
            return {"positions": positions, "current_price": current_price}
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return {"error": str(e)}


@app.get("/api/simulations/{sim_id}/performance")
async def get_simulation_performance(sim_id: int, days: int = 30):
    """Simülasyon performans grafiği verisi"""
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Son N günlük performans
            cursor.execute("""
                SELECT date, starting_capital, ending_capital, daily_pnl, daily_pnl_pct,
                       total_trades, winning_trades, losing_trades
                FROM sim_daily_performance
                WHERE simulation_id = ?
                ORDER BY date DESC
                LIMIT ?
            """, (sim_id, days))
            
            performance = []
            for row in cursor.fetchall():
                performance.append({
                    "date": row[0],
                    "starting_capital": row[1],
                    "ending_capital": row[2],
                    "daily_pnl": row[3],
                    "daily_pnl_pct": row[4],
                    "total_trades": row[5],
                    "winning_trades": row[6],
                    "losing_trades": row[7]
                })
            
            # Sırayı düzelt (eskiden yeniye)
            performance.reverse()
            
            return {"performance": performance}
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        return {"error": str(e)}


@app.get("/api/simulations/{sim_id}/summary")
async def get_simulation_summary(sim_id: int):
    """Simülasyon özeti"""
    try:
        summary = await simulation_manager.get_simulation_status(sim_id)
        if summary:
            return summary.dict()
        return {"error": "Simulation not found"}
    except Exception as e:
        logger.error(f"Error getting simulation summary: {e}")
        return {"error": str(e)}


@app.get("/api/analysis/history")
async def get_analysis_history(timeframe: str = None):
    """Son hibrit analiz sonuçlarını döndür"""
    try:
        # Hibrit analiz verilerini al
        analyses = storage.get_hybrid_analysis_history(limit=20, timeframe=timeframe)
        
        # API formatına dönüştür
        formatted_analyses = []
        for analysis in analyses:
            # Details kontrolü
            gram_details = analysis.get("details", {}).get("gram", {})
            global_details = analysis.get("details", {}).get("global", {})
            currency_details = analysis.get("details", {}).get("currency", {})
            
            # Yeni göstergeler için veri hazırlığı
            advanced_indicators = analysis.get("advanced_indicators", {})
            pattern_analysis = analysis.get("pattern_analysis", {})
            position_details = analysis.get("position_details", {})
            
            formatted_analyses.append({
                "timestamp": analysis["timestamp"].isoformat(),
                "timeframe": analysis["timeframe"],
                "price": float(analysis["gram_price"]),
                "signal": analysis["signal"],
                "signal_strength": analysis["signal_strength"],
                "confidence": analysis["confidence"],
                "position_size": analysis.get("position_size", 0) if isinstance(analysis.get("position_size"), (int, float)) else analysis.get("position_details", {}).get("lots", 0),
                "stop_loss": float(analysis["stop_loss"]) if analysis["stop_loss"] else None,
                "take_profit": float(analysis["take_profit"]) if analysis["take_profit"] else None,
                "risk_reward_ratio": analysis["risk_reward_ratio"],
                "global_trend": analysis["global_trend"]["direction"],
                "global_trend_strength": analysis["global_trend"]["strength"],
                "currency_risk": analysis["currency_risk"]["level"],
                "recommendations": analysis["recommendations"],
                "summary": analysis["summary"],
                "details": {
                    "gram": {
                        "trend": gram_details.get("trend", "NEUTRAL"),
                        "rsi": gram_details.get("indicators", {}).get("rsi"),
                        "signal": gram_details.get("signal", "HOLD"),
                        "stop_loss": float(gram_details.get("stop_loss")) if gram_details.get("stop_loss") else None,
                        "take_profit": float(gram_details.get("take_profit")) if gram_details.get("take_profit") else None
                    },
                    "global": {
                        "trend_direction": global_details.get("trend_direction", "NEUTRAL"),
                        "trend_strength": global_details.get("trend_strength", "WEAK"),
                        "momentum": {
                            "signal": global_details.get("momentum", {}).get("signal", "-")
                        },
                        "volatility": {
                            "level": global_details.get("volatility", {}).get("level", "-")
                        },
                        "supportive": global_details.get("supportive_of_signal", False)
                    },
                    "currency": {
                        "risk_level": currency_details.get("risk_level", "MEDIUM"),
                        "volatility": {
                            "level": currency_details.get("volatility", {}).get("level", "-")
                        },
                        "position_size_multiplier": currency_details.get("position_size_multiplier", 1.0),
                        "intervention_risk": {
                            "has_risk": currency_details.get("intervention_risk", {}).get("has_risk", False)
                        },
                        "trend_alignment": currency_details.get("trend_alignment", False)
                    },
                    "advanced_indicators": {
                        "cci": advanced_indicators.get("cci", {}).get("value", None),
                        "cci_signal": advanced_indicators.get("cci", {}).get("signal", "NEUTRAL"),
                        "mfi": advanced_indicators.get("mfi", {}).get("value", None),
                        "mfi_signal": advanced_indicators.get("mfi", {}).get("signal", "NEUTRAL"),
                        "combined_signal": advanced_indicators.get("combined_signal", "NEUTRAL"),
                        "divergence": advanced_indicators.get("divergence", False)
                    },
                    "pattern": {
                        "found": pattern_analysis.get("pattern_found", False),
                        "name": pattern_analysis.get("best_pattern", {}).get("pattern", "None"),
                        "signal": pattern_analysis.get("signal", "NEUTRAL"),
                        "confidence": pattern_analysis.get("confidence", 0)
                    }
                },
                "position_details": position_details
            })
        
        return {"analyses": formatted_analyses}
        
    except Exception as e:
        logger.error(f"Error getting hybrid analysis history: {e}")
        # Hata durumunda boş liste dön
        return {"analyses": []}


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


@app.get("/api/debug/analysis-timeframes")
async def debug_analysis_timeframes():
    """Analiz timeframe değerlerini debug et"""
    with storage.get_connection() as conn:
        cursor = conn.cursor()
        
        # Tüm unique timeframe değerlerini al
        cursor.execute("""
            SELECT DISTINCT timeframe, COUNT(*) as count 
            FROM analysis_results 
            GROUP BY timeframe
        """)
        
        timeframe_counts = {}
        for row in cursor.fetchall():
            timeframe_counts[row[0] if row[0] else "NULL"] = row[1]
        
        # Son 10 analizi timeframe ile birlikte al
        cursor.execute("""
            SELECT id, timestamp, timeframe, price 
            FROM analysis_results 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        recent_analyses = []
        for row in cursor.fetchall():
            recent_analyses.append({
                "id": row[0],
                "timestamp": row[1],
                "timeframe": row[2],
                "price": row[3]
            })
        
        return {
            "timeframe_counts": timeframe_counts,
            "recent_analyses": recent_analyses
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
                        "ons_try": float(latest_price.ons_try),
                        "gram_altin": float(latest_price.gram_altin) if latest_price.gram_altin else None
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)