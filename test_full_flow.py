#!/usr/bin/env python3
"""
Full flow testi - Signal combiner'dan database'e kadar
"""
import sys
sys.path.insert(0, '.')

from strategies.hybrid_strategy import HybridStrategy
from storage.sqlite_storage import SQLiteStorage
from datetime import datetime, timedelta
import json

print("=== FULL FLOW TEST ===\n")

# 1. Storage'dan veri al
storage = SQLiteStorage()
end_time = datetime.now()
start_time = end_time - timedelta(hours=2)

# Mum verilerini al
candles = list(storage.generate_candles('GRAM_ALTIN', '15m'))
recent_candles = candles[-100:] if len(candles) >= 100 else candles

print(f"✅ {len(recent_candles)} mum hazır")

# 2. Market data hazırla
market_data = {
    'gram_candles': recent_candles,
    'ons_candles': recent_candles,  # Mock
    'usd_try_candles': recent_candles  # Mock
}

# 3. Strategy çalıştır
strategy = HybridStrategy()
result = strategy.analyze(market_data, '15m')

print(f"\n📊 STRATEGY RESULT:")
print(f"Signal: {result['signal']}")
print(f"Confidence: {result['confidence']:.3f}")
print(f"Strength: {result['signal_strength']}")

# 4. Gram analysis kontrolü
gram_analysis = result.get('gram_analysis', {})
print(f"\n📊 GRAM ANALYSIS:")
print(f"Signal: {gram_analysis.get('signal')}")
print(f"Confidence: {gram_analysis.get('confidence', 0):.3f}")

# 5. Veritabanına kaydedilen son veriyi kontrol et
import sqlite3
conn = sqlite3.connect('gold_prices.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT 
        signal,
        confidence,
        json_extract(gram_analysis, '$.signal') as gram_signal,
        json_extract(gram_analysis, '$.confidence') as gram_conf
    FROM hybrid_analysis 
    WHERE timeframe = '15m'
    ORDER BY timestamp DESC 
    LIMIT 1
''')

db_result = cursor.fetchone()
if db_result:
    print(f"\n📊 DATABASE LAST RECORD:")
    print(f"Signal: {db_result[0]}")
    print(f"Confidence: {db_result[1]:.3f}")
    print(f"Gram Signal: {db_result[2]}")
    print(f"Gram Conf: {db_result[3]:.3f}")

conn.close()

print("\n💡 ANALYSIS:")
if result['signal'] != db_result[0]:
    print("❌ PROBLEM: Strategy result doesn't match database!")
else:
    print("✅ Strategy result matches database")