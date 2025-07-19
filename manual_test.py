#!/usr/bin/env python3
from storage.sqlite_storage import SQLiteStorage
from strategies.hybrid_strategy import HybridStrategy
from datetime import datetime

storage = SQLiteStorage('gold_prices.db')
strategy = HybridStrategy()

# Market data
market_data = storage.get_latest_prices(100)
print(f'Market data: {len(market_data)} kayıt')

# Gram candles
gram_candles = storage.generate_candles(interval_minutes=15, limit=50)
print(f'Gram candles: {len(gram_candles)} mum')

if gram_candles and market_data:
    result = strategy.analyze(gram_candles, market_data)
    print(f'\nAnaliz Sonucu:')
    print(f'Fiyat: ₺{result["gram_price"]}')
    print(f'Güven: {result["confidence"]*100:.1f}%')
    print(f'Pozisyon: {result["position_size"]["recommended_size"]*100:.0f}%')
    print(f'Sinyal: {result["signal"]}')
    
    # Detaylı bilgi
    gram = result.get('gram_analysis', {})
    if gram:
        print(f'\nGram Analiz Detayı:')
        print(f'Trend: {gram.get("trend")}')
        print(f'RSI: {gram.get("indicators", {}).get("rsi")}')