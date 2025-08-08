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
from indicators.market_regime import calculate_market_regime_analysis

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

# Storage instances
storage = SQLiteStorage()
log_manager = LogManager()

@router.get("/dashboard")
async def get_dashboard_data():
    """Dashboard için tüm verileri tek seferde getir - Ultra Optimized"""
    cache_key = "dashboard_data_v2"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # Single connection for all queries - Connection pooling optimization
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Optimized: Single query for all dashboard data
            latest_price = storage.get_latest_price()
            if not latest_price:
                return {"error": "No price data available"}
            
            # Batched queries for better performance
            today_start = timezone.get_day_start()
            
            # Single query to get all dashboard metrics
            cursor.execute("""
                WITH dashboard_metrics AS (
                    SELECT 
                        COUNT(CASE WHEN signal IN ('BUY', 'SELL') AND timestamp >= ? THEN 1 END) as today_signals,
                        COUNT(*) as total_records
                    FROM hybrid_analysis
                ),
                recent_signals AS (
                    SELECT timestamp, timeframe, signal, confidence, gram_price
                    FROM hybrid_analysis
                    WHERE signal IN ('BUY', 'SELL')
                    ORDER BY timestamp DESC
                    LIMIT 5
                ),
                performance_data AS (
                    SELECT 
                        COUNT(*) as daily_trades,
                        SUM(CASE WHEN net_profit_loss > 0 THEN 1 ELSE 0 END) as daily_wins
                    FROM sim_positions
                    WHERE status = 'CLOSED' AND exit_time >= ?
                )
                SELECT 
                    dm.today_signals,
                    dm.total_records,
                    pd.daily_trades,
                    pd.daily_wins
                FROM dashboard_metrics dm, performance_data pd
            """, (today_start, timezone.now() - timedelta(hours=24)))
            
            metrics = cursor.fetchone()
            
            # Get recent signals separately for better cache efficiency
            cursor.execute("""
                SELECT timestamp, timeframe, signal, confidence, gram_price
                FROM hybrid_analysis
                WHERE signal IN ('BUY', 'SELL')
                ORDER BY timestamp DESC
                LIMIT 5
            """)
            
            recent_signals = [
                {
                    "timestamp": row[0],
                    "timeframe": row[1], 
                    "signal": row[2],
                    "confidence": float(row[3]),
                    "price": float(row[4])
                }
                for row in cursor.fetchall()
            ]
        
            # Calculate performance metrics from batched query
            daily_trades = metrics[2] if metrics else 0
            daily_wins = metrics[3] if metrics else 0
            performance_summary = {
                "daily_trades": daily_trades,
                "daily_wins": daily_wins,
                "daily_win_rate": (daily_wins / daily_trades * 100) if daily_trades > 0 else 0
            }
        
            # Optimized dashboard data structure
            dashboard_data = {
                "current_price": {
                    "gram_altin": float(latest_price.gram_altin) if latest_price.gram_altin else 0,
                    "ons_usd": float(latest_price.ons_usd),
                    "usd_try": float(latest_price.usd_try),
                    "timestamp": latest_price.timestamp.isoformat()
                },
                "stats": {
                    "total_records": metrics[1] if metrics else 0,
                    "today_signals": metrics[0] if metrics else 0
                },
                "recent_signals": recent_signals,
                "performance": performance_summary,
                "last_update": timezone.now().isoformat()
            }
            
            # Increased cache time for better performance - 60 seconds
            cache.set(cache_key, dashboard_data, ttl=60)
            return dashboard_data
        
    except Exception as e:
        logger.error(f"Dashboard data hatası: {e}")
        return {
            "error": str(e),
            "current_price": {"gram_altin": 0, "ons_usd": 0, "usd_try": 0},
            "stats": {"total_records": 0, "today_signals": 0},
            "recent_signals": [],
            "performance": {"daily_trades": 0, "daily_wins": 0, "daily_win_rate": 0}
        }

@router.get("/stats")
async def get_stats():
    """Sistem istatistikleri - Geriye dönük uyumluluk için"""
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
async def get_latest_prices(limit: int = 60, interval: str = "1m"):
    """
    Son fiyat verilerini getir - Ultra Optimized with Smart Caching
    
    Args:
        limit: Maksimum kayıt sayısı (default: 60, max: 150)
        interval: Veri aralığı ('1m', '5m', '15m') - default: 1m
    """
    # Strict limit control for performance
    limit = min(max(limit, 5), 150)  # Reduced max limit for better performance
    
    # Enhanced cache key with version
    cache_key = f"prices_latest_v2_{limit}_{interval}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Optimized interval processing
    interval_config = {
        "1m": {"multiplier": 1, "filter_seconds": 60},
        "5m": {"multiplier": 5, "filter_seconds": 300},
        "15m": {"multiplier": 10, "filter_seconds": 900}
    }
    
    config = interval_config.get(interval, interval_config["1m"])
    fetch_count = min(limit * config["multiplier"] + 20, 300)  # Reduced fetch size
    
    latest_prices = storage.get_latest_prices(fetch_count)
    
    # Optimized filtering algorithm
    if latest_prices:
        if interval != "1m":
            # Efficient interval filtering with single pass
            filtered_prices = []
            last_time = None
            filter_seconds = config["filter_seconds"]
            
            for p in reversed(latest_prices):
                if last_time is None or (p.timestamp - last_time).total_seconds() >= filter_seconds:
                    filtered_prices.append(p)
                    last_time = p.timestamp
                    if len(filtered_prices) >= limit:
                        break
            
            prices = filtered_prices[::-1]  # Reverse efficiently
        else:
            # Direct slice for 1m interval
            prices = latest_prices[-limit:] if len(latest_prices) >= limit else latest_prices
    else:
        prices = []
    
    # Optimized response structure with minimal data
    result = {
        "prices": [
            {
                "t": p.timestamp.isoformat(),
                "g": float(p.gram_altin) if p.gram_altin else float(p.ons_try / 31.1035),
                "o": float(p.ons_usd),
                "u": float(p.usd_try)
            }
            for p in prices
        ],
        "count": len(prices),
        "interval": interval,
        "cached_at": timezone.now().isoformat()
    }
    
    # Dynamic cache TTL based on interval
    cache_ttl = 60 if interval == "1m" else 180 if interval == "5m" else 300
    cache.set(cache_key, result, ttl=cache_ttl)
    return result

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

@router.get("/prices/daily-range")
async def get_daily_price_range():
    """24 saatlik en yüksek ve en düşük fiyatlar"""
    cached = cache.get("daily_price_range")
    if cached:
        return cached
    
    try:
        # Son 24 saatteki fiyatları al
        yesterday = timezone.now() - timedelta(hours=24)
        
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    MIN(gram_altin) as daily_low,
                    MAX(gram_altin) as daily_high,
                    MIN(ons_usd) as ons_low,
                    MAX(ons_usd) as ons_high,
                    MIN(usd_try) as usd_low,
                    MAX(usd_try) as usd_high
                FROM prices 
                WHERE timestamp >= ?
                AND gram_altin IS NOT NULL
            """, (yesterday,))
            
            result = cursor.fetchone()
            
            if result and result[0] is not None:
                data = {
                    "gram_altin": {
                        "low": float(result[0]),
                        "high": float(result[1])
                    },
                    "ons_usd": {
                        "low": float(result[2]) if result[2] else None,
                        "high": float(result[3]) if result[3] else None
                    },
                    "usd_try": {
                        "low": float(result[4]) if result[4] else None,
                        "high": float(result[5]) if result[5] else None
                    }
                }
                
                cache.set("daily_price_range", data, ttl=300)  # 5 dakika cache
                return data
            else:
                return {"error": "No price data available for the last 24 hours"}
                
    except Exception as e:
        logger.error(f"Daily price range error: {e}")
        return {"error": str(e)}

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
async def get_performance_metrics(period: str = "month", summary_only: bool = False):
    """
    Gerçek trading performans metrikleri - Ultra Optimized Version
    
    Args:
        period: Zaman aralığı ('day', 'week', 'month') - default: 'month'
        summary_only: Sadece özet bilgiler (default: False)
    """
    cache_key = f"performance_metrics_v2_{period}_{summary_only}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Period'a göre zaman aralığı belirle
            now = timezone.now()
            period_map = {
                "day": now - timedelta(hours=24),
                "week": now - timedelta(days=7),
                "month": now - timedelta(days=30)
            }
            
            since_time = period_map.get(period, period_map["month"])
            
            # Güncel fiyat bilgisi
            latest_price = storage.get_latest_price()
            current_price = float(latest_price.gram_altin) if latest_price and latest_price.gram_altin else 0
            
            # Tek sorgu ile temel performans metrikleri
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN net_profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN net_profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(net_profit_loss) as total_pnl,
                    AVG(CASE WHEN net_profit_loss > 0 THEN net_profit_loss ELSE NULL END) as avg_win,
                    AVG(CASE WHEN net_profit_loss < 0 THEN ABS(net_profit_loss) ELSE NULL END) as avg_loss,
                    MAX(net_profit_loss) as best_trade,
                    MIN(net_profit_loss) as worst_trade
                FROM sim_positions
                WHERE status = 'CLOSED' AND exit_time >= ?
            """, (since_time,))
            
            # Açık pozisyonlar
            cursor.execute("""
                SELECT COUNT(*) as open_positions,
                       SUM(allocated_capital) as locked_capital
                FROM sim_positions
                WHERE status = 'OPEN'
            """)
            open_positions = cursor.fetchone()
            
            # Temel metrikleri hesapla
            total_trades = stats[0] or 0
            winning_trades = stats[1] or 0
            losing_trades = stats[2] or 0
            total_pnl = float(stats[3] or 0)
            avg_win = float(stats[4] or 0)
            avg_loss = float(stats[5] or 0)
            best_trade = float(stats[6] or 0)
            worst_trade = float(stats[7] or 0)
            
            # Win rate hesapla
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Profit factor
            profit_factor = (avg_win * winning_trades) / (avg_loss * losing_trades) if losing_trades > 0 and avg_loss > 0 else 0
            
            # Basit result - sadece temel bilgiler
            result = {
                "period": period,
                "current_price": current_price,
                "open_positions": open_positions[0] if open_positions else 0,
                "locked_capital": round(float(open_positions[1] or 0), 2) if open_positions else 0,
                "performance": {
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "win_rate": round(win_rate, 2),
                    "total_pnl": round(total_pnl, 2),
                    "avg_win": round(avg_win, 2),
                    "avg_loss": round(avg_loss, 2),
                    "profit_factor": round(profit_factor, 2),
                    "best_trade": round(best_trade, 2),
                    "worst_trade": round(worst_trade, 2)
                },
                "last_update": timezone.now().isoformat()
            }
            
            # Summary only mode için daha az veri
            if summary_only:
                result = {
                    "period": period,
                    "current_price": current_price,
                    "total_trades": total_trades,
                    "win_rate": round(win_rate, 2),
                    "total_pnl": round(total_pnl, 2),
                    "open_positions": open_positions[0] if open_positions else 0
                }
            
            # 5 dakika cache (period'a göre uzatılabilir)
            cache_ttl = 300 if period != "day" else 120
            cache.set(cache_key, result, ttl=cache_ttl)
            return result
            
    except Exception as e:
        logger.error(f"Performans metrikleri hatası: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "error": str(e),
            "overview": {"current_price": 0, "open_positions": 0, "locked_capital": 0, "trend": "unknown"},
            "performance": {
                "daily": {"trades": 0, "wins": 0, "win_rate": 0, "pnl": 0},
                "weekly": {"trades": 0, "wins": 0, "win_rate": 0, "pnl": 0},
                "monthly": {"trades": 0, "wins": 0, "win_rate": 0, "pnl": 0}
            },
            "timeframes": {},
            "best_timeframe": {"name": "N/A", "stats": {}}
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
        
        # Günlük en yüksek/en düşük
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MIN(gram_altin), MAX(gram_altin)
                FROM price_data
                WHERE timestamp >= ?
            """, (today_start,))
            daily_range = cursor.fetchone()
        
        daily_range_data = {}
        if daily_range and daily_range[0] and daily_range[1]:
            daily_range_data = {
                "low": float(daily_range[0]),
                "high": float(daily_range[1])
            }
        
        # Fiyatları direkt olarak da ekle (widget için)
        prices_data = {
            "gram_altin": float(latest.gram_altin) if latest.gram_altin else 0,
            "ons_usd": float(latest.ons_usd) if latest.ons_usd else 0,
            "usd_try": float(latest.usd_try) if latest.usd_try else 0
        }
        
        return {
            "timestamp": latest.timestamp.isoformat(),
            "prices": prices_data,
            "changes": changes,
            "analysis": trend_info,
            "daily_range": daily_range_data,
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
                
                # Fiyat aralığını hesapla
                price_range = max_24h - min_24h
                
                # Sadece anlamlı bir aralık varsa uyarı ver
                if price_range > 10:  # En az 10 TL fark olmalı
                    # Minimum seviyeye yaklaşma (alt %2'lik dilimde)
                    support_threshold = min_24h + (price_range * 0.02)
                    if current_price <= support_threshold:
                        alerts.append({
                            "type": "SUPPORT_NEAR",
                            "level": min_24h,
                            "message": f"Destek seviyesine yaklaşıyor: ₺{min_24h:.2f}",
                            "severity": "HIGH",
                            "timestamp": timezone.now().isoformat()
                        })
                    else:
                        # Maksimum seviyeye yaklaşma (üst %2'lik dilimde)
                        resistance_threshold = max_24h - (price_range * 0.02)
                        if current_price >= resistance_threshold:
                            alerts.append({
                                "type": "RESISTANCE_NEAR",
                                "level": max_24h,
                                "message": f"Direnç seviyesine yaklaşıyor: ₺{max_24h:.2f}",
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

@router.get("/prices/daily-open")
async def get_daily_open_price():
    """Günlük açılış fiyatını getir"""
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Bugünün açılış fiyatını al (Türkiye saati ile)
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            cursor.execute("""
                SELECT open, timestamp 
                FROM gram_altin_candles
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
                LIMIT 1
            """, (today_start.isoformat(),))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    "open": float(result[0]),
                    "timestamp": result[1],
                    "date": today_start.strftime("%Y-%m-%d")
                }
            else:
                # Bugün veri yoksa dünün kapanışını al
                yesterday_end = today_start - timedelta(days=1)
                cursor.execute("""
                    SELECT close, timestamp 
                    FROM gram_altin_candles
                    WHERE timestamp < ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (today_start.isoformat(),))
                
                result = cursor.fetchone()
                if result:
                    return {
                        "open": float(result[0]),
                        "timestamp": result[1],
                        "date": today_start.strftime("%Y-%m-%d"),
                        "is_previous_close": True
                    }
                    
            return {"error": "Açılış fiyatı bulunamadı"}
            
    except Exception as e:
        logger.error(f"Günlük açılış fiyatı hatası: {e}")
        return {"error": str(e)}

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

@router.get("/performance/realtime")
async def get_realtime_performance(include_history: bool = False, limit: int = 10):
    """
    Gerçek zamanlı sinyal performansı ve açık pozisyonlar - Optimize edilmiş
    
    Args:
        include_history: Geçmiş işlemleri dahil et (default: False)
        limit: Son kapatılan pozisyon sayısı (default: 10, max: 50)
    """
    # Cache key
    cache_key = f"realtime_performance_{include_history}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
        
    try:
        limit = min(max(limit, 5), 50)  # 5-50 arası limit
        
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            now = timezone.now()
            latest_price = storage.get_latest_price()
            current_price = float(latest_price.gram_altin) if latest_price and latest_price.gram_altin else 0
            
            # Açık pozisyonlar - sadeleştirilmiş
            cursor.execute("""
                SELECT 
                    COUNT(*) as count,
                    SUM(allocated_capital) as total_capital,
                    AVG(CASE 
                        WHEN signal_type = 'BUY' THEN (? - entry_price) / entry_price * 100
                        ELSE (entry_price - ?) / entry_price * 100
                    END) as avg_pnl_pct
                FROM sim_positions
                WHERE status = 'OPEN'
            """, (current_price, current_price))
            
            open_summary = cursor.fetchone()
            
            result = {
                "current_price": current_price,
                "open_positions": {
                    "count": open_summary[0] if open_summary else 0,
                    "total_capital": round(float(open_summary[1] or 0), 2) if open_summary else 0,
                    "avg_pnl_pct": round(float(open_summary[2] or 0), 2) if open_summary else 0
                },
                "last_update": timezone.now().isoformat()
            }
            
            # Include history aktifse son kapatılan pozisyonları ekle
            if include_history:
                cursor.execute("""
                    SELECT 
                        timeframe,
                        signal_type,
                        net_profit_loss,
                        profit_loss_pct,
                        exit_time,
                        exit_reason
                    FROM sim_positions
                    WHERE status = 'CLOSED'
                    ORDER BY exit_time DESC
                    LIMIT ?
                """, (limit,))
                
                recent_closed = []
                for row in cursor.fetchall():
                    tf, signal, pnl, pnl_pct, exit_time, reason = row
                    recent_closed.append({
                        "timeframe": tf,
                        "signal": signal,
                        "pnl": round(float(pnl), 2),
                        "pnl_pct": round(float(pnl_pct), 2),
                        "exit_time": exit_time,
                        "exit_reason": reason,
                        "success": pnl > 0
                    })
                
                result["recent_closed"] = recent_closed
            
            # Cache - 30 saniye (gerçek zamanlı olmalı)
            cache.set(cache_key, result, ttl=30)
            return result
            
    except Exception as e:
        logger.error(f"Realtime performans hatası: {e}")
        return {
            "status": "error", 
            "error": str(e),
            "current_price": 0,
            "open_positions": {"count": 0, "total_capital": 0, "avg_pnl_pct": 0}
        }

@router.get("/market-regime")
async def get_market_regime():
    """Market Regime Detection analizi"""
    cache_key = "market_regime"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # Son 100 adet gram altın OHLC verisini al
        candles = storage.generate_gram_candles(60, 100)  # 1 saatlik mumlar
        
        if not candles or len(candles) < 50:
            return {
                "status": "insufficient_data",
                "message": "Market regime analizi için yetersiz veri",
                "error": "En az 50 mum verisi gerekli"
            }
        
        # DataFrame'e çevir
        import pandas as pd
        df_data = []
        for candle in candles:
            df_data.append({
                "timestamp": candle.timestamp,
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close)
            })
        
        df = pd.DataFrame(df_data)
        df.set_index('timestamp', inplace=True)
        
        # Market regime analizi yap
        regime_analysis = calculate_market_regime_analysis(df)
        
        if regime_analysis.get('status') == 'error':
            return regime_analysis
        
        # Cache'e kaydet (2 dakika)
        cache.set(cache_key, regime_analysis, ttl=120)
        
        return regime_analysis
        
    except Exception as e:
        logger.error(f"Market regime analiz hatası: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e),
            "error_type": "analysis_error"
        }

@router.get("/market-regime/history")
async def get_market_regime_history(hours: int = 24):
    """Market regime geçmişi (saatlik data)"""
    try:
        if hours > 168:  # Max 1 hafta
            hours = 168
            
        regime_history = []
        now = timezone.now()
        
        # Her saat için market regime hesapla (cache olmadan)
        for i in range(hours):
            hour_start = now - timedelta(hours=i+1)
            hour_end = now - timedelta(hours=i)
            
            # O saatteki mumları al
            with storage.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT open, high, low, close, timestamp
                    FROM gram_altin_candles
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp ASC
                """, (hour_start.isoformat(), hour_end.isoformat()))
                
                hour_data = cursor.fetchall()
                
            if len(hour_data) >= 20:  # Minimum veri kontrolü
                try:
                    import pandas as pd
                    df_data = []
                    for row in hour_data:
                        df_data.append({
                            "open": float(row[0]),
                            "high": float(row[1]),
                            "low": float(row[2]),
                            "close": float(row[3]),
                            "timestamp": row[4]
                        })
                    
                    df = pd.DataFrame(df_data)
                    regime_result = calculate_market_regime_analysis(df)
                    
                    if regime_result.get('status') == 'success':
                        regime_history.append({
                            "timestamp": hour_end.isoformat(),
                            "volatility_level": regime_result['volatility_regime']['level'],
                            "trend_type": regime_result['trend_regime']['type'],
                            "momentum_state": regime_result['momentum_regime']['state'],
                            "overall_score": regime_result['overall_assessment']['overall_score'],
                            "risk_level": regime_result['overall_assessment']['risk_level']
                        })
                except Exception as inner_e:
                    logger.warning(f"Saat {i} için regime analizi hatası: {inner_e}")
                    continue
        
        return {
            "status": "success",
            "history": regime_history,
            "count": len(regime_history),
            "period_hours": hours
        }
        
    except Exception as e:
        logger.error(f"Market regime history hatası: {e}")
        return {
            "status": "error",
            "message": str(e),
            "history": []
        }

@router.get("/cache/stats")
async def get_cache_stats():
    """Cache istatistiklerini getir"""
    try:
        stats = cache.get_stats()
        return {
            "status": "success",
            "cache_stats": stats,
            "timestamp": timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Cache stats hatası: {e}")
        return {
            "status": "error",
            "message": str(e),
            "cache_stats": {}
        }

@router.post("/cache/clear")
async def clear_cache(key: str = None):
    """Cache'i temizle"""
    try:
        if key:
            cache.clear(key)
            message = f"Cache key '{key}' temizlendi"
        else:
            cache.clear()
            message = "Tüm cache temizlendi"
            
        return {
            "status": "success",
            "message": message,
            "timestamp": timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Cache clear hatası: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/divergence")
async def get_divergence_analysis():
    """Advanced Divergence Detection analizi"""
    cache_key = "divergence_analysis"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        from indicators.divergence_detector import calculate_divergence_analysis
        import pandas as pd
        
        # Son 200 adet gram altın OHLC verisini al
        candles = storage.generate_gram_candles(60, 200)  # 1 saatlik mumlar
        
        if not candles or len(candles) < 50:
            return {
                "status": "insufficient_data",
                "message": "Divergence analizi için yetersiz veri",
                "error": "En az 50 mum verisi gerekli"
            }
        
        # DataFrame'e çevir
        df_data = []
        for candle in candles:
            df_data.append({
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close)
            })
        
        df = pd.DataFrame(df_data)
        
        # Divergence analizi yap
        divergence_result = calculate_divergence_analysis(df)
        
        if divergence_result.get('status') == 'error':
            return divergence_result
        
        # Veritabanına kaydet (isteğe bağlı)
        try:
            with storage.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO divergence_analysis 
                    (timestamp, analysis_data, overall_signal, signal_strength, confluence_score)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    timezone.now().isoformat(),
                    json.dumps(divergence_result),
                    divergence_result.get('overall_signal', 'NEUTRAL'),
                    divergence_result.get('signal_strength', 0),
                    divergence_result.get('confluence_score', 0)
                ))
                conn.commit()
        except Exception as db_error:
            logger.warning(f"Divergence analizi veritabanına kaydedilemedi: {db_error}")
        
        # Cache'e kaydet (5 dakika)
        cache.set(cache_key, divergence_result, ttl=300)
        
        return divergence_result
        
    except Exception as e:
        logger.error(f"Divergence analiz hatası: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e),
            "error_type": "analysis_error"
        }

@router.get("/divergence/active")
async def get_active_divergences():
    """Aktif divergence'ları getir"""
    try:
        # Ana divergence analizini al
        divergence_result = await get_divergence_analysis()
        
        if divergence_result.get('status') != 'success':
            return divergence_result
        
        # Aktif divergence'ları filtrele
        active_divergences = []
        
        # Regular divergences
        for div in divergence_result.get('regular_divergences', []):
            if not div.get('invalidated', False):
                active_divergences.append({
                    "type": "regular",
                    "direction": "bullish" if "bullish" in div['type'] else "bearish",
                    "indicator": div['indicator'],
                    "strength": div['strength'],
                    "class_rating": div['class_rating'],
                    "success_probability": div['success_probability'],
                    "maturity_score": div.get('maturity_score', 0),
                    "angle_difference": div['angle_difference'],
                    "price_points": div['price_points'],
                    "indicator_points": div['indicator_points']
                })
        
        # Hidden divergences
        for div in divergence_result.get('hidden_divergences', []):
            if not div.get('invalidated', False):
                active_divergences.append({
                    "type": "hidden",
                    "direction": "bullish" if "bullish" in div['type'] else "bearish",
                    "indicator": div['indicator'],
                    "strength": div['strength'],
                    "class_rating": div['class_rating'],
                    "success_probability": div['success_probability'],
                    "maturity_score": div.get('maturity_score', 0),
                    "angle_difference": div['angle_difference'],
                    "price_points": div['price_points'],
                    "indicator_points": div['indicator_points']
                })
        
        # Sınıf ve güçe göre sırala
        active_divergences.sort(key=lambda x: (
            {"A": 3, "B": 2, "C": 1}.get(x['class_rating'], 0),
            x['strength']
        ), reverse=True)
        
        # İstatistikler
        class_counts = {"A": 0, "B": 0, "C": 0}
        direction_counts = {"bullish": 0, "bearish": 0}
        
        for div in active_divergences:
            class_counts[div['class_rating']] += 1
            direction_counts[div['direction']] += 1
        
        return {
            "status": "success",
            "active_divergences": active_divergences,
            "statistics": {
                "total_count": len(active_divergences),
                "class_counts": class_counts,
                "direction_counts": direction_counts,
                "confluence_score": divergence_result.get('confluence_score', 0),
                "dominant_divergence": divergence_result.get('dominant_divergence'),
                "overall_signal": divergence_result.get('overall_signal', 'NEUTRAL'),
                "signal_strength": divergence_result.get('signal_strength', 0)
            },
            "targets": divergence_result.get('next_targets', []),
            "invalidation_levels": divergence_result.get('invalidation_levels', []),
            "timestamp": timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Aktif divergence hatası: {e}")
        return {
            "status": "error",
            "message": str(e),
            "active_divergences": [],
            "statistics": {}
        }

@router.get("/divergence/history")
async def get_divergence_history(hours: int = 24, limit: int = 100):
    """Divergence geçmişi"""
    try:
        if hours > 168:  # Max 1 hafta
            hours = 168
        if limit > 500:  # Max 500 kayıt
            limit = 500
            
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Divergence analiz tablosu varsa oradan al
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='divergence_analysis'
            """)
            
            if cursor.fetchone():
                # Divergence tablosu var
                since_time = timezone.now() - timedelta(hours=hours)
                
                cursor.execute("""
                    SELECT timestamp, analysis_data, overall_signal, 
                           signal_strength, confluence_score
                    FROM divergence_analysis
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (since_time.isoformat(), limit))
                
                history = []
                for row in cursor.fetchall():
                    timestamp, analysis_data, signal, strength, confluence = row
                    
                    try:
                        analysis = json.loads(analysis_data) if analysis_data else {}
                        history.append({
                            "timestamp": timestamp,
                            "overall_signal": signal,
                            "signal_strength": float(strength) if strength else 0,
                            "confluence_score": float(confluence) if confluence else 0,
                            "regular_count": len(analysis.get('regular_divergences', [])),
                            "hidden_count": len(analysis.get('hidden_divergences', [])),
                            "dominant_divergence": analysis.get('dominant_divergence')
                        })
                    except json.JSONDecodeError:
                        continue
                
                return {
                    "status": "success",
                    "history": history,
                    "count": len(history),
                    "period_hours": hours
                }
            else:
                # Divergence tablosu yok, boş döndür
                return {
                    "status": "success",
                    "history": [],
                    "count": 0,
                    "period_hours": hours,
                    "note": "Divergence geçmişi henüz mevcut değil"
                }
                
    except Exception as e:
        logger.error(f"Divergence history hatası: {e}")
        return {
            "status": "error",
            "message": str(e),
            "history": []
        }

@router.get("/divergence/alerts")
async def get_divergence_alerts():
    """Divergence tabanlı uyarılar"""
    try:
        # Aktif divergence'ları al
        active_response = await get_active_divergences()
        
        if active_response.get('status') != 'success':
            return {"alerts": [], "status": "error"}
        
        alerts = []
        active_divergences = active_response['active_divergences']
        statistics = active_response['statistics']
        
        # Class A divergence uyarıları
        class_a_count = statistics['class_counts']['A']
        if class_a_count > 0:
            class_a_divs = [d for d in active_divergences if d['class_rating'] == 'A']
            for div in class_a_divs:
                alerts.append({
                    "type": "CLASS_A_DIVERGENCE",
                    "level": "HIGH",
                    "message": f"Sınıf A {div['direction']} divergence tespit edildi ({div['indicator']})",
                    "recommendation": f"Güçlü {div['direction']} sinyal - Başarı oranı: %{int(div['success_probability']*100)}",
                    "strength": div['strength'],
                    "indicator": div['indicator'],
                    "success_rate": div['success_probability'],
                    "timestamp": timezone.now().isoformat()
                })
        
        # Yüksek confluence uyarıları
        confluence_score = statistics['confluence_score']
        if confluence_score > 70:
            alerts.append({
                "type": "HIGH_CONFLUENCE",
                "level": "HIGH",
                "message": f"Yüksek confluence skoru: {confluence_score:.0f}",
                "recommendation": "Çoklu göstergede aynı yönde divergence - Güvenilirlik yüksek",
                "confluence_score": confluence_score,
                "timestamp": timezone.now().isoformat()
            })
        
        # Güçlü dominant divergence
        dominant = statistics.get('dominant_divergence')
        if dominant and dominant.get('strength', 0) > 80:
            alerts.append({
                "type": "STRONG_DOMINANT",
                "level": "MEDIUM",
                "message": f"Güçlü dominant divergence: {dominant['indicator']} ({dominant['class_rating']})",
                "recommendation": f"Ana divergence sinyali güçlü - Sınıf {dominant['class_rating']}",
                "strength": dominant['strength'],
                "timestamp": timezone.now().isoformat()
            })
        
        # Invalidation yakın uyarıları
        latest_price = storage.get_latest_price()
        if latest_price and latest_price.gram_altin:
            current_price = float(latest_price.gram_altin)
            
            for level in active_response.get('invalidation_levels', []):
                distance_pct = abs(current_price - level) / current_price * 100
                if distance_pct < 1:  # %1'den yakın
                    alerts.append({
                        "type": "INVALIDATION_NEAR",
                        "level": "MEDIUM",
                        "message": f"Geçersizleştirici seviye yakın: ₺{level:.2f}",
                        "recommendation": "Divergence geçersiz olabilir, pozisyonları gözden geçir",
                        "price_level": level,
                        "distance_pct": distance_pct,
                        "timestamp": timezone.now().isoformat()
                    })
        
        # Zayıf maturity uyarıları
        immature_count = len([d for d in active_divergences 
                            if d.get('maturity_score', 0) < 30])
        if immature_count > len(active_divergences) * 0.7:  # %70'den fazlası henüz olgunlaşmamış
            alerts.append({
                "type": "IMMATURE_DIVERGENCES",
                "level": "LOW",
                "message": "Çoğu divergence henüz olgunlaşmamış",
                "recommendation": "Sinyallerin gelişmesini bekle, erken giriş riskli",
                "immature_count": immature_count,
                "total_count": len(active_divergences),
                "timestamp": timezone.now().isoformat()
            })
        
        return {
            "status": "success",
            "alerts": alerts,
            "count": len(alerts),
            "statistics": statistics,
            "timestamp": timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Divergence alerts hatası: {e}")
        return {
            "status": "error", 
            "alerts": [],
            "message": str(e)
        }

@router.get("/fibonacci")
async def get_fibonacci_analysis():
    """Fibonacci Retracement analizi"""
    cache_key = "fibonacci_analysis"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        from indicators.fibonacci_retracement import calculate_fibonacci_analysis
        import pandas as pd
        
        # Son 100 adet gram altın OHLC verisini al
        candles = storage.generate_gram_candles(60, 100)  # 1 saatlik mumlar
        
        if not candles or len(candles) < 20:
            return {
                "status": "insufficient_data",
                "message": "Fibonacci analizi için yetersiz veri",
                "error": "En az 20 mum verisi gerekli"
            }
        
        # DataFrame'e çevir
        df_data = []
        for candle in candles:
            df_data.append({
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close)
            })
        
        df = pd.DataFrame(df_data)
        
        # Fibonacci analizi yap
        fibonacci_result = calculate_fibonacci_analysis(df)
        
        if fibonacci_result.get('status') == 'error':
            return fibonacci_result
        
        # Cache'e kaydet (3 dakika)
        cache.set(cache_key, fibonacci_result, ttl=180)
        
        return fibonacci_result
        
    except Exception as e:
        logger.error(f"Fibonacci analiz hatası: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e),
            "error_type": "analysis_error"
        }

@router.get("/fibonacci/levels")
async def get_fibonacci_levels():
    """Aktif Fibonacci seviyelerini getir"""
    try:
        # Ana Fibonacci analizini al
        fibonacci_result = await get_fibonacci_analysis()
        
        if fibonacci_result.get('status') != 'success':
            return fibonacci_result
        
        levels = fibonacci_result.get('fibonacci_levels', {})
        current_price = fibonacci_result.get('current_price', 0)
        nearest_level = fibonacci_result.get('nearest_level')
        
        # Seviyeleri düzenle ve sırala
        level_list = []
        for level_key, level_data in levels.items():
            level_ratio = float(level_key)
            
            level_list.append({
                "ratio": level_ratio,
                "price": level_data['price'],
                "strength": level_data['strength'],
                "description": level_data['description'],
                "distance_pct": level_data['distance_pct'],
                "is_nearest": nearest_level and abs(level_ratio - nearest_level['level']) < 0.001,
                "level_type": "extension" if level_ratio > 1.0 else "retracement",
                "is_golden_ratio": level_ratio in [0.382, 0.618, 1.618]
            })
        
        # Fiyata göre sırala (yakından uzağa)
        level_list.sort(key=lambda x: x['distance_pct'])
        
        return {
            "status": "success",
            "current_price": current_price,
            "levels": level_list,
            "nearest_level": nearest_level,
            "bounce_potential": fibonacci_result.get('bounce_potential', 0),
            "trend": fibonacci_result.get('trend', 'sideways'),
            "swing_range": fibonacci_result.get('range', 0),
            "timestamp": timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Fibonacci levels hatası: {e}")
        return {
            "status": "error",
            "message": str(e),
            "levels": []
        }

@router.get("/smc")
async def get_smc_analysis():
    """Smart Money Concepts analizi"""
    cache_key = "smc_analysis"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        from indicators.smart_money_concepts import calculate_smc_analysis
        import pandas as pd
        
        # Son 150 adet gram altın OHLC verisini al
        candles = storage.generate_gram_candles(60, 150)  # 1 saatlik mumlar
        
        if not candles or len(candles) < 50:
            return {
                "status": "insufficient_data",
                "message": "SMC analizi için yetersiz veri",
                "error": "En az 50 mum verisi gerekli"
            }
        
        # DataFrame'e çevir
        df_data = []
        for candle in candles:
            df_data.append({
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close)
            })
        
        df = pd.DataFrame(df_data)
        
        # SMC analizi yap
        smc_result = calculate_smc_analysis(df)
        
        if smc_result.get('status') == 'error':
            return smc_result
        
        # Cache'e kaydet (3 dakika)
        cache.set(cache_key, smc_result, ttl=180)
        
        return smc_result
        
    except Exception as e:
        logger.error(f"SMC analiz hatası: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e),
            "error_type": "analysis_error"
        }

@router.get("/smc/order-blocks")
async def get_order_blocks():
    """Aktif Order Block'ları getir"""
    try:
        # Ana SMC analizini al
        smc_result = await get_smc_analysis()
        
        if smc_result.get('status') != 'success':
            return smc_result
        
        order_blocks = smc_result.get('order_blocks', [])
        current_price = smc_result.get('current_price', 0)
        
        # Order block'ları fiyata yakınlığa göre sırala
        for ob in order_blocks:
            ob['distance_from_price'] = abs(current_price - ob['mid_point']) / current_price * 100
            ob['is_near'] = ob['distance_from_price'] < 1.0  # %1'den yakın
        
        order_blocks.sort(key=lambda x: x['distance_from_price'])
        
        # İstatistikler
        bullish_count = len([ob for ob in order_blocks if ob['type'] == 'bullish'])
        bearish_count = len([ob for ob in order_blocks if ob['type'] == 'bearish'])
        touched_count = len([ob for ob in order_blocks if ob['touched']])
        
        return {
            "status": "success",
            "current_price": current_price,
            "order_blocks": order_blocks,
            "statistics": {
                "total_count": len(order_blocks),
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
                "touched_count": touched_count,
                "untouched_count": len(order_blocks) - touched_count
            },
            "timestamp": timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Order blocks hatası: {e}")
        return {
            "status": "error",
            "message": str(e),
            "order_blocks": []
        }

@router.get("/smc/fair-value-gaps")
async def get_fair_value_gaps():
    """Fair Value Gap'leri getir"""
    try:
        # Ana SMC analizini al
        smc_result = await get_smc_analysis()
        
        if smc_result.get('status') != 'success':
            return smc_result
        
        fvg_list = smc_result.get('fair_value_gaps', [])
        current_price = smc_result.get('current_price', 0)
        
        # FVG'leri boyuta göre sırala (büyükten küçüğe)
        for fvg in fvg_list:
            fvg['distance_from_price'] = min(
                abs(current_price - fvg['high']),
                abs(current_price - fvg['low'])
            ) / current_price * 100
            fvg['price_in_gap'] = fvg['low'] <= current_price <= fvg['high']
        
        fvg_list.sort(key=lambda x: x['size_pct'], reverse=True)
        
        # İstatistikler
        bullish_count = len([fvg for fvg in fvg_list if fvg['type'] == 'bullish'])
        bearish_count = len([fvg for fvg in fvg_list if fvg['type'] == 'bearish'])
        filled_count = len([fvg for fvg in fvg_list if fvg['filled']])
        
        return {
            "status": "success",
            "current_price": current_price,
            "fair_value_gaps": fvg_list,
            "statistics": {
                "total_count": len(fvg_list),
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
                "filled_count": filled_count,
                "unfilled_count": len(fvg_list) - filled_count
            },
            "timestamp": timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Fair Value Gaps hatası: {e}")
        return {
            "status": "error",
            "message": str(e),
            "fair_value_gaps": []
        }

@router.get("/smc/market-structure")
async def get_market_structure():
    """Market Structure bilgilerini getir"""
    try:
        # Ana SMC analizini al
        smc_result = await get_smc_analysis()
        
        if smc_result.get('status') != 'success':
            return smc_result
        
        market_structure = smc_result.get('market_structure', {})
        current_price = smc_result.get('current_price', 0)
        
        # BOS/CHoCH seviye kontrolü
        bos_status = None
        choch_status = None
        
        if market_structure.get('bos_level'):
            bos_distance = abs(current_price - market_structure['bos_level']) / current_price * 100
            if market_structure['trend'] == 'bullish':
                bos_status = "risk" if current_price < market_structure['bos_level'] else "safe"
            elif market_structure['trend'] == 'bearish':
                bos_status = "risk" if current_price > market_structure['bos_level'] else "safe"
            else:
                bos_status = "neutral"
        
        if market_structure.get('choch_level'):
            choch_distance = abs(current_price - market_structure['choch_level']) / current_price * 100
            if choch_distance < 1.0:  # %1'den yakın
                choch_status = "near"
            elif choch_distance < 3.0:  # %3'ten yakın
                choch_status = "approaching"
            else:
                choch_status = "distant"
        
        return {
            "status": "success",
            "current_price": current_price,
            "market_structure": market_structure,
            "levels": {
                "bos_level": market_structure.get('bos_level'),
                "choch_level": market_structure.get('choch_level'),
                "bos_status": bos_status,
                "choch_status": choch_status
            },
            "structure_summary": {
                "trend_strength": "strong" if (
                    market_structure.get('higher_highs', 0) > 2 or 
                    market_structure.get('lower_lows', 0) > 2
                ) else "weak",
                "trend_consistency": market_structure.get('trend') != 'ranging'
            },
            "timestamp": timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Market structure hatası: {e}")
        return {
            "status": "error",
            "message": str(e),
            "market_structure": {}
        }