#!/usr/bin/env python3
"""
Override kontrolü
"""
import sys
sys.path.insert(0, '.')
import sqlite3
from datetime import datetime

# Son hybrid analysis'i al
conn = sqlite3.connect('gold_prices.db')
cursor = conn.cursor()

# Son 5 hybrid analysis
cursor.execute("""
    SELECT 
        timeframe,
        signal,
        confidence,
        json_extract(gram_analysis, '$.signal') as gram_signal,
        json_extract(gram_analysis, '$.confidence') as gram_conf,
        datetime(timestamp, 'localtime') as time
    FROM hybrid_analysis 
    WHERE timeframe = '15m'
    ORDER BY timestamp DESC 
    LIMIT 5
""")

print("=== SON 5 HYBRID ANALYSIS (15m) ===")
print(f"{'Time':<20} {'Signal':<8} {'Conf':<8} {'Gram Sig':<10} {'Gram Conf':<10}")
print("-" * 60)

for row in cursor.fetchall():
    time, signal, conf, gram_sig, gram_conf = row[5], row[1], row[2], row[3], row[4]
    print(f"{time:<20} {signal:<8} {conf:<8.3f} {gram_sig:<10} {gram_conf:<10.3f}")
    
    # Override kontrolü
    if gram_sig in ["BUY", "SELL"] and gram_conf >= 0.40:
        if signal != gram_sig:
            print(f"   ❌ OVERRIDE FAILED: Should be {gram_sig} not {signal}")
        else:
            print(f"   ✅ OVERRIDE WORKED: {gram_sig} = {signal}")

conn.close()