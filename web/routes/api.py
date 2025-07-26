"""
Genel API endpoint'leri
"""
from fastapi import APIRouter
from datetime import timedelta
import os
import logging
import json
from typing import Dict, List, Any

from storage.sqlite_storage import SQLiteStorage
from utils import timezone
from utils.log_manager import LogManager
from web.utils import cache, stats
from web.utils.formatters import parse_log_line

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

# Storage instances
storage = SQLiteStorage()
log_manager = LogManager()

@router.get("/stats")
async def get_stats():
    """Sistem istatistikleri"""
    cached = cache.get("stats")
    if cached:
        return cached
    
    db_stats = storage.get_statistics()
    
    # Uptime hesapla
    uptime = stats.get_uptime()
    
    # Bugünkü sinyalleri say - veritabanından
    today_signals = 0
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            today_start = timezone.get_day_start()
            cursor.execute("""
                SELECT COUNT(*) FROM hybrid_analysis 
                WHERE timestamp >= ? AND signal IN ('BUY', 'SELL')
            """, (today_start,))
            result = cursor.fetchone()
            today_signals = result[0] if result else 0
    except Exception as e:
        logger.error(f"Bugünkü sinyal sayısı alma hatası: {str(e)}")
        today_signals = 0
    
    result = {
        "system": {
            "uptime": uptime,
            "last_update": stats.get("last_price_update"),
            "active_connections": stats.get("active_connections"),
            "errors_today": stats.get("errors_today")
        },
        "database": {
            "total_records": db_stats.get("total_records", 0),
            "oldest_record": db_stats.get("oldest_record"),
            "newest_record": db_stats.get("newest_record"),
            "average_price": db_stats.get("average_price")
        },
        "signals": {
            "today": today_signals,
            "total": stats.get("total_signals")
        }
    }
    
    cache.set("stats", result)
    return result

@router.get("/prices/latest")
async def get_latest_prices():
    """Son 30 dakikalık gram altın fiyat verisi"""
    # 30 dakika = 1800 saniye, 5 saniyede bir kayıt = 360 kayıt + biraz buffer
    latest_prices = storage.get_latest_prices(400)  # 360 + 40 buffer
    
    # Son 30 dakikalık olanları filtrele
    if latest_prices:
        end_time = timezone.now()
        start_time = end_time - timedelta(minutes=30)
        prices = [p for p in latest_prices if p.timestamp >= start_time]
    else:
        prices = []
    
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

@router.get("/prices/current")
async def get_current_price():
    """Anlık gram altın fiyatı - Cache kullanılmaz, her zaman fresh data"""
    latest = storage.get_latest_price()
    if latest:
        return {
            "timestamp": latest.timestamp.isoformat(),
            "ons_usd": float(latest.ons_usd),
            "usd_try": float(latest.usd_try),
            "ons_try": float(latest.ons_try),
            "gram_altin": float(latest.gram_altin) if latest.gram_altin else float(latest.ons_try / 31.1035)
        }
    return {"error": "No price data available"}

@router.get("/gram-candles/{interval}")
async def get_gram_candles(interval: str):
    """Gram altın OHLC mum verileri"""
    cache_key = f"gram_candles_{interval}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    interval_map = {
        "15m": 15,
        "1h": 60,
        "4h": 240,
        "1d": 1440
    }
    
    minutes = interval_map.get(interval, 60)
    candles = storage.generate_gram_candles(minutes, 100)
    
    result = {
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
    
    cache.set(cache_key, result)
    return result

@router.get("/candles/{interval}")
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

@router.get("/signals/recent")
async def get_recent_signals():
    """Son 24 saatteki sinyalleri veritabanından al"""
    cached = cache.get("signals_recent")
    if cached:
        return cached
    
    try:
        # Son 24 saatteki hybrid analizleri al
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Son 24 saatteki analizleri al
            yesterday = timezone.now() - timedelta(hours=24)
            
            cursor.execute("""
                SELECT 
                    timestamp,
                    timeframe,
                    signal,
                    confidence,
                    gram_price,
                    stop_loss,
                    take_profit,
                    position_size,
                    risk_reward_ratio
                FROM hybrid_analysis
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 100
            """, (yesterday,))
            
            signals = []
            for row in cursor.fetchall():
                timestamp, timeframe, signal, confidence, gram_price, stop_loss, take_profit, position_size, risk_reward = row
                
                # Sadece BUY/SELL sinyallerini al (HOLD hariç)
                if signal in ['BUY', 'SELL']:
                    signals.append({
                        'timestamp': timestamp,
                        'timeframe': timeframe,
                        'signal': signal,
                        'confidence': confidence,
                        'gram_price': gram_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'position_size': position_size,
                        'risk_reward': risk_reward
                    })
            
            result = {
                'status': 'success',
                'signals': signals,
                'count': len(signals)
            }
            
            cache.set("signals_recent", result)
            return result
            
    except Exception as e:
        logger.error(f"Sinyal alma hatası: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'signals': []
        }

@router.get("/signals/today")
async def get_today_signals():
    """Bugünkü sinyalleri al (eski API uyumluluğu için)"""
    # Yeni API'yi çağır ve formatı dönüştür
    result = await get_recent_signals()
    
    if result['status'] == 'success':
        # Eski format için dönüşüm
        signals = []
        for s in result['signals']:
            signals.append({
                'type': s['signal'],
                'price': str(s['gram_price']),
                'confidence': str(s['confidence']),
                'target': str(s['take_profit']) if s['take_profit'] else '-',
                'stop_loss': str(s['stop_loss']) if s['stop_loss'] else '-',
                'timestamp': s['timestamp']
            })
        return {"signals": signals}
    
    return {"signals": []}

@router.get("/logs/recent")
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

@router.get("/logs/stats")
async def get_log_stats():
    """Log istatistiklerini döndür"""
    try:
        stats = log_manager.get_log_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting log stats: {e}")
        return {"error": str(e)}

@router.get("/logs/recent-errors")
async def get_recent_errors(count: int = 10):
    """Son hataları döndür"""
    try:
        errors = log_manager.get_recent_errors(count)
        return {"errors": errors, "count": len(errors)}
    except Exception as e:
        logger.error(f"Error getting recent errors: {e}")
        return {"error": str(e)}

@router.get("/debug/candles")
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

@router.get("/debug/analysis-timeframes")
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


@router.get("/performance/metrics")
async def get_performance_metrics():
    """Performans metrikleri"""
    cached = cache.get("performance_metrics")
    if cached:
        return cached
    
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Son 24 saatlik değişim
            now = timezone.now()
            yesterday = now - timedelta(hours=24)
            
            cursor.execute("""
                SELECT gram_altin FROM price_data 
                WHERE timestamp >= ? 
                ORDER BY timestamp ASC 
                LIMIT 1
            """, (yesterday,))
            
            yesterday_price = cursor.fetchone()
            latest_price = storage.get_latest_price()
            
            daily_change = 0
            daily_change_pct = 0
            
            if yesterday_price and latest_price and latest_price.gram_altin:
                old_price = float(yesterday_price[0]) if yesterday_price[0] else 0
                new_price = float(latest_price.gram_altin)
                if old_price > 0:
                    daily_change = new_price - old_price
                    daily_change_pct = (daily_change / old_price) * 100
            
            # Haftalık ortalama
            week_ago = now - timedelta(days=7)
            cursor.execute("""
                SELECT AVG(gram_altin) as avg_price, 
                       MIN(gram_altin) as min_price,
                       MAX(gram_altin) as max_price,
                       COUNT(*) as data_points
                FROM price_data 
                WHERE timestamp >= ? AND gram_altin IS NOT NULL
            """, (week_ago,))
            
            weekly_stats = cursor.fetchone()
            weekly_avg = float(weekly_stats[0]) if weekly_stats and weekly_stats[0] else 0
            
            # Volatilite hesapla
            volatility = 0
            if weekly_stats and weekly_stats[1] and weekly_stats[2]:
                min_price = float(weekly_stats[1])
                max_price = float(weekly_stats[2])
                if weekly_avg > 0:
                    volatility = ((max_price - min_price) / weekly_avg) * 100
            
            # Sinyal başarı oranı
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN signal IN ('BUY', 'SELL') THEN 1 ELSE 0 END) as actionable_signals
                FROM hybrid_analysis 
                WHERE timestamp >= ?
            """, (week_ago,))
            
            signal_stats = cursor.fetchone()
            total_signals = signal_stats[0] if signal_stats else 0
            actionable_signals = signal_stats[1] if signal_stats else 0
            
            # Trend hesapla
            trend = "Yatay"
            if daily_change_pct > 1:
                trend = "Yükseliş"
            elif daily_change_pct < -1:
                trend = "Düşüş"
            
            volatility_level = "Düşük"
            if volatility > 5:
                volatility_level = "Yüksek"
            elif volatility > 2:
                volatility_level = "Orta"
            
            result = {
                "daily": {
                    "change": daily_change,
                    "change_pct": daily_change_pct,
                    "current_price": float(latest_price.gram_altin) if latest_price and latest_price.gram_altin else 0
                },
                "weekly": {
                    "average": weekly_avg,
                    "trend": trend,
                    "min": float(weekly_stats[1]) if weekly_stats and weekly_stats[1] else 0,
                    "max": float(weekly_stats[2]) if weekly_stats and weekly_stats[2] else 0
                },
                "volatility": {
                    "value": volatility,
                    "level": volatility_level
                },
                "signals": {
                    "total": total_signals,
                    "actionable": actionable_signals,
                    "success_rate": (actionable_signals / total_signals * 100) if total_signals > 0 else 0
                }
            }
            
            cache.set("performance_metrics", result)
            return result
            
    except Exception as e:
        logger.error(f"Performans metrikleri hatası: {e}")
        return {
            "daily": {"change": 0, "change_pct": 0, "current_price": 0},
            "weekly": {"average": 0, "trend": "Bilinmiyor", "min": 0, "max": 0},
            "volatility": {"value": 0, "level": "Bilinmiyor"},
            "signals": {"total": 0, "actionable": 0, "success_rate": 0}
        }

@router.get("/market/overview")
async def get_market_overview():
    """Piyasa genel görünümü"""
    try:
        # Son fiyat bilgileri
        latest = storage.get_latest_price()
        if not latest:
            return {"error": "Fiyat verisi bulunamadı"}
        
        # Son 1 saatlik değişim
        hour_ago = timezone.now() - timedelta(hours=1)
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gram_altin, ons_usd, usd_try 
                FROM price_data 
                WHERE timestamp >= ? 
                ORDER BY timestamp ASC 
                LIMIT 1
            """, (hour_ago,))
            
            hour_old = cursor.fetchone()
        
        # Değişim hesapla
        changes = {}
        if hour_old:
            if hour_old[0] and latest.gram_altin:
                gram_change = float(latest.gram_altin) - float(hour_old[0])
                gram_change_pct = (gram_change / float(hour_old[0])) * 100
                changes["gram_altin"] = {
                    "value": float(latest.gram_altin),
                    "change": gram_change,
                    "change_pct": gram_change_pct
                }
            
            if hour_old[1] and latest.ons_usd:
                ons_change = float(latest.ons_usd) - float(hour_old[1])
                ons_change_pct = (ons_change / float(hour_old[1])) * 100
                changes["ons_usd"] = {
                    "value": float(latest.ons_usd),
                    "change": ons_change,
                    "change_pct": ons_change_pct
                }
            
            if hour_old[2] and latest.usd_try:
                usd_change = float(latest.usd_try) - float(hour_old[2])
                usd_change_pct = (usd_change / float(hour_old[2])) * 100
                changes["usd_try"] = {
                    "value": float(latest.usd_try),
                    "change": usd_change,
                    "change_pct": usd_change_pct
                }
        
        # Son analizden trend bilgisi
        analyses = storage.get_hybrid_analysis_history(limit=1)
        trend_info = {}
        if analyses:
            analysis = analyses[0]
            trend_info = {
                "signal": analysis.get("signal"),
                "confidence": analysis.get("confidence"),
                "global_trend": analysis.get("global_trend", {}).get("direction"),
                "currency_risk": analysis.get("currency_risk", {}).get("level")
            }
        
        return {
            "timestamp": latest.timestamp.isoformat(),
            "prices": changes,
            "analysis": trend_info,
            "last_update": timezone.format_for_display(latest.timestamp)
        }
        
    except Exception as e:
        logger.error(f"Market overview hatası: {e}")
        return {"error": str(e)}

@router.get("/alerts/active")
async def get_active_alerts():
    """Aktif uyarıları getir (önemli seviyeler yaklaşıldığında)"""
    try:
        alerts = []
        latest = storage.get_latest_price()
        
        if not latest or not latest.gram_altin:
            return {"alerts": []}
        
        current_price = float(latest.gram_altin)
        
        # Son 24 saatlik min/max
        yesterday = timezone.now() - timedelta(hours=24)
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MIN(gram_altin) as min_price, MAX(gram_altin) as max_price
                FROM price_data
                WHERE timestamp >= ? AND gram_altin IS NOT NULL
            """, (yesterday,))
            
            result = cursor.fetchone()
            if result and result[0] and result[1]:
                min_24h = float(result[0])
                max_24h = float(result[1])
                
                # Minimum seviyeye yaklaşma
                if current_price <= min_24h * 1.01:  # %1 yakınlık
                    alerts.append({
                        "type": "SUPPORT_NEAR",
                        "level": min_24h,
                        "message": f"24 saatlik minimum seviyeye yaklaşılıyor: ₺{min_24h:.2f}",
                        "severity": "HIGH",
                        "timestamp": timezone.now().isoformat()
                    })
                
                # Maksimum seviyeye yaklaşma
                if current_price >= max_24h * 0.99:  # %1 yakınlık
                    alerts.append({
                        "type": "RESISTANCE_NEAR",
                        "level": max_24h,
                        "message": f"24 saatlik maksimum seviyeye yaklaşılıyor: ₺{max_24h:.2f}",
                        "severity": "HIGH",
                        "timestamp": timezone.now().isoformat()
                    })
            
            # Son 1 saatte hızlı değişim
            hour_ago = timezone.now() - timedelta(hours=1)
            cursor.execute("""
                SELECT gram_altin FROM price_data
                WHERE timestamp >= ? AND gram_altin IS NOT NULL
                ORDER BY timestamp ASC LIMIT 1
            """, (hour_ago,))
            
            hour_old = cursor.fetchone()
            if hour_old and hour_old[0]:
                hour_old_price = float(hour_old[0])
                change_pct = ((current_price - hour_old_price) / hour_old_price) * 100
                
                if abs(change_pct) >= 2:  # %2'den fazla değişim
                    direction = "yükseliş" if change_pct > 0 else "düşüş"
                    alerts.append({
                        "type": "RAPID_CHANGE",
                        "change_pct": change_pct,
                        "message": f"Son 1 saatte hızlı {direction}: %{abs(change_pct):.1f}",
                        "severity": "MEDIUM",
                        "timestamp": timezone.now().isoformat()
                    })
        
        return {"alerts": alerts, "count": len(alerts)}
        
    except Exception as e:
        logger.error(f"Alert hatası: {e}")
        return {"alerts": [], "error": str(e)}

@router.get("/analysis/indicators/{timeframe}")
async def get_analysis_indicators(timeframe: str):
    """Belirli bir timeframe için detaylı teknik göstergeler"""
    cache_key = f"indicators_{timeframe}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # Son analizi al
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gram_analysis, global_trend_analysis, currency_risk_analysis, advanced_indicators
                FROM hybrid_analysis
                WHERE timeframe = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (timeframe,))
            
            result = cursor.fetchone()
            if not result:
                return {"error": "Analiz bulunamadı"}
            
            gram_analysis = json.loads(result[0]) if result[0] else {}
            global_analysis = json.loads(result[1]) if result[1] else {}
            currency_analysis = json.loads(result[2]) if result[2] else {}
            advanced = json.loads(result[3]) if result[3] else {}
            
            indicators = {
                "timeframe": timeframe,
                "gram_indicators": gram_analysis.get("indicators", {}),
                "global_indicators": global_analysis,
                "currency_indicators": currency_analysis,
                "advanced_indicators": advanced,
                "timestamp": timezone.now().isoformat()
            }
            
            cache.set(cache_key, indicators)
            return indicators
            
    except Exception as e:
        logger.error(f"Indicator analiz hatası: {e}")
        return {"error": str(e)}

@router.get("/analysis/patterns/active")
async def get_active_patterns():
    """Aktif chart pattern'leri getir"""
    try:
        patterns = []
        
        # Her timeframe için son pattern'leri al
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            for timeframe in ["15m", "1h", "4h", "1d"]:
                cursor.execute("""
                    SELECT gram_analysis, timestamp
                    FROM hybrid_analysis
                    WHERE timeframe = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (timeframe,))
                
                result = cursor.fetchone()
                if result and result[0]:
                    gram_analysis = json.loads(result[0])
                    if gram_analysis.get("patterns"):
                        for pattern in gram_analysis["patterns"]:
                            patterns.append({
                                "timeframe": timeframe,
                                "name": pattern.get("name"),
                                "type": pattern.get("type"),
                                "confidence": pattern.get("confidence"),
                                "target": pattern.get("target"),
                                "timestamp": result[1]
                            })
        
        # Güven skoruna göre sırala
        patterns.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return {
            "patterns": patterns[:10],  # En güvenilir 10 pattern
            "count": len(patterns)
        }
        
    except Exception as e:
        logger.error(f"Pattern analiz hatası: {e}")
        return {"patterns": [], "error": str(e)}