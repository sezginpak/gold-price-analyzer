"""
Gold Price Analyzer - Hibrit Sistem Ana Uygulama
"""
import asyncio
import signal
import sys
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

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

# Logging setup - dosya ve console'a yaz
logger = setup_logger(
    name="gold_analyzer",
    log_dir="logs",
    level="INFO"
)


class HybridGoldAnalyzer:
    """Hibrit analiz sistemi - Gram altın odaklı"""
    
    def __init__(self):
        # HaremAltin servisi
        self.harem_service = HaremAltinPriceService(refresh_interval=5)
        
        # Collector
        self.collector = HaremPriceCollector(self.harem_service)
        
        # Storage
        self.storage = SQLiteStorage()
        
        # Hibrit strateji
        self.strategy = HybridStrategy()
        
        # Timeframe analyzer (farklı zaman dilimleri için)
        self.timeframe_analyzer = TimeframeAnalyzer(self.storage)
        
        # Son analiz zamanları - dict comprehension ile optimize
        self.last_analysis_times = {tf: datetime.min for tf in ANALYSIS_INTERVALS.keys()}
        
        # Analiz aralıkları (dakika) - constants'tan al
        self.analysis_intervals = ANALYSIS_INTERVALS
        
    async def analyze_price(self, price_data: PriceData):
        """Fiyat verisi geldiğinde analiz yap"""
        try:
            current_time = datetime.now()
            
            # Her timeframe için analiz zamanı geldi mi kontrol et
            for timeframe, interval_minutes in self.analysis_intervals.items():
                if current_time >= self.last_analysis_times[timeframe] + timedelta(minutes=interval_minutes):
                    await self.run_hybrid_analysis(timeframe)
                    self.last_analysis_times[timeframe] = current_time
                    
        except Exception as e:
            logger.error(f"Price analysis error: {e}", exc_info=True)
    
    async def run_hybrid_analysis(self, timeframe: str):
        """Hibrit analizi çalıştır"""
        try:
            logger.info(f"Running hybrid analysis for {timeframe}")
            
            # Gerekli mum sayısı ve aralık - constants'tan al
            required_candles = CANDLE_REQUIREMENTS.get(timeframe, 100)
            interval_minutes = self.analysis_intervals.get(timeframe, 15)
            
            # Gram altın mumlarını oluştur
            gram_candles = self.storage.generate_candles(interval_minutes, required_candles)
            
            if len(gram_candles) < required_candles * 0.7:  # %70'i varsa analiz yap
                logger.warning(f"Not enough gram candles for {timeframe}: {len(gram_candles)}/{required_candles}")
                return
            
            # Market data (son 200 kayıt - trend analizi için)
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=48)
            market_data = self.storage.get_price_range(start_time, end_time)
            
            if len(market_data) < 50:
                logger.warning(f"Not enough market data: {len(market_data)}")
                return
            
            # Gram altın mumlarını model formatına çevir - list comprehension ile optimize
            gram_candle_models = [
                GramAltinCandle(
                    timestamp=candle.timestamp,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    interval=candle.interval
                )
                for candle in gram_candles
            ]
            
            # Hibrit analiz
            analysis_result = self.strategy.analyze(gram_candle_models, market_data)
            
            # Timeframe ekle
            analysis_result["timeframe"] = timeframe
            
            # Sonucu kaydet
            self.storage.save_hybrid_analysis(analysis_result)
            
            # Sinyali göster
            self._display_hybrid_signal(analysis_result, timeframe)
            
        except Exception as e:
            logger.error(f"Hybrid analysis error for {timeframe}: {e}", exc_info=True)
    
    def _display_hybrid_signal(self, analysis: Dict, timeframe: str):
        """Hibrit analiz sonucunu göster"""
        signal = analysis["signal"]
        if signal == "HOLD":
            return  # HOLD sinyallerini gösterme
        
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
        print(f"📅 Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
        """Periyodik istatistik gösterimi"""
        while True:
            await asyncio.sleep(300)  # 5 dakikada bir
            
            try:
                stats = self.storage.get_statistics()
                latest_analysis = self.storage.get_latest_hybrid_analysis()
                
                if stats['total_records'] > 0:
                    print(f"\n📊 SİSTEM İSTATİSTİKLERİ")
                    print(f"{'─'*50}")
                    print(f"Toplam Kayıt: {stats['total_records']:,}")
                    print(f"Son Güncelleme: {stats['newest_record']}")
                    
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
        logger.info("System stopped")


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
        
        # Sonsuza kadar çalış
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await analyzer.stop()


if __name__ == "__main__":
    asyncio.run(main())