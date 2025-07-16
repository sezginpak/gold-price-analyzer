"""
Gold Price Analyzer - Robust Version
Auto-restart, error handling ve detaylı loglama ile
"""
import asyncio
import signal
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List
import traceback

from services.harem_altin_service import HaremAltinPriceService
from collectors.harem_price_collector import HaremPriceCollector
from analyzers.signal_generator import SignalGenerator
from storage.sqlite_storage import SQLiteStorage
from models.price_data import PriceData, PriceCandle
from config import settings
from utils.logger import setup_logger, log_exception

# Logger setup
logger = setup_logger(
    name="gold_analyzer",
    level=os.getenv("LOG_LEVEL", "INFO")
)


class RobustGoldPriceAnalyzer:
    """Hata toleranslı analiz sistemi"""
    
    def __init__(self):
        self.logger = logger
        self.restart_count = 0
        self.max_restarts = 10
        self.error_count = 0
        self.last_error_time = None
        self.running = False
        
        # Servisler
        self.harem_service = None
        self.collector = None
        self.storage = None
        self.signal_generator = None
        
        # İstatistikler
        self.stats = {
            "start_time": datetime.now(),
            "signals_generated": 0,
            "errors_caught": 0,
            "restarts": 0,
            "last_price_update": None,
            "total_price_updates": 0
        }
        
    def initialize_services(self):
        """Servisleri başlat/yeniden başlat"""
        try:
            self.logger.info(f"Initializing services (restart #{self.restart_count})")
            
            # HaremAltin servisi
            self.harem_service = HaremAltinPriceService(refresh_interval=5)
            
            # Collector
            self.collector = HaremPriceCollector(self.harem_service)
            
            # Storage
            self.storage = SQLiteStorage()
            
            # Signal generator
            self.signal_generator = SignalGenerator(
                min_confidence=settings.min_confidence_score
            )
            
            self.logger.info("All services initialized successfully")
            return True
            
        except Exception as e:
            log_exception(self.logger, e, "Service initialization")
            return False
    
    async def analyze_price_safe(self, price_data: PriceData):
        """Güvenli fiyat analizi"""
        try:
            self.stats["total_price_updates"] += 1
            self.stats["last_price_update"] = datetime.now()
            
            # Her 12 update'de bir analiz (60 saniye)
            if self.stats["total_price_updates"] % 12 != 0:
                return
            
            self.logger.debug(f"Analyzing price: {price_data.ons_try}")
            
            # OHLC mumları al
            candles_15m = self.storage.generate_candles(15, 100)
            
            if len(candles_15m) < 50:
                self.logger.debug(f"Not enough candles: {len(candles_15m)}")
                return
            
            # Sinyal üret
            signal = self.signal_generator.generate_signal(
                price_data,
                candles_15m,
                settings.risk_tolerance
            )
            
            if signal:
                self.stats["signals_generated"] += 1
                self._display_signal(signal, price_data)
                self._save_signal_to_file(signal, price_data)
                
        except Exception as e:
            self.error_count += 1
            self.stats["errors_caught"] += 1
            log_exception(self.logger, e, "Price analysis")
    
    def _display_signal(self, signal, price_data):
        """Sinyali göster ve logla"""
        signal_type = "🟢 ALIŞ" if signal.signal_type.value == "BUY" else "🔴 SATIŞ"
        
        signal_info = (
            f"\n{'='*60}\n"
            f"⚡ {signal_type} SİNYALİ ⚡\n"
            f"{'='*60}\n"
            f"📅 Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💰 Fiyat: {price_data.ons_try:.2f} TRY\n"
            f"📊 USD/TRY: {price_data.usd_try:.4f}\n"
            f"🎯 Hedef: {signal.target_price:.2f} TRY\n"
            f"🛑 Stop Loss: {signal.stop_loss:.2f} TRY\n"
            f"📈 Güven: %{signal.overall_confidence*100:.0f}\n"
            f"⚠️  Risk: {signal.risk_level.value}\n"
            f"📝 Sebepler: {', '.join(signal.reasons)}\n"
            f"{'='*60}\n"
        )
        
        print(signal_info)
        self.logger.info(f"Signal generated: {signal.signal_type.value} at {price_data.ons_try}")
    
    def _save_signal_to_file(self, signal, price_data):
        """Sinyalleri dosyaya kaydet"""
        try:
            os.makedirs("signals", exist_ok=True)
            
            signal_file = f"signals/signals_{datetime.now().strftime('%Y%m%d')}.log"
            
            with open(signal_file, "a", encoding="utf-8") as f:
                f.write(f"\n{datetime.now().isoformat()}")
                f.write(f"\nType: {signal.signal_type.value}")
                f.write(f"\nPrice: {price_data.ons_try}")
                f.write(f"\nConfidence: {signal.overall_confidence}")
                f.write(f"\nTarget: {signal.target_price}")
                f.write(f"\nStop: {signal.stop_loss}")
                f.write(f"\nReasons: {signal.reasons}")
                f.write(f"\n{'-'*50}\n")
                
        except Exception as e:
            self.logger.error(f"Failed to save signal: {e}")
    
    async def show_statistics(self):
        """Periyodik istatistik gösterimi ve sağlık kontrolü"""
        while self.running:
            await asyncio.sleep(300)  # 5 dakika
            
            try:
                uptime = datetime.now() - self.stats["start_time"]
                db_stats = self.storage.get_statistics()
                
                stats_info = (
                    f"\n📊 SİSTEM İSTATİSTİKLERİ\n"
                    f"{'─'*40}\n"
                    f"⏱️  Çalışma Süresi: {uptime}\n"
                    f"🔄 Yeniden Başlatma: {self.stats['restarts']}\n"
                    f"📍 Toplam Güncelleme: {self.stats['total_price_updates']}\n"
                    f"📢 Üretilen Sinyal: {self.stats['signals_generated']}\n"
                    f"❌ Yakalanan Hata: {self.stats['errors_caught']}\n"
                    f"💾 DB Kayıt Sayısı: {db_stats.get('total_records', 0)}\n"
                    f"⏰ Son Güncelleme: {self.stats['last_price_update']}\n"
                    f"{'─'*40}\n"
                )
                
                print(stats_info)
                self.logger.info("Statistics displayed")
                
                # Sağlık kontrolü
                if self.stats["last_price_update"]:
                    time_since_update = datetime.now() - self.stats["last_price_update"]
                    if time_since_update > timedelta(minutes=5):
                        self.logger.warning(f"No price update for {time_since_update}")
                        
            except Exception as e:
                self.logger.error(f"Statistics error: {e}")
    
    async def cleanup_old_data(self):
        """Periyodik veri temizliği"""
        while self.running:
            await asyncio.sleep(86400)  # 24 saat
            
            try:
                self.logger.info("Running daily cleanup...")
                self.storage.cleanup_old_data(days_to_keep=30)
                
                # Eski log dosyalarını temizle
                self._cleanup_old_logs()
                
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")
    
    def _cleanup_old_logs(self):
        """30 günden eski log dosyalarını sil"""
        try:
            cutoff = datetime.now() - timedelta(days=30)
            
            for log_dir in ["logs", "signals"]:
                if not os.path.exists(log_dir):
                    continue
                    
                for file in os.listdir(log_dir):
                    file_path = os.path.join(log_dir, file)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_time < cutoff:
                        os.remove(file_path)
                        self.logger.info(f"Deleted old file: {file}")
                        
        except Exception as e:
            self.logger.error(f"Log cleanup error: {e}")
    
    async def start(self):
        """Sistemi başlat"""
        self.running = True
        self.logger.info("="*60)
        self.logger.info("GOLD PRICE ANALYZER - ROBUST VERSION")
        self.logger.info("="*60)
        
        if not self.initialize_services():
            self.logger.error("Failed to initialize services")
            return
        
        # Callback ekle
        self.collector.add_analysis_callback(self.analyze_price_safe)
        
        # Collector'ı başlat
        await self.collector.start()
        
        # Background task'ları başlat
        asyncio.create_task(self.show_statistics())
        asyncio.create_task(self.cleanup_old_data())
        
        self.logger.info("System started successfully")
        
        print(f"\n{'='*60}")
        print("🏆 ALTIN FİYAT ANALİZ SİSTEMİ - ROBUST 🏆")
        print(f"{'='*60}")
        print(f"✅ Sistem başlatıldı")
        print(f"📊 Log dosyası: logs/gold_analyzer.log")
        print(f"🚨 Hata dosyası: logs/gold_analyzer_errors.log")
        print(f"📍 Sinyal dosyası: signals/signals_YYYYMMDD.log")
        print(f"{'='*60}\n")
    
    async def stop(self):
        """Sistemi durdur"""
        self.running = False
        self.logger.info("Stopping system...")
        
        try:
            if self.collector:
                await self.collector.stop()
            if self.harem_service:
                await self.harem_service.stop()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            
        self.logger.info("System stopped")
    
    async def run_with_restart(self):
        """Auto-restart ile çalıştır"""
        while self.restart_count < self.max_restarts:
            try:
                await self.start()
                
                # Ana döngü
                while self.running:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                self.restart_count += 1
                log_exception(self.logger, e, f"Main loop (restart #{self.restart_count})")
                
                if self.restart_count >= self.max_restarts:
                    self.logger.critical(f"Max restarts ({self.max_restarts}) reached. Exiting.")
                    break
                
                self.logger.warning(f"Restarting in 30 seconds... (attempt {self.restart_count}/{self.max_restarts})")
                await asyncio.sleep(30)
                
                # Servisleri yeniden başlat
                self.stats["restarts"] += 1
                continue
                
            finally:
                await self.stop()


async def main():
    """Ana fonksiyon"""
    analyzer = RobustGoldPriceAnalyzer()
    
    # Signal handler
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        analyzer.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await analyzer.run_with_restart()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}\n{traceback.format_exc()}")
    finally:
        await analyzer.stop()


if __name__ == "__main__":
    asyncio.run(main())