#!/usr/bin/env python3
"""
Signal combiner'ı direkt test et
"""
import sys
sys.path.insert(0, '.')

from strategies.hybrid.signal_combiner import SignalCombiner
from collections import defaultdict

# Test signal combiner directly
sc = SignalCombiner()

# Test case 1: Exact values from DB
print("=== TEST 1: DB Values (conf=0.5) ===")
gram_signal = {"signal": "BUY", "confidence": 0.5}
global_trend = {"trend_direction": "BEARISH", "trend": "BEARISH"}
currency_risk = {"risk_level": "HIGH"}
advanced = {"combined_signal": "NEUTRAL", "combined_confidence": 0}
patterns = {"pattern_found": False}

result = sc.combine_signals(
    gram_signal, global_trend, currency_risk,
    advanced, patterns, "15m", 0.5
)

print(f"Input: Gram={gram_signal['signal']} (conf={gram_signal['confidence']:.2f})")
print(f"Output: Signal={result['signal']}, Conf={result['confidence']:.3f}")
print(f"Should override: {gram_signal['confidence'] >= 0.40}")

# Test case 2: Slightly lower confidence
print("\n=== TEST 2: Lower confidence (conf=0.417) ===")
gram_signal2 = {"signal": "BUY", "confidence": 0.417}
result2 = sc.combine_signals(
    gram_signal2, global_trend, currency_risk,
    advanced, patterns, "15m", 0.5
)

print(f"Input: Gram={gram_signal2['signal']} (conf={gram_signal2['confidence']:.3f})")
print(f"Output: Signal={result2['signal']}, Conf={result2['confidence']:.3f}")
print(f"Should override: {gram_signal2['confidence'] >= 0.40}")

# Test case 3: Check what's happening
print("\n=== TEST 3: Debug mode ===")
print("Checking override logic...")
print(f"gram_signal_type in ['BUY', 'SELL']: {gram_signal['signal'] in ['BUY', 'SELL']}")
print(f"gram_confidence >= 0.40: {gram_signal['confidence'] >= 0.40}")
print(f"Both conditions: {gram_signal['signal'] in ['BUY', 'SELL'] and gram_signal['confidence'] >= 0.40}")