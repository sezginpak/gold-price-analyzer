"""
Gold Price Analyzer - Hibrit Sistem Ana Uygulama
"""
import asyncio
import signal
import sys
import logging
import json
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import gc  # Garbage collection için
import psutil  # System resource monitoring
import weakref  # Weak references for memory optimization
from utils.timezone import now, format_for_display

from services.harem_altin_service import HaremAltinPriceService
from collectors.harem_price_collector import HaremPriceCollector
from storage.sqlite_storage import SQLiteStorage
from models.price_data import PriceData
from models.market_data import GramAltinCandle
from strategies.hybrid_strategy import HybridStrategy
from config import settings
from analyzers.timeframe_analyzer import TimeframeAnalyzer
from utils.logger import setup_logger
from utils.constants import CANDLE_REQUIREMENTS, ANALYSIS_INTERVALS
from simulation.simulation_manager import SimulationManager
from models.simulation import StrategyType

# Logging setup - dosya ve console'a yaz
logger = setup_logger(
    name="gold_analyzer",
    log_dir="logs",
    level="DEBUG"  # DEBUG seviyesine çekildi
)


class HybridGoldAnalyzer:
    """Hibrit analiz sistemi - Memory & CPU Optimized"""
    
    def __init__(self):
        # Memory optimization: Use slots for fixed attributes
        self.__slots__ = ['harem_service', 'collector', 'storage', 'strategy', 
                         'timeframe_analyzer', 'simulation_manager', 'last_analysis_times', 
                         'analysis_intervals', '_analysis_cache', '_memory_threshold']
        
        # HaremAltin servisi - Optimized refresh interval
        self.harem_service = HaremAltinPriceService(refresh_interval=10)  # Increased from 5 to 10
        
        # Collector
        self.collector = HaremPriceCollector(self.harem_service)
        
        # Storage
        self.storage = SQLiteStorage()
        
        # Hibrit strateji
        self.strategy = HybridStrategy(storage=self.storage)
        
        # Timeframe analyzer (farklı zaman dilimleri için)
        self.timeframe_analyzer = TimeframeAnalyzer(self.storage)
        
        # Simülasyon yöneticisi
        self.simulation_manager = SimulationManager(self.storage)
        
        # Memory optimization: Analysis cache with size limit
        self._analysis_cache = {}
        self._memory_threshold = 500  # MB
        
        # Son analiz zamanları - dict comprehension ile optimize
        from datetime import datetime
        from utils.timezone import TURKEY_TZ
        # Timezone-aware minimum datetime kullan
        min_datetime = TURKEY_TZ.localize(datetime.min.replace(year=2000))
        self.last_analysis_times = {tf: min_datetime for tf in ANALYSIS_INTERVALS.keys()}
        
        # Analiz aralıkları (dakika) - constants'tan al
        self.analysis_intervals = ANALYSIS_INTERVALS
        
    async def analyze_price(self, price_data: PriceData):
        """Fiyat verisi geldiğinde analiz yap - Memory optimized"""
        try:
            # Memory check before analysis
            if self._check_memory_usage():
                logger.warning("High memory usage detected, running cleanup")
                await self._cleanup_memory()
            
            current_time = now()
            
            # Optimize timeframe analysis scheduling
            analysis_tasks = []
            for timeframe, interval_minutes in self.analysis_intervals.items():
                if current_time >= self.last_analysis_times[timeframe] + timedelta(minutes=interval_minutes):
                    analysis_tasks.append(self.run_hybrid_analysis(timeframe))
                    self.last_analysis_times[timeframe] = current_time
            
            # Run analysis tasks concurrently for better performance
            if analysis_tasks:
                await asyncio.gather(*analysis_tasks, return_exceptions=True)
                    
        except Exception as e:
            logger.error(f"Price analysis error: {e}", exc_info=True)
    
    async def run_hybrid_analysis(self, timeframe: str):
        """Hibrit analizi çalıştır - CPU & Memory Optimized"""
        try:
            logger.debug(f"Running hybrid analysis for {timeframe}")  # Reduced to debug level
            
            # Cache-friendly approach
            cache_key = f"analysis_{timeframe}"
            if cache_key in self._analysis_cache:
                cached_time, cached_result = self._analysis_cache[cache_key]
                if (now() - cached_time).total_seconds() < 30:  # 30 second cache
                    return cached_result
            
            # Optimized data requirements based on timeframe
            required_candles = min(CANDLE_REQUIREMENTS.get(timeframe, 100), 150)  # Cap at 150
            interval_minutes = self.analysis_intervals.get(timeframe, 15)
            
            # Gram altın mumlarını oluştur - optimized call
            gram_candles = self.storage.generate_gram_candles(interval_minutes, required_candles)
            
            if len(gram_candles) < required_candles * 0.6:  # Reduced threshold to 60%
                logger.debug(f"Not enough gram candles for {timeframe}: {len(gram_candles)}/{required_candles}")
                return
            
            # Optimized market data retrieval - reduced timespan
            end_time = now()
            hours_back = 24 if timeframe in ['15m', '1h'] else 48  # Adaptive time range
            start_time = end_time - timedelta(hours=hours_back)
            
            # Use latest prices for better performance
            market_data_size = min(200, len(gram_candles) * 2)  # Adaptive size
            market_data = self.storage.get_latest_prices(market_data_size)
            
            if len(market_data) < 30:  # Reduced minimum requirement
                logger.debug(f"Not enough market data: {len(market_data)}")
                return
            
            # Memory-efficient model conversion - using generator where possible
            try:
                # Optimized model conversion with memory reuse
                gram_candle_models = []
                for candle in gram_candles:
                    model = GramAltinCandle(
                        timestamp=candle.timestamp,
                        open=candle.open,
                        high=candle.high,
                        low=candle.low,
                        close=candle.close,
                        interval=candle.interval
                    )
                    gram_candle_models.append(model)
                
                # Hibrit analiz - timeframe parametresi ile
                analysis_result = self.strategy.analyze(gram_candle_models, market_data, timeframe)
                
                # Timeframe ekle (yedek)
                analysis_result["timeframe"] = timeframe
                
                # Cache the result
                self._analysis_cache[cache_key] = (now(), analysis_result)
                
                # Limit cache size to prevent memory bloat
                if len(self._analysis_cache) > 10:
                    # Remove oldest entry
                    oldest_key = min(self._analysis_cache.keys(), 
                                   key=lambda k: self._analysis_cache[k][0])
                    del self._analysis_cache[oldest_key]
                
                # Sonucu kaydet
                self.storage.save_hybrid_analysis(analysis_result)
                
                # Sinyali göster (only for important signals)
                if analysis_result.get("signal") != "HOLD":
                    self._display_hybrid_signal(analysis_result, timeframe)
                
            finally:
                # Explicit cleanup for large objects
                del gram_candle_models
                del market_data
                gc.collect()
            
        except Exception as e:
            logger.error(f"Hybrid analysis error for {timeframe}: {e}", exc_info=True)
    
    def _display_hybrid_signal(self, analysis: Dict, timeframe: str):
        """Hibrit analiz sonucunu göster"""
        signal = analysis["signal"]
        if signal == "HOLD":
            return  # HOLD sinyallerini gösterme
        
        # Trading signal kaydet
        if signal in ["BUY", "SELL", "STRONG_BUY", "STRONG_SELL"]:
            trading_signal = {
                "timestamp": analysis["timestamp"],
                "signal_type": signal,
                "price_level": analysis["gram_price"],
                "confidence": analysis["confidence"],
                "risk_level": analysis["currency_risk"]["risk_level"],
                "target_price": analysis.get("take_profit"),
                "stop_loss": analysis.get("stop_loss"),
                "reasons": json.dumps({
                    "summary": analysis["summary"],
                    "timeframe": timeframe,
                    "strength": analysis["signal_strength"],
                    "recommendations": analysis["recommendations"]
                })
            }
            try:
                self.storage.save_trading_signal(trading_signal)
            except Exception as e:
                logger.error(f"Failed to save trading signal: {e}")
        
        # Emoji mapping'leri class seviyesinde sabit olarak tanımlasaydık daha optimize olurdu
        # ama şimdilik inline bırakalım
        signal_emoji = "🟢 ALIŞ" if signal == "BUY" else "🔴 SATIŞ"
        strength_emoji = {
            "STRONG": "💪",
            "MODERATE": "👍",
            "WEAK": "👌"
        }.get(analysis["signal_strength"], "")
        
        print(f"\n{'='*70}")
        print(f"⚡ {signal_emoji} SİNYALİ {strength_emoji} [{timeframe}] ⚡")
        print(f"{'='*70}")
        print(f"📅 Zaman: {format_for_display(now())}")
        print(f"💰 Gram Altın: {analysis['gram_price']:.2f} TRY")
        print(f"📊 Güven: %{analysis['confidence']*100:.0f}")
        position_size = analysis.get('position_size', 0)
        if isinstance(position_size, dict):
            position_value = position_size.get('lots', 0)
        else:
            position_value = position_size
        print(f"📈 Pozisyon: {position_value:.3f} lot")
        
        if analysis.get("stop_loss"):
            print(f"🛑 Stop Loss: {analysis['stop_loss']:.2f} TRY")
        if analysis.get("take_profit"):
            print(f"🎯 Hedef: {analysis['take_profit']:.2f} TRY")
        if analysis.get("risk_reward_ratio"):
            print(f"⚖️  Risk/Ödül: 1:{analysis['risk_reward_ratio']:.2f}")
        
        # Global durum
        global_trend = analysis["global_trend"]
        print(f"\n🌍 Global Trend: {global_trend['trend_direction']} ({global_trend['trend_strength']})")
        
        # Kur riski
        currency_risk = analysis["currency_risk"]
        risk_emoji = {
            "LOW": "🟢",
            "MEDIUM": "🟡",
            "HIGH": "🔴",
            "EXTREME": "🚨"
        }.get(currency_risk['risk_level'], "")
        print(f"💱 USD/TRY Risk: {risk_emoji} {currency_risk['risk_level']}")
        
        # Öneriler
        print(f"\n📝 Öneriler:")
        for rec in analysis["recommendations"]:
            print(f"   • {rec}")
        
        print(f"\n📋 Özet: {analysis['summary']}")
        print(f"{'='*70}\n")
    
    async def show_statistics(self):
        """Periyodik istatistik gösterimi - Memory optimized"""
        while True:
            await asyncio.sleep(600)  # 10 dakikada bir (reduced frequency)
            
            try:
                # Advanced memory management
                await self._memory_management()
                
                stats = self.storage.get_statistics()
                latest_analysis = self.storage.get_latest_hybrid_analysis()
                
                # Memory usage info
                memory_info = self._get_memory_info()
                
                if stats['total_records'] > 0:
                    print(f"\n📊 SYSTEM PERFORMANCE")
                    print(f"{'─'*50}")
                    print(f"Toplam Kayıt: {stats['total_records']:,}")
                    print(f"Memory Usage: {memory_info['used']:.1f}MB (Peak: {memory_info['peak']:.1f}MB)")
                    print(f"CPU Usage: {memory_info['cpu']:.1f}%")
                    print(f"Cache Size: {len(self._analysis_cache)} entries")
                    
                    if latest_analysis:
                        print(f"\nSon Analiz:")
                        print(f"  Sinyal: {latest_analysis['signal']} ({latest_analysis['signal_strength']})")
                        print(f"  Güven: %{latest_analysis['confidence']*100:.0f}")
                        print(f"  Gram Altın: {latest_analysis['gram_price']:.2f} TRY")
                    
                    print(f"{'─'*50}\n")
            except Exception as e:
                logger.error(f"Statistics error: {e}")
    
    async def start(self):
        """Sistemi başlat"""
        logger.info("Hybrid Gold Price Analyzer starting...")
        
        # Analiz callback'ini ekle
        self.collector.add_analysis_callback(self.analyze_price)
        
        # Collector'ı başlat
        await self.collector.start()
        
        # İstatistik gösterimi
        asyncio.create_task(self.show_statistics())
        
        # Simülasyon sistemini başlat
        logger.info("Starting SimulationManager...")
        asyncio.create_task(self.simulation_manager.start())
        logger.info("SimulationManager task created")
        
        logger.info("System started successfully")
        
        # Başlangıç mesajı
        print(f"\n{'='*70}")
        print("🏆 HİBRİT ALTIN ANALİZ SİSTEMİ 🏆")
        print(f"{'='*70}")
        print(f"✅ Sistem başlatıldı")
        print(f"📊 Ana Fiyat: GRAM ALTIN")
        print(f"🌍 Trend Belirleyici: ONS/USD")
        print(f"💱 Risk Değerlendirme: USD/TRY")
        print(f"🎯 Analiz Aralıkları: 15dk, 1s, 4s, Günlük")
        print(f"{'='*70}\n")
        
    async def stop(self):
        """Sistemi durdur"""
        logger.info("Stopping system...")
        await self.collector.stop()
        await self.harem_service.stop()
        await self.simulation_manager.stop()
        logger.info("System stopped")
    
    def _check_memory_usage(self) -> bool:
        """Memory usage kontrolü"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            return memory_mb > self._memory_threshold
        except:
            return False
    
    async def _cleanup_memory(self):
        """Memory cleanup işlemleri"""
        try:
            # Clear analysis cache
            self._analysis_cache.clear()
            
            # Force garbage collection
            gc.collect()
            
            logger.info("Memory cleanup completed")
        except Exception as e:
            logger.error(f"Memory cleanup error: {e}")
    
    async def _memory_management(self):
        """Advanced memory management"""
        try:
            # Garbage collection
            collected = gc.collect()
            
            # Clear old cache entries
            current_time = now()
            expired_keys = [
                key for key, (timestamp, _) in self._analysis_cache.items()
                if (current_time - timestamp).total_seconds() > 300  # 5 minutes
            ]
            
            for key in expired_keys:
                del self._analysis_cache[key]
            
            if collected > 0 or expired_keys:
                logger.debug(f"Memory management: {collected} objects collected, {len(expired_keys)} cache entries expired")
                
        except Exception as e:
            logger.error(f"Memory management error: {e}")
    
    def _get_memory_info(self) -> dict:
        """Memory ve CPU bilgilerini al"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'used': memory_info.rss / 1024 / 1024,  # MB
                'peak': memory_info.peak_wss / 1024 / 1024 if hasattr(memory_info, 'peak_wss') else memory_info.rss / 1024 / 1024,  # MB
                'cpu': process.cpu_percent()
            }
        except:
            return {'used': 0, 'peak': 0, 'cpu': 0}


async def main():
    """Ana fonksiyon"""
    analyzer = HybridGoldAnalyzer()
    
    # Signal handler
    def signal_handler(signum, frame):
        logger.info("Shutdown signal received")
        asyncio.create_task(analyzer.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await analyzer.start()
        
        # Main loop with optimized sleep for better resource usage
        while True:
            await asyncio.sleep(60)  # 1 dakikalık döngü - resource optimization
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await analyzer.stop()


if __name__ == "__main__":
    asyncio.run(main())