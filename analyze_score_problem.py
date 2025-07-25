#!/usr/bin/env python3
"""
Score hesaplama problemini analiz et
"""
import sys
sys.path.insert(0, '.')

from collections import defaultdict
from strategies.hybrid.signal_combiner import SignalCombiner

print("=== SCORE HESAPLAMA ANALİZİ ===\n")

# Signal combiner instance
combiner = SignalCombiner()

# Test senaryosu: Gram BUY diyor
test_scores = defaultdict(float)

# Ağırlıkları göster
print("📊 Signal Combiner Ağırlıkları:")
for key, weight in combiner.weights.items():
    print(f"   {key}: {weight:.2f}")
print(f"   TOPLAM: {sum(combiner.weights.values()):.2f}")

# Senaryo 1: Sadece gram signal
print("\n🧪 Senaryo 1: Sadece Gram BUY sinyali")
test_scores.clear()
gram_confidence = 0.60
test_scores["BUY"] += combiner.weights["gram_analysis"] * gram_confidence
test_scores["HOLD"] += combiner.weights["gram_analysis"] * (1 - gram_confidence)

print(f"   Skorlar: {dict(test_scores)}")
final = max(test_scores.items(), key=lambda x: x[1])[0]
print(f"   Final sinyal: {final}")

# Senaryo 2: Global trend BEARISH (ters yönde)
print("\n🧪 Senaryo 2: Gram BUY + Global BEARISH")
test_scores.clear()
test_scores["BUY"] += combiner.weights["gram_analysis"] * gram_confidence
# Global trend ters yönde - HOLD'a puan verir
test_scores["HOLD"] += combiner.weights["global_trend"] * 0.5

print(f"   Skorlar: {dict(test_scores)}")
final = max(test_scores.items(), key=lambda x: x[1])[0]
print(f"   Final sinyal: {final}")

# Senaryo 3: Yüksek risk eklenince
print("\n🧪 Senaryo 3: Gram BUY + Global BEARISH + High Risk")
test_scores.clear()
test_scores["BUY"] += combiner.weights["gram_analysis"] * gram_confidence
test_scores["HOLD"] += combiner.weights["global_trend"] * 0.5
# Yüksek risk - HOLD'a daha çok puan
test_scores["HOLD"] += combiner.weights["currency_risk"] * 0.7
# BUY sinyalini zayıflat
test_scores["BUY"] *= 0.7

print(f"   Skorlar: {dict(test_scores)}")
final = max(test_scores.items(), key=lambda x: x[1])[0]
print(f"   Final sinyal: {final}")

print("\n💡 ANALİZ:")
print("1. Gram analyzer tek başına BUY verse bile...")
print("2. Global trend BEARISH ise HOLD'a puan ekleniyor")
print("3. Risk yüksekse HOLD daha da güçleniyor")
print("4. Sonuçta HOLD kazanıyor!")

print("\n🔧 ÇÖZÜM ÖNERİLERİ:")
print("1. Gram sinyaline daha fazla ağırlık ver (0.35 -> 0.50)")
print("2. Global trend mismatch'i daha az cezalandır")
print("3. Gram BUY/SELL varsa direkt onu kullan (override)")

# Gerçek bir analiz simüle et
print("\n📊 Gerçek Veri Simülasyonu:")
real_data = {
    "gram_signal": {"signal": "BUY", "confidence": 0.40},
    "global_trend": {"trend_direction": "BEARISH"},
    "currency_risk": {"risk_level": "HIGH"},
    "advanced_indicators": {"combined_signal": "NEUTRAL", "combined_confidence": 0},
    "patterns": {"pattern_found": False}
}

# Manuel hesaplama
scores = defaultdict(float)

# 1. Gram signal
gram_sig = real_data["gram_signal"]["signal"]
gram_conf = real_data["gram_signal"]["confidence"]
scores[gram_sig] += combiner.weights["gram_analysis"] * gram_conf

# 2. Global trend
if real_data["global_trend"]["trend_direction"] == "BEARISH" and gram_sig == "BUY":
    scores["HOLD"] += combiner.weights["global_trend"] * 0.5

# 3. Risk
if real_data["currency_risk"]["risk_level"] == "HIGH":
    scores["HOLD"] += combiner.weights["currency_risk"] * 0.7
    scores["BUY"] *= 0.7

print(f"\nGerçek skorlar: {dict(scores)}")
final = max(scores.items(), key=lambda x: x[1])[0]
print(f"Final sinyal: {final} {'❌ SORUN VAR!' if final == 'HOLD' else '✅'}")