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
async def get_performance_metrics():
    """Gerçek trading performans metrikleri - simülasyon verilerinden"""
    cached = cache.get("performance_metrics")
    if cached:
        return cached
    
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Son fiyat ve değişimler
            now = timezone.now()
            yesterday = now - timedelta(hours=24)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            # Güncel fiyat bilgisi
            latest_price = storage.get_latest_price()
            current_price = float(latest_price.gram_altin) if latest_price and latest_price.gram_altin else 0
            
            # Simülasyon performans metrikleri - son 30 gün
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
            """, (month_ago,))
            
            month_stats = cursor.fetchone()
            
            # Son 7 gün performansı
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN net_profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(net_profit_loss) as total_pnl
                FROM sim_positions
                WHERE status = 'CLOSED' AND exit_time >= ?
            """, (week_ago,))
            
            week_stats = cursor.fetchone()
            
            # Son 24 saat performansı
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN net_profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(net_profit_loss) as total_pnl
                FROM sim_positions
                WHERE status = 'CLOSED' AND exit_time >= ?
            """, (yesterday,))
            
            daily_stats = cursor.fetchone()
            
            # Timeframe bazlı performans
            cursor.execute("""
                SELECT 
                    timeframe,
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN net_profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(net_profit_loss) as total_pnl,
                    AVG(net_profit_loss) as avg_pnl
                FROM sim_positions
                WHERE status = 'CLOSED' AND exit_time >= ?
                GROUP BY timeframe
            """, (month_ago,))
            
            timeframe_performance = {}
            for row in cursor.fetchall():
                tf, total, wins, pnl, avg_pnl = row
                win_rate = (wins / total * 100) if total > 0 else 0
                timeframe_performance[tf] = {
                    "total_trades": total,
                    "winning_trades": wins,
                    "win_rate": win_rate,
                    "total_pnl": float(pnl) if pnl else 0,
                    "avg_pnl": float(avg_pnl) if avg_pnl else 0
                }
            
            # En başarılı timeframe
            best_timeframe = max(
                timeframe_performance.items(), 
                key=lambda x: x[1]["win_rate"],
                default=("N/A", {"win_rate": 0})
            )
            
            # Açık pozisyonlar
            cursor.execute("""
                SELECT COUNT(*) as open_positions,
                       SUM(allocated_capital) as locked_capital
                FROM sim_positions
                WHERE status = 'OPEN'
            """)
            
            open_positions = cursor.fetchone()
            
            # Metrikleri hesapla
            month_total = month_stats[0] or 0
            month_wins = month_stats[1] or 0
            month_losses = month_stats[2] or 0
            month_pnl = float(month_stats[3] or 0)
            avg_win = float(month_stats[4] or 0)
            avg_loss = float(month_stats[5] or 0)
            
            # Başarı oranları
            month_win_rate = (month_wins / month_total * 100) if month_total > 0 else 0
            week_win_rate = (week_stats[1] / week_stats[0] * 100) if week_stats[0] > 0 else 0
            daily_win_rate = (daily_stats[1] / daily_stats[0] * 100) if daily_stats[0] > 0 else 0
            
            # Profit factor
            profit_factor = (avg_win * month_wins) / (avg_loss * month_losses) if month_losses > 0 and avg_loss > 0 else 0
            
            # Trend analizi (son 7 gün ortalama win rate'e göre)
            trend = "stable"
            if daily_win_rate > week_win_rate * 1.1:  # %10'dan fazla iyileşme
                trend = "improving"
            elif daily_win_rate < week_win_rate * 0.9:  # %10'dan fazla kötüleşme
                trend = "declining"
            
            result = {
                "overview": {
                    "current_price": current_price,
                    "open_positions": open_positions[0] if open_positions else 0,
                    "locked_capital": float(open_positions[1] or 0) if open_positions else 0,
                    "trend": trend
                },
                "performance": {
                    "daily": {
                        "trades": daily_stats[0] or 0,
                        "wins": daily_stats[1] or 0,
                        "win_rate": daily_win_rate,
                        "pnl": float(daily_stats[2] or 0),
                        "pnl_per_trade": float(daily_stats[2] or 0) / daily_stats[0] if daily_stats[0] > 0 else 0
                    },
                    "weekly": {
                        "trades": week_stats[0] or 0,
                        "wins": week_stats[1] or 0,
                        "win_rate": week_win_rate,
                        "pnl": float(week_stats[2] or 0),
                        "pnl_per_trade": float(week_stats[2] or 0) / week_stats[0] if week_stats[0] > 0 else 0
                    },
                    "monthly": {
                        "trades": month_total,
                        "wins": month_wins,
                        "losses": month_losses,
                        "win_rate": month_win_rate,
                        "pnl": month_pnl,
                        "avg_win": avg_win,
                        "avg_loss": avg_loss,
                        "profit_factor": profit_factor,
                        "best_trade": float(month_stats[6] or 0),
                        "worst_trade": float(month_stats[7] or 0)
                    }
                },
                "timeframes": timeframe_performance,
                "best_timeframe": {
                    "name": best_timeframe[0],
                    "stats": best_timeframe[1]
                },
                "last_update": timezone.now().isoformat()
            }
            
            cache.set("performance_metrics", result, ttl=60)  # 1 dakika cache
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
async def get_realtime_performance():
    """Gerçek zamanlı sinyal performansı ve açık pozisyonlar"""
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            now = timezone.now()
            
            # Açık pozisyonlar detayı
            cursor.execute("""
                SELECT 
                    sp.id,
                    sp.timeframe,
                    sp.signal_type,
                    sp.entry_price,
                    sp.allocated_capital,
                    sp.entry_time,
                    sp.stop_loss,
                    sp.take_profit,
                    s.name as simulation_name,
                    s.strategy_type
                FROM sim_positions sp
                JOIN simulations s ON sp.simulation_id = s.id
                WHERE sp.status = 'OPEN'
                ORDER BY sp.entry_time DESC
            """)
            
            open_positions = []
            latest_price = storage.get_latest_price()
            current_price = float(latest_price.gram_altin) if latest_price and latest_price.gram_altin else 0
            
            for row in cursor.fetchall():
                pos_id, tf, signal, entry, capital, entry_time, sl, tp, sim_name, strategy = row
                
                # Anlık kar/zarar hesapla
                if signal == 'BUY':
                    pnl = (current_price - float(entry)) * (float(capital) / float(entry))
                    pnl_pct = ((current_price - float(entry)) / float(entry)) * 100
                else:  # SELL
                    pnl = (float(entry) - current_price) * (float(capital) / float(entry))
                    pnl_pct = ((float(entry) - current_price) / float(entry)) * 100
                
                # Pozisyon süresi
                entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                duration = now - entry_dt
                duration_hours = duration.total_seconds() / 3600
                
                open_positions.append({
                    "id": pos_id,
                    "timeframe": tf,
                    "signal": signal,
                    "entry_price": float(entry),
                    "current_price": current_price,
                    "allocated_capital": float(capital),
                    "unrealized_pnl": round(pnl, 2),
                    "unrealized_pnl_pct": round(pnl_pct, 2),
                    "entry_time": entry_time,
                    "duration_hours": round(duration_hours, 1),
                    "stop_loss": float(sl) if sl else None,
                    "take_profit": float(tp) if tp else None,
                    "simulation": sim_name,
                    "strategy": strategy,
                    "risk_status": "HIGH" if pnl_pct < -2 else "MEDIUM" if pnl_pct < -1 else "LOW"
                })
            
            # Son kapatılan pozisyonlar (son 10)
            cursor.execute("""
                SELECT 
                    sp.timeframe,
                    sp.signal_type,
                    sp.entry_price,
                    sp.exit_price,
                    sp.net_profit_loss,
                    sp.profit_loss_pct,
                    sp.entry_time,
                    sp.exit_time,
                    sp.exit_reason,
                    s.name as simulation_name
                FROM sim_positions sp
                JOIN simulations s ON sp.simulation_id = s.id
                WHERE sp.status = 'CLOSED'
                ORDER BY sp.exit_time DESC
                LIMIT 10
            """)
            
            closed_positions = []
            for row in cursor.fetchall():
                tf, signal, entry, exit, pnl, pnl_pct, entry_time, exit_time, reason, sim_name = row
                
                # İşlem süresi
                entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                exit_dt = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
                duration = exit_dt - entry_dt
                
                closed_positions.append({
                    "timeframe": tf,
                    "signal": signal,
                    "entry_price": float(entry),
                    "exit_price": float(exit),
                    "pnl": float(pnl),
                    "pnl_pct": float(pnl_pct),
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "duration_hours": round(duration.total_seconds() / 3600, 1),
                    "exit_reason": reason,
                    "simulation": sim_name,
                    "success": pnl > 0
                })
            
            # Son sinyaller ve durumları
            cursor.execute("""
                SELECT 
                    ha.timestamp,
                    ha.timeframe,
                    ha.signal,
                    ha.confidence,
                    ha.gram_price,
                    ha.stop_loss,
                    ha.take_profit,
                    CASE 
                        WHEN EXISTS (
                            SELECT 1 FROM sim_positions sp 
                            WHERE sp.signal_time = ha.timestamp 
                            AND sp.timeframe = ha.timeframe
                        ) THEN 'EXECUTED'
                        ELSE 'PENDING'
                    END as status
                FROM hybrid_analysis ha
                WHERE ha.signal IN ('BUY', 'SELL')
                AND ha.timestamp >= ?
                ORDER BY ha.timestamp DESC
                LIMIT 20
            """, (now - timedelta(hours=6),))  # Son 6 saat
            
            recent_signals = []
            for row in cursor.fetchall():
                timestamp, tf, signal, conf, price, sl, tp, status = row
                recent_signals.append({
                    "timestamp": timestamp,
                    "timeframe": tf,
                    "signal": signal,
                    "confidence": float(conf),
                    "price": float(price),
                    "stop_loss": float(sl) if sl else None,
                    "take_profit": float(tp) if tp else None,
                    "status": status
                })
            
            # Özet istatistikler
            total_open_capital = sum(p["allocated_capital"] for p in open_positions)
            total_unrealized_pnl = sum(p["unrealized_pnl"] for p in open_positions)
            
            return {
                "summary": {
                    "open_positions_count": len(open_positions),
                    "total_open_capital": round(total_open_capital, 2),
                    "total_unrealized_pnl": round(total_unrealized_pnl, 2),
                    "current_price": current_price,
                    "last_update": timezone.now().isoformat()
                },
                "open_positions": open_positions,
                "recent_closed": closed_positions,
                "recent_signals": recent_signals,
                "status": "success"
            }
            
    except Exception as e:
        logger.error(f"Realtime performans hatası: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "summary": {},
            "open_positions": [],
            "recent_closed": [],
            "recent_signals": []
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

@router.get("/market-regime/alerts")
async def get_regime_alerts():
    """Market regime uyarıları"""
    try:
        # Mevcut regime'i al
        regime_response = await get_market_regime()
        
        if regime_response.get('status') != 'success':
            return {"alerts": [], "status": "error"}
        
        alerts = []
        regime = regime_response
        
        # Volatilite uyarıları
        vol_regime = regime['volatility_regime']
        if vol_regime['squeeze_potential']:
            alerts.append({
                "type": "VOLATILITY_SQUEEZE",
                "level": "HIGH",
                "message": "Volatilite sıkışması tespit edildi - Breakout bekleniyor",
                "recommendation": "Pozisyon boyutunu azalt, breakout yönünü bekle"
            })
        elif vol_regime['level'] == 'extreme':
            alerts.append({
                "type": "EXTREME_VOLATILITY",
                "level": "HIGH", 
                "message": "Ekstrem volatilite seviyesi",
                "recommendation": "Risk yönetimini sıkılaştır, stop loss'ları daralt"
            })
        
        # Trend uyarıları
        trend_regime = regime['trend_regime']
        if trend_regime['breakout_potential']:
            alerts.append({
                "type": "BREAKOUT_POTENTIAL",
                "level": "MEDIUM",
                "message": "Breakout potansiyeli yüksek",
                "recommendation": "Trend takip stratejisine hazır ol"
            })
        
        # Momentum uyarıları
        momentum_regime = regime['momentum_regime']
        if momentum_regime['state'] == 'exhausted':
            alerts.append({
                "type": "MOMENTUM_EXHAUSTION",
                "level": "HIGH",
                "message": "Momentum tükenmesi - Reversal riski",
                "recommendation": "Pozisyonları azalt, reversal sinyallerini izle"
            })
        elif momentum_regime['reversal_potential'] > 70:
            alerts.append({
                "type": "REVERSAL_WARNING",
                "level": "MEDIUM",
                "message": "Yüksek reversal potansiyeli",
                "recommendation": "Counter-trend fırsatlarını değerlendir"
            })
        
        # Regime transition uyarıları
        transition = regime['regime_transition']
        if transition['early_warning']:
            alerts.append({
                "type": "REGIME_TRANSITION",
                "level": "MEDIUM",
                "message": f"Regime değişimi yaklaşıyor: {transition['next_regime']}",
                "recommendation": "Strateji parametrelerini gözden geçir"
            })
        
        return {
            "status": "success",
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Regime alerts hatası: {e}")
        return {
            "status": "error", 
            "alerts": [],
            "message": str(e)
        }