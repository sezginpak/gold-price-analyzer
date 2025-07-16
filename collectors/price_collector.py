"""
Fiyat veri toplama servisi
"""
import asyncio
import aiohttp
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
import logging
from models.price_data import PriceData
from config import settings

logger = logging.getLogger(__name__)


class PriceCollector:
    """Fiyat verisi toplama servisi"""
    
    def __init__(self):
        self.api_base_url = settings.api_base_url
        self.api_key = settings.api_key
        self.collection_interval = settings.collection_interval
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_running = False
        
    async def start(self):
        """Servisi başlat"""
        self.session = aiohttp.ClientSession()
        self.is_running = True
        logger.info("Price collector started")
        
    async def stop(self):
        """Servisi durdur"""
        self.is_running = False
        if self.session:
            await self.session.close()
        logger.info("Price collector stopped")
    
    async def fetch_price_data(self) -> Optional[PriceData]:
        """API'den fiyat verisi çek"""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # API endpoint'inizi buraya ekleyin
            url = f"{self.api_base_url}/api/v1/prices/current"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # API response formatınıza göre düzenleyin
                    price_data = PriceData(
                        ons_usd=Decimal(str(data.get("ons_usd", 0))),
                        usd_try=Decimal(str(data.get("usd_try", 0))),
                        ons_try=Decimal(str(data.get("ons_try", 0))),
                        source=data.get("source", "api")
                    )
                    
                    logger.debug(f"Fetched price data: ONS/USD={price_data.ons_usd}, USD/TRY={price_data.usd_try}")
                    return price_data
                else:
                    logger.error(f"API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching price data: {e}")
            return None
    
    async def collect_prices(self, callback=None):
        """Sürekli fiyat toplama döngüsü"""
        while self.is_running:
            try:
                price_data = await self.fetch_price_data()
                
                if price_data and callback:
                    await callback(price_data)
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Collection loop error: {e}")
                await asyncio.sleep(self.collection_interval)


class MockPriceCollector(PriceCollector):
    """Test için mock fiyat üretici"""
    
    def __init__(self):
        super().__init__()
        self.base_ons_usd = Decimal("2050")
        self.base_usd_try = Decimal("38.5")
        self.volatility = Decimal("0.002")  # %0.2 volatilite
    
    async def fetch_price_data(self) -> Optional[PriceData]:
        """Mock fiyat verisi üret"""
        import random
        
        # Rastgele fiyat değişimi
        ons_change = self.base_ons_usd * self.volatility * Decimal(str(random.uniform(-1, 1)))
        usd_change = self.base_usd_try * self.volatility * Decimal(str(random.uniform(-1, 1)))
        
        ons_usd = self.base_ons_usd + ons_change
        usd_try = self.base_usd_try + usd_change
        ons_try = ons_usd * usd_try
        
        # Base fiyatları güncelle (trend simülasyonu)
        self.base_ons_usd += ons_change * Decimal("0.1")
        self.base_usd_try += usd_change * Decimal("0.1")
        
        return PriceData(
            ons_usd=ons_usd.quantize(Decimal("0.01")),
            usd_try=usd_try.quantize(Decimal("0.0001")),
            ons_try=ons_try.quantize(Decimal("0.01")),
            source="mock"
        )