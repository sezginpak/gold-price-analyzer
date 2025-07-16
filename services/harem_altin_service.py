# -*- coding: utf-8 -*-
"""
Canli altin/doviz fiyatlari icin REST API servisi
HaremAltin'dan canli fiyat verilerini JSON API ile alir

Bu dosya JavaScript kodundaki AJAX cagrilarini Python'a cevirir:
- https://canlipiyasalar.haremaltin.com/tmp/altin.json?dil_kodu=tr
- Basit HTTP JSON API
- Periyodik fiyat guncellemeleri
"""

import json
import time
import asyncio
import logging
import signal
import sys
import os
from typing import Dict, Optional, Any, Callable
from datetime import datetime, timedelta

import aiohttp
import ssl

# Logging ayarlari - sadece uyarı ve hata mesajları
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class HaremAltinPriceService:
    """HaremAltin canli fiyat servisi - REST API tabanli"""
    
    _instance = None
    
    def __new__(cls, refresh_interval: int = 3):
        if cls._instance is None:
            cls._instance = super(HaremAltinPriceService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, refresh_interval: int = 3):
        """
        Args:
            refresh_interval: Saniye cinsinden guncelleme araligi (varsayilan: 3 saniye)
        """
        if self._initialized:
            return
            
        self._initialized = True
        self.api_url = "https://canlipiyasalar.haremaltin.com/tmp/altin.json"
        self.refresh_interval = refresh_interval
        self.is_running = False
        self.callbacks = []
        self.last_prices = {}
        
        # Cache ayarlari
        self._cached_prices = {}
        self._last_update = None
        self._cache_duration = 300  # 5 dakika cache
        
        # Cache dizini olustur
        os.makedirs("data", exist_ok=True)
        
        # Cache'den yukle
        self._load_from_cache()
        
        # SSL context - sertifika dogrulama olmadan
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Fiyat tanimlari - JavaScript'teki priceDefs'e benzer
        self.price_definitions = {
            "ALTIN": {"label": "Altin", "dp": 3},
            "USDTRY": {"label": "USD/TRY", "dp": 4},
            "EURTRY": {"label": "EUR/TRY", "dp": 4},
            "GBPTRY": {"label": "GBP/TRY", "dp": 3},
            "CEYREK_YENI": {"label": "Yeni Ceyrek", "dp": 3},
            "CEYREK_ESKI": {"label": "Eski Ceyrek", "dp": 3},
            "YARIM_YENI": {"label": "Yeni Yarim", "dp": 3},
            "YARIM_ESKI": {"label": "Eski Yarim", "dp": 3},
            "TEK_YENI": {"label": "Yeni Tam", "dp": 3},
            "TEK_ESKI": {"label": "Eski Tam", "dp": 3},
            "ONS": {"label": "ONS", "dp": 2},
            "GUMUSTRY": {"label": "Gumus", "dp": 0},
        }
        
    def add_callback(self, callback: Callable[[Dict], None]):
        """Fiyat guncellemesi geldiginde cagrilacak callback ekle"""
        self.callbacks.append(callback)
        
    def remove_callback(self, callback: Callable[[Dict], None]):
        """Callback'i kaldir"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    async def fetch_prices(self) -> Optional[Dict]:
        """API'den fiyatlari cek"""
        try:
            params = {"dil_kodu": "tr"}
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(self.api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # API response formati: {"meta": {...}, "data": {...}}
                        if "data" in data:
                            return data["data"]
                        else:
                            logger.warning("API yaniti 'data' field'i icermiyor")
                            return None
                    else:
                        logger.error(f"API istegi basarisiz: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Fiyat cekme hatasi: {e}")
            return None

    def _compare_prices(self, new_prices: Dict) -> Dict:
        """Yeni fiyatlari eskilerle karsilastir ve degisim yonunu belirle"""
        compared_prices = {}
        
        for code, price_data in new_prices.items():
            # Yeni fiyat verisini kopyala
            compared_price = dict(price_data)
            
            # Eski fiyatla karsilastir
            if code in self.last_prices:
                old_data = self.last_prices[code]
                
                # Alis fiyati karsilastirmasi
                if "alis" in compared_price and "alis" in old_data:
                    try:
                        new_alis = float(compared_price["alis"])
                        old_alis = float(old_data["alis"])
                        
                        if new_alis > old_alis:
                            compared_price["alis_direction"] = "up"
                        elif new_alis < old_alis:
                            compared_price["alis_direction"] = "down"
                        else:
                            compared_price["alis_direction"] = "same"
                    except (ValueError, TypeError):
                        compared_price["alis_direction"] = "unknown"
                
                # Satis fiyati karsilastirmasi
                if "satis" in compared_price and "satis" in old_data:
                    try:
                        new_satis = float(compared_price["satis"])
                        old_satis = float(old_data["satis"])
                        
                        if new_satis > old_satis:
                            compared_price["satis_direction"] = "up"
                        elif new_satis < old_satis:
                            compared_price["satis_direction"] = "down"
                        else:
                            compared_price["satis_direction"] = "same"
                    except (ValueError, TypeError):
                        compared_price["satis_direction"] = "unknown"
            else:
                # Ilk kez gorulen fiyat
                compared_price["alis_direction"] = "new"
                compared_price["satis_direction"] = "new"
            
            compared_prices[code] = compared_price
            
        return compared_prices

    async def _notify_callbacks(self, prices: Dict):
        """Callback'leri fiyat guncellemesi ile bilgilendir"""
        # Cache'i guncelle
        self._cached_prices = prices
        self._last_update = datetime.now()
        self._save_to_cache()
        
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(prices)
                else:
                    callback(prices)
            except Exception as e:
                logger.error(f"Callback hatasi: {e}")

    async def start(self):
        """Servisi baslat - periyodik fiyat cekmeye basla"""
        self.is_running = True
        logger.debug(f"Canli fiyat servisi basladi (her {self.refresh_interval} saniyede guncelleme)")
        
        try:
            while self.is_running:
                # Fiyatlari cek
                new_prices = await self.fetch_prices()
                
                if new_prices:
                    # Degisimleri karsilastir
                    compared_prices = self._compare_prices(new_prices)
                    
                    # Callback'leri bilgilendir
                    if compared_prices:
                        logger.debug(f"Fiyat guncellemesi: {len(compared_prices)} urun")
                        await self._notify_callbacks(compared_prices)
                    
                    # Son fiyatlari guncelle
                    self.last_prices = new_prices
                else:
                    # Bu mesajı da debug seviyesine çevirelim, çok sık tekrar ediyor
                    logger.debug("Fiyat verisi alinamadi")
                
                # Bekleme
                await asyncio.sleep(self.refresh_interval)
                
        except asyncio.CancelledError:
            logger.debug("Servis durduruldu")
        except Exception as e:
            logger.error(f"Servis hatasi: {e}")
        finally:
            self.is_running = False

    async def stop(self):
        """Servisi durdur"""
        self.is_running = False
        logger.debug("Servis durdurma sinyali gonderildi")

    async def get_current_prices(self) -> Optional[Dict]:
        """Anlık fiyatlari tek seferlik al"""
        return await self.fetch_prices()
    
    # Cache ve helper metodlari
    def get_last_price(self) -> float:
        """Son altin satis fiyatini dondurur (sync)"""
        try:
            if self._is_cache_valid():
                altin_data = self._cached_prices.get("ALTIN")
                if altin_data and "satis" in altin_data:
                    try:
                        return float(altin_data["satis"])
                    except (ValueError, TypeError):
                        pass
            return self._get_fallback_price("satis")
        except Exception as e:
            logger.error(f"Son satis fiyati alma hatasi: {e}")
            return self._get_fallback_price("satis")
    
    def get_last_buy_price(self) -> float:
        """Son altin alis fiyatini dondurur (sync)"""
        try:
            if self._is_cache_valid():
                altin_data = self._cached_prices.get("ALTIN")
                if altin_data and "alis" in altin_data:
                    try:
                        return float(altin_data["alis"])
                    except (ValueError, TypeError):
                        pass
            return self._get_fallback_price("alis")
        except Exception as e:
            logger.error(f"Son alis fiyati alma hatasi: {e}")
            return self._get_fallback_price("alis")
    
    def get_exchange_rate(self, currency_pair: str) -> Optional[float]:
        """Doviz kuru dondurur (USD/TRY, EUR/TRY vb)"""
        try:
            if self._is_cache_valid():
                pair_data = self._cached_prices.get(currency_pair.upper())
                if pair_data and "satis" in pair_data:
                    try:
                        return float(pair_data["satis"])
                    except (ValueError, TypeError):
                        logger.warning(f"Gecersiz doviz kuru: {pair_data['satis']}")
            
            # Fallback degerler
            fallback_rates = {
                "USDTRY": 30.0,
                "EURTRY": 32.0,
                "GBPTRY": 38.0
            }
            
            fallback = fallback_rates.get(currency_pair.upper())
            if fallback:
                logger.warning(f"Doviz kuru cache'den alinamadi, fallback kullaniliyor: {currency_pair} = {fallback}")
                return fallback
                
            return None
        except Exception as e:
            logger.error(f"Doviz kuru alma hatasi ({currency_pair}): {e}")
            return None
    
    def get_all_prices(self) -> Dict[str, float]:
        """Hem alis hem satis fiyatlarini birlikte dondurur"""
        return {
            "satis": self.get_last_price(),
            "alis": self.get_last_buy_price()
        }
    
    def get_all_cached_prices(self) -> Dict[str, Any]:
        """Tum onbellekli fiyatlari dondurur"""
        if self._is_cache_valid():
            return self._cached_prices.copy()
        else:
            logger.warning("Cache gecersiz, bos dict donduruluyor")
            return {}
    
    def get_price_info(self) -> Dict[str, Any]:
        """Tum fiyat bilgilerini ve metadata dondurur"""
        all_prices = self.get_all_prices()
        
        return {
            "prices": all_prices,
            "metadata": {
                "last_update": self._last_update.isoformat() if self._last_update else None,
                "cache_valid": self._is_cache_valid(),
                "service_running": self.is_running,
                "total_products": len(self._cached_prices)
            }
        }
    
    def _is_cache_valid(self) -> bool:
        """Cache'in gecerli olup olmadigini kontrol eder"""
        if not self._last_update or not self._cached_prices:
            return False
        
        age = datetime.now() - self._last_update
        return age.total_seconds() < self._cache_duration
    
    def _get_fallback_price(self, price_type: str) -> float:
        """Fallback fiyat degerleri dondurur"""
        fallback_values = {
            "satis": 4200.0,  # Varsayilan altin satis fiyati
            "alis": 4150.0    # Varsayilan altin alis fiyati  
        }
        
        fallback = fallback_values.get(price_type, 4000.0)
        logger.warning(f"Fallback fiyat kullaniliyor: {price_type} = {fallback}")
        return fallback
    
    def _save_to_cache(self) -> None:
        """Tum fiyatlari onbellige kaydeder"""
        try:
            os.makedirs("data", exist_ok=True)
            cache_data = {
                'prices': self._cached_prices,
                'last_update': self._last_update.isoformat() if self._last_update else None
            }
            with open('data/gold_price_cache.json', 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Onbellek kaydetme hatasi: {str(e)}")
    
    def _load_from_cache(self) -> None:
        """Fiyatlari onbellekten yukler"""
        try:
            cache_file = 'data/gold_price_cache.json'
            if not os.path.exists(cache_file):
                logger.debug("Onbellek dosyasi bulunamadi")
                return
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            self._cached_prices = cache_data.get('prices', {})
            update_time = cache_data.get('last_update')
            
            if update_time:
                self._last_update = datetime.fromisoformat(update_time)
                
            logger.debug(f"Onbellek yuklendi: {len(self._cached_prices)} urun, son guncelleme: {self._last_update}")
            
        except Exception as e:
            logger.error(f"Onbellek okuma hatasi: {str(e)}")
            self._cached_prices = {}
            self._last_update = None

# Ornek kullanim ve test fonksiyonlari
async def price_callback(prices: Dict):
    """Ornek callback - gelen fiyatlari logla"""
    print(f"\n📊 Fiyat guncellemesi: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 50)
    
    # Onemli fiyatlari goster
    important_codes = ["ALTIN", "USDTRY", "EURTRY", "ONS", "CEYREK_YENI", "YARIM_YENI"]
    
    for code in important_codes:
        if code in prices:
            price_data = prices[code]
            alis = price_data.get("alis", "N/A")
            satis = price_data.get("satis", "N/A")
            alis_dir = price_data.get("alis_direction", "")
            satis_dir = price_data.get("satis_direction", "")
            
            # Yön oklarini goster
            alis_arrow = "↑" if alis_dir == "up" else "↓" if alis_dir == "down" else ""
            satis_arrow = "↑" if satis_dir == "up" else "↓" if satis_dir == "down" else ""
            
            print(f"{code:12} | Alış: {alis:>8} {alis_arrow} | Satış: {satis:>8} {satis_arrow}")

async def main():
    """Ana test fonksiyonu"""
    service = HaremAltinPriceService(refresh_interval=5)  # 5 saniyede bir guncelle
    
    # Callback ekle
    service.add_callback(price_callback)
    
    # Signal handler - Ctrl+C ile temiz kapanis
    def signal_handler(signum, frame):
        logger.debug("Kapatma sinyali alindi")
        asyncio.create_task(service.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Servisi baslat
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.debug("Kullanici tarafindan durduruldu")
    finally:
        await service.stop()

# Service provider fonksiyonu
def get_price_service() -> HaremAltinPriceService:
    """
    FastAPI icin bagimlilik enjeksiyonu ile HaremAltinPriceService ornegi saglar.
    
    Returns:
        HaremAltinPriceService: Servis ornegi
    """
    return HaremAltinPriceService()

# Global instance
price_service = HaremAltinPriceService()

if __name__ == "__main__":
    asyncio.run(main())