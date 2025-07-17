"""
Farklı zaman dilimleri için analiz yöneticisi
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable
import logging
from config import settings
from models.price_data import PriceData

logger = logging.getLogger(__name__)


class TimeframeAnalyzer:
    """Farklı zaman dilimlerinde analiz yapar"""
    
    def __init__(self, analyze_callback: Callable):
        """
        Args:
            analyze_callback: Analiz fonksiyonu (price_data, timeframe, candle_minutes)
        """
        self.analyze_callback = analyze_callback
        self.last_analysis_times: Dict[str, datetime] = {
            "15m": datetime.min,
            "1h": datetime.min,
            "4h": datetime.min,
            "1d": datetime.min
        }
        
        # Zaman dilimi ayarları (dakika cinsinden)
        self.timeframe_configs = {
            "15m": {
                "interval": settings.analysis_interval_15m,
                "candle_minutes": 15,
                "min_candles": 50
            },
            "1h": {
                "interval": settings.analysis_interval_1h,
                "candle_minutes": 60,
                "min_candles": 50
            },
            "4h": {
                "interval": settings.analysis_interval_4h,
                "candle_minutes": 240,
                "min_candles": 35
            },
            "1d": {
                "interval": settings.analysis_interval_daily,
                "candle_minutes": 1440,
                "min_candles": 26
            }
        }
        
        self.running = False
        self.tasks = []
    
    async def process_price_update(self, price_data: PriceData):
        """Fiyat güncellemesini işle ve gerekli analizleri tetikle"""
        current_time = datetime.now()
        
        for timeframe, config in self.timeframe_configs.items():
            # Bu zaman dilimi için analiz zamanı geldi mi?
            time_since_last = (current_time - self.last_analysis_times[timeframe]).total_seconds() / 60
            
            if time_since_last >= config["interval"]:
                # Analizi asenkron olarak başlat
                asyncio.create_task(self._run_analysis(price_data, timeframe, config))
                self.last_analysis_times[timeframe] = current_time
    
    async def _run_analysis(self, price_data: PriceData, timeframe: str, config: dict):
        """Belirli bir zaman dilimi için analiz yap"""
        try:
            logger.info(f"Running {timeframe} analysis at price {price_data.ons_try}")
            
            # Analiz callback'ini çağır
            await self.analyze_callback(
                price_data,
                timeframe=timeframe,
                candle_minutes=config["candle_minutes"]
            )
            
        except Exception as e:
            logger.error(f"Error in {timeframe} analysis: {e}", exc_info=True)
    
    async def start_scheduled_analyses(self):
        """Zamanlanmış analizleri başlat"""
        self.running = True
        
        # Her zaman dilimi için ayrı task başlat
        for timeframe, config in self.timeframe_configs.items():
            task = asyncio.create_task(self._run_scheduled_analysis(timeframe, config))
            self.tasks.append(task)
        
        logger.info("Scheduled analyses started for all timeframes")
    
    async def _run_scheduled_analysis(self, timeframe: str, config: dict):
        """Belirli bir zaman dilimi için zamanlanmış analiz döngüsü"""
        while self.running:
            try:
                # Bir sonraki analiz zamanını bekle
                await asyncio.sleep(config["interval"] * 60)  # Dakikadan saniyeye çevir
                
                # En son fiyatı al ve analiz yap
                # Bu kısım main'de halledilecek
                logger.debug(f"Scheduled {timeframe} analysis triggered")
                
            except Exception as e:
                logger.error(f"Error in scheduled {timeframe} analysis: {e}")
                await asyncio.sleep(60)  # Hata durumunda 1 dakika bekle
    
    def stop(self):
        """Tüm analizleri durdur"""
        self.running = False
        
        # Tüm task'ları iptal et
        for task in self.tasks:
            task.cancel()
        
        logger.info("Timeframe analyzer stopped")
    
    def get_analysis_status(self) -> Dict[str, dict]:
        """Analiz durumunu döndür"""
        current_time = datetime.now()
        status = {}
        
        for timeframe, config in self.timeframe_configs.items():
            last_analysis = self.last_analysis_times[timeframe]
            time_since_last = (current_time - last_analysis).total_seconds() / 60 if last_analysis != datetime.min else float('inf')
            
            status[timeframe] = {
                "last_analysis": last_analysis.isoformat() if last_analysis != datetime.min else None,
                "minutes_since_last": round(time_since_last, 1),
                "next_analysis_in": max(0, config["interval"] - time_since_last),
                "interval": config["interval"]
            }
        
        return status