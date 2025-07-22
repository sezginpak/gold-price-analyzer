#!/usr/bin/env python3
"""Mum üretimini debug et"""
from storage.sqlite_storage import SQLiteStorage
from datetime import datetime, timedelta
import sqlite3

storage = SQLiteStorage('gold_prices.db')

print("=== MUM ÜRETİM DEBUG ===\n")

# Son 15 dakikanın ham verilerini kontrol et
conn = storage.get_connection()
cursor = conn.cursor()

# Son 15 dakikanın verileri
cursor.execute("""
    SELECT 
        MIN(timestamp) as start_time,
        MAX(timestamp) as end_time,
        COUNT(*) as record_count,
        AVG(gram_altin) as avg_price,
        MIN(gram_altin) as min_price,
        MAX(gram_altin) as max_price
    FROM price_data 
    WHERE timestamp > datetime('now', '-15 minutes')
    AND gram_altin IS NOT NULL
""")
result = cursor.fetchone()
print(f"Son 15 dakika ham veri:")
print(f"  Başlangıç: {result['start_time']}")
print(f"  Bitiş: {result['end_time']}")
print(f"  Kayıt sayısı: {result['record_count']}")
print(f"  Ortalama: {result['avg_price']:.2f}")
print(f"  Min: {result['min_price']}")
print(f"  Max: {result['max_price']}")

# generate_candles çıktısı
print("\n=== generate_candles(15, 5) çıktısı ===")
candles = storage.generate_candles(15, 5)
for i, candle in enumerate(candles):
    print(f"{i+1}. {candle.timestamp} - O:{candle.open:.2f} H:{candle.high:.2f} L:{candle.low:.2f} C:{candle.close:.2f}")

# SQL ile doğrudan mum oluştur
print("\n=== SQL ile son 15 dakika mumu ===")
cursor.execute("""
    SELECT 
        datetime(strftime('%s', 'now') / (15 * 60) * (15 * 60), 'unixepoch') as candle_time,
        MIN(gram_altin) as low,
        MAX(gram_altin) as high,
        (SELECT gram_altin FROM price_data 
         WHERE timestamp > datetime('now', '-15 minutes') 
         AND gram_altin IS NOT NULL 
         ORDER BY timestamp ASC LIMIT 1) as open,
        (SELECT gram_altin FROM price_data 
         WHERE timestamp > datetime('now', '-15 minutes') 
         AND gram_altin IS NOT NULL 
         ORDER BY timestamp DESC LIMIT 1) as close
    FROM price_data
    WHERE timestamp > datetime('now', '-15 minutes')
    AND gram_altin IS NOT NULL
""")
result = cursor.fetchone()
if result:
    print(f"Zaman: {result['candle_time']}")
    print(f"Open: {result['open']}")
    print(f"High: {result['high']}")
    print(f"Low: {result['low']}")
    print(f"Close: {result['close']}")

conn.close()