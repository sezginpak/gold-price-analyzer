#!/usr/bin/env python3
"""Sinyal üretimini debug et"""
from storage.sqlite_storage import SQLiteStorage
from analyzers.gram_altin_analyzer import GramAltinAnalyzer
from models.market_data import GramAltinCandle
from datetime import datetime
from decimal import Decimal

storage = SQLiteStorage('gold_prices.db')
analyzer = GramAltinAnalyzer()

# Mum verilerini al
candles = storage.generate_candles(15, 30)
print(f"Mum sayısı: {len(candles)}")

if candles:
    # Model formatına çevir
    gram_candles = []
    for c in candles:
        gram_candles.append(GramAltinCandle(
            timestamp=c.timestamp,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            interval='15m'
        ))
    
    # Analiz yap
    result = analyzer.analyze(gram_candles)
    
    print(f"\nAnaliz Sonucu:")
    print(f"Fiyat: {result.get('price')}")
    print(f"Sinyal: {result.get('signal')}")
    print(f"Güven: {result.get('confidence')}")
    
    # Gösterge detayları
    indicators = result.get('indicators', {})
    print(f"\nGöstergeler:")
    print(f"RSI: {indicators.get('rsi')} - {indicators.get('rsi_signal')}")
    print(f"MACD: {indicators.get('macd', {}).get('signal')}")
    print(f"Bollinger: {indicators.get('bollinger', {}).get('position')}")
    print(f"Stochastic: {indicators.get('stochastic', {}).get('signal')}")