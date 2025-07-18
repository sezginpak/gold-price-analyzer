#!/usr/bin/env python3
"""Test gram altın analizörü - dinamik güven testi"""
from analyzers.gram_altin_analyzer import GramAltinAnalyzer
from models.market_data import GramAltinCandle
from datetime import datetime
from decimal import Decimal
import random

analyzer = GramAltinAnalyzer()

# Farklı senaryolar test et
scenarios = [
    {"name": "Sabit Fiyat", "volatility": 0.001},
    {"name": "Düşük Volatilite", "volatility": 0.005},
    {"name": "Orta Volatilite", "volatility": 0.01},
    {"name": "Yüksek Volatilite", "volatility": 0.02}
]

for scenario in scenarios:
    print(f"\n=== {scenario['name']} (Volatilite: {scenario['volatility']*100:.1f}%) ===")
    
    candles = []
    base_price = 4350
    
    # 30 mum oluştur
    for i in range(30):
        # Rastgele fiyat değişimi
        change = random.uniform(-scenario['volatility'], scenario['volatility'])
        price = base_price * (1 + change)
        
        # OHLC değerleri
        open_price = price + random.uniform(-5, 5)
        high_price = max(open_price, price) + random.uniform(0, 5)
        low_price = min(open_price, price) - random.uniform(0, 5)
        close_price = price
        
        candle = GramAltinCandle(
            timestamp=datetime.now(),
            open=Decimal(str(open_price)),
            high=Decimal(str(high_price)),
            low=Decimal(str(low_price)),
            close=Decimal(str(close_price)),
            interval='15m'
        )
        candles.append(candle)
        
        # Base price'ı güncelle
        base_price = price
    
    # Analiz yap
    result = analyzer.analyze(candles)
    
    print(f"Signal: {result.get('signal')}")
    print(f"Confidence: {result.get('confidence'):.3f}")
    print(f"Price: ₺{result.get('price')}")
    
    # Son 5 fiyat
    last_5_prices = [float(c.close) for c in candles[-5:]]
    price_change = (last_5_prices[-1] - last_5_prices[0]) / last_5_prices[0] * 100
    print(f"Son 5 mum değişimi: %{price_change:.2f}")