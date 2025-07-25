#!/usr/bin/env python3
"""
Final sinyal üretimini test et
"""
import sys
sys.path.insert(0, '/root/gold-price-analyzer')

from strategies.hybrid_strategy import HybridStrategy
from storage.sqlite_storage import SQLiteStorage
from datetime import datetime, timedelta

def test_signals():
    print("=== SINYAL ÜRETIM TESTİ ===\n")
    
    storage = SQLiteStorage()
    strategy = HybridStrategy()
    
    # Son verileri al
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=2)
    
    for timeframe in ['15m', '1h']:
        print(f"\n📊 TIMEFRAME: {timeframe}")
        print("-" * 50)
        
        # Mum verilerini al
        candles = storage.generate_candles('GRAM_ALTIN', timeframe, start_time, end_time)
        
        if not candles or len(candles) < 30:
            print(f"❌ Yeterli veri yok: {len(candles) if candles else 0} mum")
            continue
            
        print(f"✅ {len(candles)} mum yüklendi")
        
        # Market data
        market_data = {
            'gram_candles': candles,
            'ons_candles': candles,
            'usd_try_candles': candles
        }
        
        # Analiz
        try:
            result = strategy.analyze(market_data, timeframe)
            
            print(f"\n📈 SONUÇ:")
            print(f"Signal: {result['signal']}")
            print(f"Confidence: {result['confidence']:.2%}")
            print(f"Strength: {result['signal_strength']}")
            
            # Gram analiz detayları
            gram = result.get('gram_analysis', {})
            if gram:
                print(f"\n🔍 GRAM ANALİZ:")
                print(f"Gram Signal: {gram.get('signal')}")
                print(f"Gram Confidence: {gram.get('confidence', 0):.2%}")
                print(f"Trend: {gram.get('trend')}")
                print(f"RSI: {gram.get('indicators', {}).get('rsi', 'N/A')}")
                
        except Exception as e:
            print(f"❌ HATA: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_signals()