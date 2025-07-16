"""
Gold Price Analyzer Demo
"""
import asyncio
import sys
from datetime import datetime
from decimal import Decimal

from services.harem_altin_service import HaremAltinPriceService
from collectors.harem_price_collector import HaremPriceCollector
from analyzers.signal_generator import SignalGenerator
from storage.sqlite_storage import SQLiteStorage
from models.price_data import PriceData


async def demo():
    """Demo uygulama"""
    print("🏆 ALTIN FİYAT ANALİZ SİSTEMİ - DEMO 🏆")
    print("="*60)
    
    # Servisleri başlat
    harem_service = HaremAltinPriceService(refresh_interval=5)
    collector = HaremPriceCollector(harem_service)
    storage = SQLiteStorage()
    signal_generator = SignalGenerator(min_confidence=0.6)
    
    # İstatistikleri göster
    stats = storage.get_statistics()
    print(f"\n📊 Veritabanı İstatistikleri:")
    print(f"Toplam kayıt: {stats['total_records']}")
    if stats['total_records'] > 0:
        print(f"İlk kayıt: {stats['oldest_record']}")
        print(f"Son kayıt: {stats['newest_record']}")
    
    # Analiz callback'i
    async def analyze_callback(price_data: PriceData):
        print(f"\n💰 Yeni Fiyat: {datetime.now().strftime('%H:%M:%S')}")
        print(f"ONS/USD: ${price_data.ons_usd}")
        print(f"USD/TRY: {price_data.usd_try}")
        print(f"ONS/TRY: {price_data.ons_try:.2f} TRY")
        
        # Yeterli veri varsa analiz yap
        candles = storage.generate_candles(15, 50)
        if len(candles) >= 20:
            signal = signal_generator.generate_signal(price_data, candles, "medium")
            if signal:
                print(f"\n🚨 SİNYAL: {signal.signal_type.value}")
                print(f"Güven: %{signal.overall_confidence*100:.0f}")
                print(f"Hedef: {signal.target_price:.2f}")
                print(f"Stop: {signal.stop_loss:.2f}")
    
    # Collector'a callback ekle
    collector.add_analysis_callback(analyze_callback)
    
    # Collector'ı başlat
    await collector.start()
    
    print("\n✅ Sistem başladı. Fiyatlar takip ediliyor...")
    print("Çıkmak için Ctrl+C")
    
    # 2 dakika çalıştır
    try:
        await asyncio.sleep(120)
    except KeyboardInterrupt:
        print("\n⏹️  Durduruluyor...")
    
    await collector.stop()
    await harem_service.stop()
    
    # Son istatistikler
    final_stats = storage.get_statistics()
    print(f"\n📊 Final İstatistikler:")
    print(f"Toplam kayıt: {final_stats['total_records']}")
    if final_stats['average_price']:
        print(f"Ortalama fiyat: {final_stats['average_price']:.2f} TRY")


if __name__ == "__main__":
    asyncio.run(demo())