#!/usr/bin/env python3
"""
Dip Detection Sistemi Test Script
"""
import asyncio
import logging
from datetime import datetime, timedelta
from storage.sqlite_storage import SQLiteStorage
from strategies.hybrid_strategy import HybridStrategy
from models.market_data import MarketData
from utils import timezone

# Logging ayarla
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_dip_detection():
    """Dip detection sistemini test et"""
    try:
        # Storage başlat
        storage = SQLiteStorage()
        
        # Strateji başlat
        strategy = HybridStrategy(storage)
        
        # Son verileri al
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=4)
        
        # Farklı timeframe'lerde test et
        timeframes = ["15m", "1h", "4h"]
        
        print("\n" + "="*80)
        print("DIP DETECTION SİSTEMİ TEST SONUÇLARI")
        print("="*80 + "\n")
        
        for timeframe in timeframes:
            print(f"\n📊 TIMEFRAME: {timeframe}")
            print("-" * 50)
            
            # Timeframe'e göre interval belirle
            interval_map = {
                "15m": 15,
                "1h": 60,
                "4h": 240,
                "1d": 1440
            }
            interval_minutes = interval_map.get(timeframe, 15)
            required_candles = 100
            
            # Gram altın mumlarını oluştur
            gram_candles = storage.generate_candles(interval_minutes, required_candles)
            
            # Market verilerini simüle et (son fiyatları al)
            latest_prices = storage.get_latest_prices(limit=100)
            market_data = []
            for price in latest_prices:
                if price.ons_usd or price.usd_try:
                    # MarketData objesine dönüştür
                    market_data.append(MarketData(
                        timestamp=price.timestamp,
                        gram_altin=float(price.gram_altin) if price.gram_altin else float(price.ons_try) / 31.1035,
                        ons_usd=float(price.ons_usd) if price.ons_usd else 0,
                        usd_try=float(price.usd_try) if price.usd_try else 0,
                        ons_try=float(price.ons_try) if hasattr(price, 'ons_try') and price.ons_try else 0,
                        source=price.source if hasattr(price, 'source') else "api"
                    ))
            
            if not gram_candles or not market_data:
                print(f"❌ {timeframe} için yeterli veri yok")
                continue
            
            # Analiz yap
            result = strategy.analyze(gram_candles, market_data, timeframe)
            
            # Sonuçları göster
            print(f"📍 Güncel Fiyat: {result.get('gram_price', 0):.2f} TL")
            print(f"📈 Sinyal: {result.get('signal')} ({result.get('signal_strength')})")
            print(f"🎯 Güven Skoru: {result.get('confidence', 0):.2%}")
            
            # Global trend bilgisi
            global_trend = result.get('global_trend', {})
            print(f"🌍 Global Trend: {global_trend.get('trend_direction', 'UNKNOWN')}")
            
            # DIP DETECTION SONUÇLARI
            dip_detection = result.get('dip_detection', {})
            if dip_detection:
                print(f"\n🔍 DIP DETECTION ANALİZİ:")
                print(f"   • Dip Skoru: {dip_detection.get('score', 0):.3f}")
                print(f"   • Dip Fırsatı: {'✅ EVET' if dip_detection.get('is_dip_opportunity') else '❌ HAYIR'}")
                
                if dip_detection.get('signals'):
                    print(f"   • Tespit Edilen Sinyaller:")
                    for sig in dip_detection['signals']:
                        print(f"     - {sig}")
            
            # Pozisyon önerileri
            if result.get('position_size_recommendation'):
                print(f"\n💰 POZİSYON ÖNERİSİ:")
                print(f"   • Boyut: %{result['position_size_recommendation']*100:.0f}")
                if result.get('stop_loss_recommendation'):
                    print(f"   • Stop Loss: {result['stop_loss_recommendation']}")
            
            # Divergence analizi
            divergence = result.get('divergence_analysis', {})
            if divergence.get('divergence_type') != 'NONE':
                print(f"\n📊 DIVERGENCE ANALİZİ:")
                print(f"   • Tip: {divergence.get('divergence_type')}")
                print(f"   • Güç: {divergence.get('strength')}")
                print(f"   • Skor: {divergence.get('total_score')}")
            
            # Momentum analizi
            momentum = result.get('momentum_analysis', {})
            if momentum.get('exhaustion_detected'):
                print(f"\n⚡ MOMENTUM ANALİZİ:")
                print(f"   • Exhaustion Tipi: {momentum.get('exhaustion_type')}")
                print(f"   • Skor: {momentum.get('exhaustion_score', 0):.3f}")
            
            # Smart money analizi
            smart_money = result.get('smart_money_analysis', {})
            if smart_money.get('manipulation_score', 0) > 0.3:
                print(f"\n🏦 SMART MONEY ANALİZİ:")
                print(f"   • Manipulation Skoru: {smart_money.get('manipulation_score', 0):.3f}")
                print(f"   • Yön: {smart_money.get('smart_money_direction')}")
                if smart_money.get('stop_hunt_detected'):
                    print(f"   • ⚠️ Stop Hunt Detected!")
            
            # Öneriler
            recommendations = result.get('recommendations', [])
            if recommendations:
                print(f"\n📝 ÖNERİLER:")
                for rec in recommendations:
                    print(f"   • {rec}")
            
            print("\n" + "-" * 50)
        
        # Storage close metodu yok, connection'ı kapatmaya gerek yok
        print("\n✅ Test tamamlandı!")
        
    except Exception as e:
        logger.error(f"Test hatası: {e}", exc_info=True)
        print(f"\n❌ Test hatası: {e}")

if __name__ == "__main__":
    asyncio.run(test_dip_detection())