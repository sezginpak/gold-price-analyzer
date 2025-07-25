#!/usr/bin/env python3
"""
Hybrid strategy'yi direkt test et
"""
import sys
sys.path.insert(0, '.')

from strategies.hybrid_strategy import HybridStrategy

# Mock data
gram_analysis = {
    "signal": "BUY",
    "confidence": 0.5,
    "price": 3000,
    "trend": "BEARISH",
    "indicators": {"rsi": 30}
}

global_analysis = {
    "trend_direction": "BEARISH",
    "trend": "BEARISH"
}

currency_analysis = {
    "risk_level": "HIGH"
}

# Test hybrid strategy
hs = HybridStrategy()

# Mock the combine_signals call directly
combined = hs._combine_signals(
    gram_analysis, global_analysis, currency_analysis,
    {"combined_signal": "NEUTRAL", "combined_confidence": 0},  # advanced
    {"pattern_found": False},  # patterns
    "15m", 0.5  # timeframe, volatility
)

print(f"Gram Input: {gram_analysis['signal']} (conf={gram_analysis['confidence']:.2f})")
print(f"Combined Output: {combined['signal']} (conf={combined['confidence']:.3f})")

# Test the full analyze method with mock data
print("\n=== FULL ANALYZE TEST ===")
# We need proper candle data for this...
print("(Skipping full analyze test - needs proper candle data)")