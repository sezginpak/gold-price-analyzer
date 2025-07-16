"""
Gold Price Analyzer - Ana uygulama
"""
import asyncio
import signal
import sys
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

from services.harem_altin_service import HaremAltinPriceService

from collectors.harem_price_collector import HaremPriceCollector
from analyzers.signal_generator import SignalGenerator
from storage.sqlite_storage import SQLiteStorage
from models.price_data import PriceData, PriceCandle
from config import settings

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GoldPriceAnalyzer:
    """Ana analiz sistemi"""
    
    def __init__(self):
        # HaremAltin servisi
        self.harem_service = HaremAltinPriceService(refresh_interval=5)
        
        # Collector
        self.collector = HaremPriceCollector(self.harem_service)
        
        # Storage
        self.storage = SQLiteStorage()
        
        # Signal generator
        self.signal_generator = SignalGenerator(min_confidence=settings.min_confidence_score)
        
        # Analiz için buffer
        self.analysis_counter = 0
        self.analysis_interval = 12  # Her 12 update'de bir analiz (60 saniye)
        
        # Sinyal geçmişi
        self.recent_signals = []
        self.max_signal_history = 10
        
    async def analyze_price(self, price_data: PriceData):
        """Fiyat analizi yap"""
        self.analysis_counter += 1
        
        # Her analysis_interval'de bir analiz yap
        if self.analysis_counter % self.analysis_interval != 0:
            return
            
        try:
            # Son 100 mumu al (15 dakikalık)
            candles_15m = self.storage.generate_candles(15, 100)
            
            if len(candles_15m) < 50:
                logger.info(f"Not enough candles for analysis: {len(candles_15m)}")
                return
            
            # Sinyal üret
            signal = self.signal_generator.generate_signal(
                price_data, 
                candles_15m, 
                settings.risk_tolerance
            )
            
            if signal:
                # Sinyal geçmişine ekle
                self.recent_signals.append(signal)
                if len(self.recent_signals) > self.max_signal_history:
                    self.recent_signals.pop(0)
                
                # Sinyali logla ve göster
                self._display_signal(signal, price_data)
                
                # TODO: Burada email/SMS bildirimi gönderilebilir
                
        except Exception as e:
            logger.error(f"Analysis error: {e}")
    
    def _display_signal(self, signal, price_data):
        """Sinyali güzel formatta göster"""
        signal_emoji = "🟢 ALIŞ" if signal.signal_type.value == "BUY" else "🔴 SATIŞ"
        
        print(f"\n{'='*60}")
        print(f"⚡ {signal_emoji} SİNYALİ ⚡")
        print(f"{'='*60}")
        print(f"📅 Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💰 Fiyat: {price_data.ons_try:.2f} TRY")
        print(f"📊 USD/TRY: {price_data.usd_try:.4f}")
        print(f"🎯 Hedef: {signal.target_price:.2f} TRY")
        print(f"🛑 Stop Loss: {signal.stop_loss:.2f} TRY")
        print(f"📈 Güven: %{signal.overall_confidence*100:.0f}")
        print(f"⚠️  Risk: {signal.risk_level.value}")
        print(f"\n📝 Sebepler:")
        for reason in signal.reasons:
            print(f"   • {reason}")
        print(f"{'='*60}\n")
    
    async def show_statistics(self):
        """Periyodik istatistik gösterimi"""
        while True:
            await asyncio.sleep(300)  # 5 dakikada bir
            
            try:
                stats = self.storage.get_statistics()
                if stats['total_records'] > 0:
                    print(f"\n📊 İSTATİSTİKLER")
                    print(f"{'─'*40}")
                    print(f"Toplam Kayıt: {stats['total_records']:,}")
                    print(f"İlk Kayıt: {stats['oldest_record']}")
                    print(f"Son Kayıt: {stats['newest_record']}")
                    print(f"Ort. Fiyat: {stats['average_price']:.2f} TRY")
                    print(f"Son {len(self.recent_signals)} Sinyal")
                    print(f"{'─'*40}\n")
            except Exception as e:
                logger.error(f"Statistics error: {e}")
    
    async def start(self):
        """Sistemi başlat"""
        logger.info("Gold Price Analyzer starting...")
        
        # Analiz callback'ini ekle
        self.collector.add_analysis_callback(self.analyze_price)
        
        # Collector'ı başlat
        await self.collector.start()
        
        # İstatistik gösterimi
        asyncio.create_task(self.show_statistics())
        
        logger.info("System started successfully")
        
        # Başlangıç mesajı
        print(f"\n{'='*60}")
        print("🏆 ALTIN FİYAT ANALİZ SİSTEMİ 🏆")
        print(f"{'='*60}")
        print(f"✅ Sistem başlatıldı")
        print(f"📊 Veri toplama aralığı: {self.harem_service.refresh_interval} saniye")
        print(f"🎯 Minimum güven skoru: %{settings.min_confidence_score*100:.0f}")
        print(f"⚠️  Risk toleransı: {settings.risk_tolerance}")
        print(f"{'='*60}\n")
        
    async def stop(self):
        """Sistemi durdur"""
        logger.info("Stopping system...")
        await self.collector.stop()
        await self.harem_service.stop()
        logger.info("System stopped")


async def main():
    """Ana fonksiyon"""
    analyzer = GoldPriceAnalyzer()
    
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