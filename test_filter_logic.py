#!/usr/bin/env python3
"""
Filter logic'i test et
"""
import sys
sys.path.insert(0, '.')

from utils.constants import MIN_CONFIDENCE_THRESHOLDS

print("=== FILTER LOGIC TEST ===\n")

# Test senaryoları
test_cases = [
    # (timeframe, signal, confidence, expected_result)
    ("15m", "BUY", 0.60, "PASS"),   # %60 > %25 threshold
    ("15m", "BUY", 0.40, "PASS"),   # %40 > %25 threshold
    ("15m", "BUY", 0.24, "FAIL"),   # %24 < %25 threshold
    ("1h", "SELL", 0.35, "PASS"),   # %35 > %30 threshold
    ("1h", "BUY", 0.28, "FAIL"),    # %28 < %30 threshold
]

print("📊 Mevcut Confidence Threshold'ları:")
for tf, threshold in MIN_CONFIDENCE_THRESHOLDS.items():
    print(f"   {tf}: {threshold:.2%}")

print("\n🧪 Test Sonuçları:")
print(f"{'Timeframe':<10} {'Signal':<8} {'Confidence':<12} {'Threshold':<12} {'Sonuç':<10}")
print("-" * 60)

for tf, signal, conf, expected in test_cases:
    threshold = MIN_CONFIDENCE_THRESHOLDS.get(tf, 0.5)
    result = "PASS ✅" if conf >= threshold else "FAIL ❌"
    expected_icon = "✅" if expected == "PASS" else "❌"
    
    print(f"{tf:<10} {signal:<8} {conf:<12.2%} {threshold:<12.2%} {result}")
    
    if (result.startswith("PASS") and expected == "FAIL") or (result.startswith("FAIL") and expected == "PASS"):
        print(f"   ⚠️  UYARI: Beklenen {expected}{expected_icon} ama {result} aldık!")

# Gerçek veritabanı değerlerini kontrol et
print("\n📊 Veritabanındaki Son Değerler:")
import sqlite3
conn = sqlite3.connect('gold_prices.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT 
        timeframe,
        signal,
        confidence,
        json_extract(gram_analysis, '$.signal') as gram_signal,
        json_extract(gram_analysis, '$.confidence') as gram_conf
    FROM hybrid_analysis 
    WHERE timeframe IN ('15m', '1h')
    ORDER BY timestamp DESC 
    LIMIT 10
''')

results = cursor.fetchall()
print(f"\n{'TF':<5} {'Signal':<8} {'Conf':<8} {'Gram Sig':<10} {'Gram Conf':<10} {'Geçmeli mi?'}")
print("-" * 60)

for tf, signal, conf, gram_sig, gram_conf in results:
    threshold = MIN_CONFIDENCE_THRESHOLDS.get(tf, 0.5)
    should_pass = conf >= threshold
    status = "✅ EVET" if should_pass else "❌ HAYIR"
    
    print(f"{tf:<5} {signal:<8} {conf:<8.2%} {gram_sig or 'N/A':<10} {gram_conf or 0:<10.2%} {status}")
    
    # Eğer gram BUY/SELL ama final HOLD ise problem var
    if gram_sig in ['BUY', 'SELL'] and signal == 'HOLD':
        print(f"   🚨 PROBLEM: Gram {gram_sig} diyor ama {signal} olmuş!")
        if conf < threshold:
            print(f"      → Sebep: Confidence ({conf:.2%}) < Threshold ({threshold:.2%})")

conn.close()