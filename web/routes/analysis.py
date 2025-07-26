"""
Analiz API endpoint'leri
"""
from fastapi import APIRouter
import json
import logging
from datetime import timedelta

from storage.sqlite_storage import SQLiteStorage
from config import settings
from utils import timezone
from web.utils import cache
from web.utils.formatters import format_analysis_summary

router = APIRouter(prefix="/api/analysis")
logger = logging.getLogger(__name__)

# Storage instance
storage = SQLiteStorage()

@router.get("/config")
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

@router.post("/trigger/{timeframe}")
async def trigger_analysis(timeframe: str):
    """Manuel olarak analiz tetikle"""
    try:
        valid_timeframes = ["15m", "1h", "4h", "1d"]
        if timeframe not in valid_timeframes:
            return {"error": f"Geçersiz timeframe. Geçerli değerler: {valid_timeframes}"}
        
        # Son fiyat verisini al
        latest_price = storage.get_latest_price()
        if not latest_price:
            return {"error": "Fiyat verisi bulunamadı"}
        
        # Mum verilerini oluştur
        if timeframe == "15m":
            candles = storage.generate_gram_candles(15, 100)
        elif timeframe == "1h":
            candles = storage.generate_gram_candles(60, 100)
        elif timeframe == "4h":
            candles = storage.generate_gram_candles(240, 100)
        else:  # 1d
            candles = storage.generate_gram_candles(1440, 100)
        
        if len(candles) < 50:
            return {"error": f"Yeterli veri yok. Mevcut: {len(candles)}, Gerekli: 50"}
        
        # Timeframe'e özel analiz çalıştır (gerçek analiz main.py'de çalışıyor)
        # Burada sadece analiz tetiklendiğini logla
        logger.info(f"Manuel analiz tetiklendi: {timeframe}")
        
        # Son analizi dön
        analyses = storage.get_hybrid_analysis_history(limit=1, timeframe=timeframe)
        
        return {
            "status": "success",
            "message": f"{timeframe} analizi tetiklendi",
            "timeframe": timeframe,
            "timestamp": timezone.now().isoformat(),
            "latest_price": float(latest_price.gram_altin) if latest_price.gram_altin else None,
            "candle_count": len(candles),
            "last_analysis": analyses[0] if analyses else None
        }
        
    except Exception as e:
        logger.error(f"Analiz tetikleme hatası: {e}")
        return {"error": str(e)}

@router.get("/history")
async def get_analysis_history(
    timeframe: str = None,
    page: int = 1,
    per_page: int = 20,
    start_date: str = None,
    end_date: str = None,
    signal_type: str = None
):
    """Son hibrit analiz sonuçlarını döndür - gelişmiş filtreleme ile"""
    try:
        from datetime import datetime
        
        # Tarih parametrelerini parse et
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if start_date else None
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00')) if end_date else None
        
        # Offset hesapla
        offset = (page - 1) * per_page if page > 0 else 0
        
        # Toplam kayıt sayısını al
        total_count = storage.get_hybrid_analysis_count(
            timeframe=timeframe,
            start_date=start_dt,
            end_date=end_dt,
            signal_type=signal_type
        )
        
        # Hibrit analiz verilerini al
        analyses = storage.get_hybrid_analysis_history(
            limit=per_page, 
            offset=offset,
            timeframe=timeframe,
            start_date=start_dt,
            end_date=end_dt,
            signal_type=signal_type
        )
        
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
                "summary": format_analysis_summary(analysis),
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
        
        return {
            "analyses": formatted_analyses,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_count,
                "pages": (total_count + per_page - 1) // per_page if per_page > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting hybrid analysis history: {e}")
        # Hata durumunda boş liste dön
        return {"analyses": []}

@router.get("/details")
async def get_analysis_details(timeframe: str = None):
    """Detaylı analiz bilgilerini döndür"""
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # En son analizleri al
            if timeframe:
                cursor.execute("""
                    SELECT * FROM hybrid_analysis 
                    WHERE timeframe = ? 
                    ORDER BY id DESC LIMIT 1
                """, (timeframe,))
            else:
                cursor.execute("""
                    SELECT * FROM hybrid_analysis 
                    ORDER BY id DESC LIMIT 3
                """)
            
            analyses = []
            for row in cursor.fetchall():
                col_names = [desc[0] for desc in cursor.description]
                data = dict(zip(col_names, row))
                
                # JSON alanları parse et
                try:
                    gram_analysis = json.loads(data.get('gram_analysis', '{}'))
                    global_analysis = json.loads(data.get('global_analysis', '{}'))
                    currency_analysis = json.loads(data.get('currency_analysis', '{}'))
                    advanced_indicators = json.loads(data.get('advanced_indicators', '{}'))
                    pattern_analysis = json.loads(data.get('pattern_analysis', '{}'))
                except:
                    continue
                
                analyses.append({
                    'id': data['id'],
                    'timestamp': data['timestamp'],
                    'timeframe': data['timeframe'],
                    'signal': data['signal'],
                    'confidence': float(data['confidence']) if data['confidence'] else 0,
                    'gram_price': float(data['gram_price']) if data['gram_price'] else 0,
                    'gram_analysis': gram_analysis,
                    'global_analysis': global_analysis,
                    'currency_analysis': currency_analysis,
                    'advanced_indicators': advanced_indicators,
                    'pattern_analysis': pattern_analysis
                })
            
            return {'analyses': analyses}
            
    except Exception as e:
        logger.error(f"Analysis details error: {e}")
        return {'analyses': []}

@router.get("/levels")
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

# Yeni endpoint'ler ekleyelim

@router.get("/indicators/{timeframe}")
async def get_technical_indicators(timeframe: str):
    """Belirli bir timeframe için teknik göstergeleri getir"""
    try:
        # Cache kontrolü
        cache_key = f"indicators_{timeframe}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Timeframe'e göre mum verilerini al
        interval_map = {
            "15m": 15,
            "1h": 60,
            "4h": 240,
            "1d": 1440
        }
        
        minutes = interval_map.get(timeframe, 60)
        candles = storage.generate_gram_candles(minutes, 100)
        
        if len(candles) < 20:
            return {"error": "Yeterli veri yok"}
        
        # Son analizi al
        analyses = storage.get_hybrid_analysis_history(limit=1, timeframe=timeframe)
        
        if not analyses:
            return {"error": "Analiz bulunamadı"}
        
        analysis = analyses[0]
        
        # Göstergeleri hazırla
        indicators = {
            "rsi": {
                "value": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("rsi"),
                "overbought": 70,
                "oversold": 30
            },
            "macd": {
                "macd": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("macd"),
                "signal": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("macd_signal"),
                "histogram": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("macd_histogram")
            },
            "bollinger": {
                "upper": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("bb_upper"),
                "middle": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("bb_middle"),
                "lower": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("bb_lower")
            },
            "cci": analysis.get("advanced_indicators", {}).get("cci", {}).get("value"),
            "mfi": analysis.get("advanced_indicators", {}).get("mfi", {}).get("value"),
            "stochastic": {
                "k": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("stoch_k"),
                "d": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("stoch_d")
            },
            "moving_averages": {
                "ma20": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("ma20"),
                "ma50": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("ma50"),
                "ma200": analysis.get("details", {}).get("gram", {}).get("indicators", {}).get("ma200")
            }
        }
        
        result = {
            "timeframe": timeframe,
            "timestamp": analysis["timestamp"].isoformat(),
            "price": float(analysis["gram_price"]),
            "indicators": indicators
        }
        
        cache.set(cache_key, result, ttl=60)  # 1 dakika cache
        return result
        
    except Exception as e:
        logger.error(f"Error getting indicators: {e}")
        return {"error": str(e)}

@router.get("/performance/summary")
async def get_performance_summary():
    """Genel performans özeti"""
    try:
        # Son 7 günlük performans verilerini al
        week_ago = timezone.now() - timedelta(days=7)
        
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Toplam sinyal sayıları
            cursor.execute("""
                SELECT 
                    signal,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence
                FROM hybrid_analysis
                WHERE timestamp > ?
                GROUP BY signal
            """, (week_ago,))
            
            signal_stats = {}
            for row in cursor.fetchall():
                signal_stats[row[0]] = {
                    "count": row[1],
                    "avg_confidence": row[2]
                }
            
            # Timeframe bazlı istatistikler
            cursor.execute("""
                SELECT 
                    timeframe,
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN signal = 'BUY' THEN 1 ELSE 0 END) as buy_signals,
                    SUM(CASE WHEN signal = 'SELL' THEN 1 ELSE 0 END) as sell_signals,
                    AVG(confidence) as avg_confidence
                FROM hybrid_analysis
                WHERE timestamp > ? AND signal IN ('BUY', 'SELL')
                GROUP BY timeframe
            """, (week_ago,))
            
            timeframe_stats = []
            for row in cursor.fetchall():
                timeframe_stats.append({
                    "timeframe": row[0],
                    "total_signals": row[1],
                    "buy_signals": row[2],
                    "sell_signals": row[3],
                    "avg_confidence": row[4]
                })
            
            # Son 24 saatteki en güçlü sinyaller
            yesterday = timezone.now() - timedelta(days=1)
            cursor.execute("""
                SELECT 
                    timestamp,
                    timeframe,
                    signal,
                    confidence,
                    gram_price
                FROM hybrid_analysis
                WHERE timestamp > ? AND signal IN ('BUY', 'SELL')
                ORDER BY confidence DESC
                LIMIT 5
            """, (yesterday,))
            
            strongest_signals = []
            for row in cursor.fetchall():
                strongest_signals.append({
                    "timestamp": row[0],
                    "timeframe": row[1],
                    "signal": row[2],
                    "confidence": row[3],
                    "price": row[4]
                })
            
            return {
                "period": "7_days",
                "signal_distribution": signal_stats,
                "timeframe_performance": timeframe_stats,
                "strongest_signals_24h": strongest_signals
            }
            
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        return {"error": str(e)}

@router.get("/patterns/active")
async def get_active_patterns():
    """Aktif chart pattern'leri getir"""
    try:
        # Son analizlerden pattern bilgilerini al
        analyses = storage.get_hybrid_analysis_history(limit=4)  # Her timeframe için 1
        
        active_patterns = []
        for analysis in analyses:
            pattern_data = analysis.get("pattern_analysis", {})
            if pattern_data.get("pattern_found"):
                pattern = pattern_data.get("best_pattern", {})
                active_patterns.append({
                    "timeframe": analysis["timeframe"],
                    "pattern": pattern.get("pattern", "Unknown"),
                    "signal": pattern_data.get("signal", "NEUTRAL"),
                    "confidence": pattern_data.get("confidence", 0),
                    "timestamp": analysis["timestamp"].isoformat(),
                    "price": float(analysis["gram_price"])
                })
        
        return {
            "patterns": active_patterns,
            "count": len(active_patterns)
        }
        
    except Exception as e:
        logger.error(f"Error getting active patterns: {e}")
        return {"error": str(e)}

@router.get("/ons-indicators")
async def get_ons_indicators():
    """ONS/USD teknik göstergelerini getir"""
    try:
        # Son hibrit analizden ONS/USD göstergelerini al
        analyses = storage.get_hybrid_analysis_history(limit=1)
        
        if not analyses:
            return {"error": "No analysis data available"}
            
        analysis = analyses[0]
        global_data = analysis.get("global_trend", {})
        
        # ONS/USD teknik göstergeleri
        technical_indicators = global_data.get("technical_indicators", {})
        
        return {
            "timestamp": analysis["timestamp"].isoformat(),
            "ons_usd_price": float(global_data.get("ons_usd_price", 0)),
            "trend_direction": global_data.get("direction", "NEUTRAL"),
            "trend_strength": global_data.get("strength", "WEAK"),
            "indicators": {
                "rsi": {
                    "value": technical_indicators.get("rsi"),
                    "signal": technical_indicators.get("rsi_signal", "neutral")
                },
                "macd": technical_indicators.get("macd", {}),
                "bollinger": technical_indicators.get("bollinger", {}),
                "stochastic": technical_indicators.get("stochastic", {})
            },
            "indicator_signal": global_data.get("indicator_signal", {
                "signal": "NEUTRAL",
                "confidence": 0
            })
        }
        
    except Exception as e:
        logger.error(f"Error getting ONS indicators: {e}")
        return {"error": str(e)}