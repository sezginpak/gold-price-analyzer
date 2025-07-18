#!/usr/bin/env python3
"""Test gram altın analizörü"""
from analyzers.gram_altin_analyzer import GramAltinAnalyzer
from models.market_data import GramAltinCandle
from datetime import datetime
from decimal import Decimal
import random

# Test mumları oluştur
candles = []
base_price = 4340

print("Test mumları oluşturuluyor...")

# Yükseliş trendi
for i in range(30):
    price = base_price + (i * 2)  # Her mumda 2 TL artış
    candle = GramAltinCandle(
        timestamp=datetime.now(),
        open=Decimal(str(price)),
        high=Decimal(str(price + 5)),
        low=Decimal(str(price - 2)),
        close=Decimal(str(price + 3)),
        interval='15m'
    )
    candles.append(candle)

analyzer = GramAltinAnalyzer()
result = analyzer.analyze(candles)

print("\n=== YÜKSELIŞ TRENDİ ===")
print(f"Signal: {result.get('signal')}")
print(f"Confidence: {result.get('confidence'):.3f}")
print(f"Trend: {result.get('trend')}")
print(f"Trend Strength: {result.get('trend_strength')}")

# Düşüş trendi
candles2 = []
base_price = 4400
for i in range(30):
    price = base_price - (i * 2)  # Her mumda 2 TL düşüş
    candle = GramAltinCandle(
        timestamp=datetime.now(),
        open=Decimal(str(price)),
        high=Decimal(str(price + 2)),
        low=Decimal(str(price - 5)),
        close=Decimal(str(price - 3)),
        interval='15m'
    )
    candles2.append(candle)

result2 = analyzer.analyze(candles2)

print("\n=== DÜŞÜŞ TRENDİ ===")
print(f"Signal: {result2.get('signal')}")
print(f"Confidence: {result2.get('confidence'):.3f}")
print(f"Trend: {result2.get('trend')}")
print(f"Trend Strength: {result2.get('trend_strength')}")