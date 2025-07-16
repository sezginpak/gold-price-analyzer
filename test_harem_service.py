"""
HaremAltin servisi testi
"""
import asyncio
import logging
from datetime import datetime
from services.harem_altin_service import HaremAltinPriceService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_price_callback(prices):
    """Test callback"""
    print(f"\n📊 Fiyat Güncellemesi - {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 60)
    
    # Önemli fiyatları göster
    if "ALTIN" in prices:
        altin = prices["ALTIN"]
        print(f"ALTIN: Alış: {altin.get('alis', 'N/A')} | Satış: {altin.get('satis', 'N/A')}")
    
    if "USDTRY" in prices:
        usd = prices["USDTRY"]
        print(f"USD/TRY: {usd.get('satis', 'N/A')}")
        
    if "ONS" in prices:
        ons = prices["ONS"]
        print(f"ONS: {ons.get('satis', 'N/A')} USD")
        
        # ONS/TRY hesapla
        if "USDTRY" in prices:
            try:
                ons_usd = float(ons.get('satis', 0))
                usd_try = float(prices["USDTRY"].get('satis', 0))
                ons_try = ons_usd * usd_try
                print(f"ONS/TRY: {ons_try:.2f} TRY (Hesaplanan)")
            except:
                pass


async def test_service():
    """Test HaremAltin service"""
    print("🧪 HaremAltin Servis Testi Başlıyor...")
    
    service = HaremAltinPriceService(refresh_interval=5)
    service.add_callback(test_price_callback)
    
    # İlk fiyatları çek
    print("\n📡 İlk fiyatlar çekiliyor...")
    prices = await service.get_current_prices()
    
    if prices:
        print(f"✅ {len(prices)} ürün fiyatı alındı")
        await test_price_callback(prices)
    else:
        print("❌ Fiyat alınamadı!")
        return
    
    # 30 saniye boyunca canlı takip
    print("\n🔄 Canlı takip başlıyor (30 saniye)...")
    
    # Servisi arka planda başlat
    service_task = asyncio.create_task(service.start())
    
    # 30 saniye bekle
    await asyncio.sleep(30)
    
    # Servisi durdur
    await service.stop()
    service_task.cancel()
    
    print("\n✅ Test tamamlandı!")


if __name__ == "__main__":
    asyncio.run(test_service())