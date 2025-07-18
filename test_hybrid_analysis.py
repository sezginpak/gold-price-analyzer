#!/usr/bin/env python3
"""Hibrit analiz test scripti"""
import asyncio
from datetime import datetime, timedelta
from storage.sqlite_storage import SQLiteStorage
from strategies.hybrid_strategy import HybridStrategy
from decimal import Decimal

async def test_analysis():
    """Son analizleri karşılaştır"""
    storage = SQLiteStorage("gold_prices.db")
    strategy = HybridStrategy()
    
    # Son 5 analizi al
    recent_analyses = storage.get_analysis_history(limit=5)
    
    print("\n=== SON 5 ANALİZ ===")
    print(f"{'Zaman':<20} {'Fiyat':<12} {'Sinyal':<10} {'Güven':<8} {'Pozisyon':<10}")
    print("-" * 70)
    
    for analysis in recent_analyses:
        time_str = analysis.timestamp.strftime("%H:%M:%S")
        price = f"₺{analysis.gram_price:.2f}" if analysis.gram_price else "₺0.00"
        signal = analysis.signal
        confidence = f"%{int(analysis.confidence * 100)}"
        position = f"%{int(analysis.position_size * 100)}"
        
        print(f"{time_str:<20} {price:<12} {signal:<10} {confidence:<8} {position:<10}")
    
    # Şimdi yeni bir analiz yap
    print("\n=== YENİ ANALİZ YAPALIM ===")
    
    # Market verilerini al
    market_data = storage.get_latest_prices(limit=100)
    print(f"Market veri sayısı: {len(market_data)}")
    
    # Gram altın mumlarını oluştur
    gram_candles = []
    if market_data:
        gram_candles = storage.generate_candles(
            symbol="gram_altin",
            interval="15m", 
            limit=50
        )
    print(f"Gram altın mum sayısı: {len(gram_candles)}")
    
    if gram_candles and market_data:
        # Analiz yap
        result = strategy.analyze(gram_candles, market_data)
        
        print(f"\nYeni Analiz Sonucu:")
        print(f"Fiyat: ₺{result['gram_price']}")
        print(f"Sinyal: {result['signal']}")
        print(f"Güven: %{result['confidence']*100:.1f}")
        print(f"Pozisyon: %{result['position_size']['recommended_size']*100:.0f}")
        print(f"Özet: {result['summary']}")
        
        # Detaylı gösterge bilgileri
        gram = result.get('gram_analysis', {})
        indicators = gram.get('indicators', {})
        
        print(f"\nGösterge Detayları:")
        print(f"RSI: {indicators.get('rsi', 'N/A')}")
        print(f"MACD Sinyal: {indicators.get('macd', {}).get('signal', 'N/A')}")
        print(f"Bollinger Pozisyon: {indicators.get('bollinger', {}).get('position', 'N/A')}")
        print(f"Stochastic: {indicators.get('stochastic', {}).get('signal', 'N/A')}")
        
    storage.close()

if __name__ == "__main__":
    asyncio.run(test_analysis())