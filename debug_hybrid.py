#!/usr/bin/env python3
"""Hibrit analiz debug script"""
import sys
import logging
from storage.sqlite_storage import SQLiteStorage
from strategies.hybrid_strategy import HybridStrategy
from datetime import datetime, timedelta

# Detaylı logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    storage = SQLiteStorage('gold_prices.db')
    strategy = HybridStrategy()
    
    # Son fiyat verilerini al
    latest_prices = storage.get_latest_prices(100)
    print(f"\n=== SON FİYATLAR ===")
    if latest_prices:
        latest = latest_prices[0]
        print(f"Timestamp: {latest.timestamp}")
        print(f"Gram Altın: ₺{latest.gram_altin}")
        print(f"ONS/USD: ${latest.ons_usd}")
        print(f"USD/TRY: ₺{latest.usd_try}")
        print(f"Toplam Fiyat Kaydı: {len(latest_prices)}")
    else:
        print("Fiyat verisi bulunamadı!")
        return
    
    # Gram mumlarını al
    gram_candles = storage.generate_candles(interval_minutes=15, limit=50)
    print(f"\n=== GRAM MUM VERİLERİ ===")
    print(f"Toplam Mum: {len(gram_candles)}")
    
    if gram_candles:
        latest_candle = gram_candles[-1]
        print(f"Son Mum Timestamp: {latest_candle.timestamp}")
        print(f"Son Mum Close: ₺{latest_candle.close}")
        print(f"Son Mum High: ₺{latest_candle.high}")
        print(f"Son Mum Low: ₺{latest_candle.low}")
        
        # İlk ve son mum fiyatları
        first_close = float(gram_candles[0].close)
        last_close = float(gram_candles[-1].close)
        price_change = ((last_close - first_close) / first_close * 100)
        print(f"Fiyat Değişimi: %{price_change:.2f}")
    else:
        print("Mum verisi bulunamadı!")
        return
    
    # Market data hazırla
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=48)
    market_data = storage.get_price_range(start_time, end_time)
    print(f"\n=== MARKET DATA ===")
    print(f"Toplam Market Data: {len(market_data)}")
    
    if len(market_data) < 50:
        print("Yetersiz market data!")
        return
    
    # Hibrit strateji analizi
    print(f"\n=== HİBRİT ANALİZ ===")
    try:
        result = strategy.analyze(gram_candles, market_data)
        
        print(f"\nANALİZ SONUCU:")
        print(f"Gram Price: ₺{result.get('gram_price', 'NONE')}")
        print(f"Signal: {result.get('signal', 'NONE')}")
        print(f"Confidence: {result.get('confidence', 0)*100:.1f}%")
        print(f"Signal Strength: {result.get('signal_strength', 'NONE')}")
        print(f"Position Size: {result.get('position_size', {}).get('recommended_size', 0)*100:.0f}%")
        
        # Gram analiz detayı
        gram_analysis = result.get('gram_analysis', {})
        if gram_analysis:
            print(f"\nGRAM ANALİZ DETAYI:")
            print(f"Price: ₺{gram_analysis.get('price', 'NONE')}")
            print(f"Trend: {gram_analysis.get('trend', 'NONE')}")
            print(f"Trend Strength: {gram_analysis.get('trend_strength', 'NONE')}")
            print(f"Confidence: {gram_analysis.get('confidence', 0)*100:.1f}%")
            
            indicators = gram_analysis.get('indicators', {})
            if indicators:
                print(f"\nİNDİKATÖRLER:")
                print(f"RSI: {indicators.get('rsi', 'NONE')}")
                print(f"MACD Signal: {indicators.get('macd', {}).get('signal', 'NONE')}")
        else:
            print("\nGram analiz sonucu boş!")
            
    except Exception as e:
        print(f"Hibrit analiz hatası: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()