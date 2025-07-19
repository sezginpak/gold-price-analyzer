"""
HaremAltin API'den fiyat toplama servisi
"""
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Callable
import logging
from models.price_data import PriceData
from storage.sqlite_storage import SQLiteStorage
from config import settings

logger = logging.getLogger(__name__)


class HaremPriceCollector:
    """HaremAltin API entegrasyonu"""
    
    def __init__(self, harem_service):
        """
        Args:
            harem_service: HaremAltinPriceService instance
        """
        self.harem_service = harem_service
        self.storage = SQLiteStorage()
        self.is_running = False
        self.analysis_callbacks = []
        
    def add_analysis_callback(self, callback: Callable):
        """Analiz için callback ekle"""
        self.analysis_callbacks.append(callback)
        
    async def price_callback(self, prices: Dict[str, Any]):
        """HaremAltin servisinden gelen fiyatları işle"""
        try:
            # Altın ve döviz verilerini al
            altin_data = prices.get("ALTIN", {})
            usd_data = prices.get("USDTRY", {})
            ons_data = prices.get("ONS", {})
            
            # Eksik veri kontrolü
            if not all([altin_data, usd_data, ons_data]):
                logger.warning("Eksik fiyat verisi")
                return
                
            # ONS fiyatını USD cinsinden al
            ons_usd_value = ons_data.get("satis", 0)
            usd_try_value = usd_data.get("satis", 0)
            gram_altin_value = altin_data.get("satis", 0)
            
            # Değerlerin geçerliliğini kontrol et (önce float'a çevir)
            try:
                ons_usd_float = float(ons_usd_value) if ons_usd_value else 0
                usd_try_float = float(usd_try_value) if usd_try_value else 0
                gram_altin_float = float(gram_altin_value) if gram_altin_value else 0
            except (ValueError, TypeError):
                ons_usd_float = usd_try_float = gram_altin_float = 0
                
            if not all([ons_usd_float > 0, usd_try_float > 0, gram_altin_float > 0]):
                logger.warning(f"Geçersiz fiyat verisi: ONS={ons_usd_value}, USD={usd_try_value}, Gram={gram_altin_value}")
                # Son geçerli fiyatı kullan
                last_price = self.storage.get_latest_price()
                if last_price:
                    logger.info("Son geçerli fiyat kullanılıyor")
                    price_data = PriceData(
                        ons_usd=last_price.ons_usd,
                        usd_try=last_price.usd_try,
                        ons_try=last_price.ons_try,
                        gram_altin=last_price.gram_altin,
                        source="haremaltin_cached"
                    )
                    # Analiz callback'lerini çağır ama veritabanına kaydetme
                    for callback in self.analysis_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(price_data)
                            else:
                                callback(price_data)
                        except Exception as e:
                            logger.error(f"Analysis callback error: {e}", exc_info=True)
                return
            
            ons_usd = Decimal(str(ons_usd_value))
            usd_try = Decimal(str(usd_try_value))
            gram_altin = Decimal(str(gram_altin_value))
            
            # ONS/TRY hesapla
            ons_try = ons_usd * usd_try
            
            # PriceData oluştur
            price_data = PriceData(
                ons_usd=ons_usd,
                usd_try=usd_try,
                ons_try=ons_try,
                gram_altin=gram_altin,
                source="haremaltin"
            )
            
            # Veritabanına kaydet
            self.storage.save_price(price_data)
            
            # Analiz callback'lerini çağır
            logger.debug(f"Calling {len(self.analysis_callbacks)} analysis callbacks")
            for callback in self.analysis_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(price_data)
                    else:
                        callback(price_data)
                except Exception as e:
                    logger.error(f"Analysis callback error: {e}", exc_info=True)
                    
            logger.debug(f"Price saved: ONS/USD={ons_usd}, USD/TRY={usd_try}, ONS/TRY={ons_try}")
            
        except Exception as e:
            logger.error(f"Error processing price data: {e}")
    
    async def start(self):
        """Servisi başlat"""
        if self.is_running:
            logger.warning("Collector already running")
            return
            
        self.is_running = True
        
        # HaremAltin servisine callback ekle
        self.harem_service.add_callback(self.price_callback)
        
        # HaremAltin servisini başlat
        if not self.harem_service.is_running:
            logger.info("Starting HaremAltin price service...")
            asyncio.create_task(self.harem_service.start())
        
        logger.info("HaremPriceCollector started")
        
    async def stop(self):
        """Servisi durdur"""
        self.is_running = False
        
        # Callback'i kaldır
        self.harem_service.remove_callback(self.price_callback)
        
        logger.info("HaremPriceCollector stopped")
    
    def get_latest_candles(self, interval_minutes: int, limit: int = 100):
        """Son OHLC mumlarını getir"""
        return self.storage.generate_candles(interval_minutes, limit)
    
    def get_statistics(self):
        """İstatistikleri getir"""
        return self.storage.get_statistics()