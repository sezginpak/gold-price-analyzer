"""
Test yardımcı fonksiyonları ve mock data üreticileri
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random


class MockCandle:
    """Test için mock candle verisi"""
    def __init__(self, open_price: float, close_price: float = None, 
                 high_price: float = None, low_price: float = None,
                 timestamp: datetime = None):
        self.open = open_price
        self.close = close_price or (open_price + random.uniform(-10, 10))
        self.high = high_price or max(self.open, self.close) + random.uniform(0, 5)
        self.low = low_price or min(self.open, self.close) - random.uniform(0, 5)
        self.timestamp = timestamp or datetime.now()


def generate_trending_candles(base_price: float, count: int, 
                            trend: str = "BULLISH", volatility: float = 0.01) -> List[MockCandle]:
    """Trend'li mum verisi üret"""
    candles = []
    current_price = base_price
    
    for i in range(count):
        if trend == "BULLISH":
            change = random.uniform(0, volatility * current_price)
        elif trend == "BEARISH":
            change = -random.uniform(0, volatility * current_price)
        else:  # NEUTRAL
            change = random.uniform(-volatility * current_price / 2, volatility * current_price / 2)
        
        open_price = current_price
        close_price = current_price + change
        
        candle = MockCandle(
            open_price=open_price,
            close_price=close_price,
            timestamp=datetime.now() - timedelta(minutes=(count - i))
        )
        candles.append(candle)
        current_price = close_price
    
    return candles


def generate_reversal_candles(base_price: float, count: int, 
                            reversal_point: int = None) -> List[MockCandle]:
    """Dönüş pattern'li mum verisi üret"""
    if reversal_point is None:
        reversal_point = count // 2
    
    candles = []
    
    # İlk yarı - yukarı trend
    candles.extend(generate_trending_candles(base_price, reversal_point, "BULLISH"))
    
    # İkinci yarı - aşağı trend
    last_price = candles[-1].close
    candles.extend(generate_trending_candles(last_price, count - reversal_point, "BEARISH"))
    
    return candles


def generate_exhaustion_pattern(base_price: float) -> List[MockCandle]:
    """Momentum exhaustion pattern'i üret"""
    candles = []
    current_price = base_price
    
    # 7 ardışık yeşil mum (momentum buildup)
    for i in range(7):
        increase = (0.005 + i * 0.001) * current_price  # Artan momentum
        candle = MockCandle(
            open_price=current_price,
            close_price=current_price + increase
        )
        candles.append(candle)
        current_price = candle.close
    
    # Dev mum (spike)
    spike_candle = MockCandle(
        open_price=current_price,
        close_price=current_price * 1.02,  # %2 spike
        high_price=current_price * 1.025
    )
    candles.append(spike_candle)
    
    # Rejection mumu
    rejection_candle = MockCandle(
        open_price=spike_candle.close,
        close_price=spike_candle.close * 0.99,
        high_price=spike_candle.close * 1.005,
        low_price=spike_candle.close * 0.985
    )
    candles.append(rejection_candle)
    
    return candles


def generate_stop_hunt_pattern(base_price: float, support_level: float) -> List[MockCandle]:
    """Stop hunt pattern'i üret"""
    candles = []
    
    # Support'a yaklaşma
    for i in range(5):
        candle = MockCandle(
            open_price=base_price - i * 2,
            close_price=base_price - (i + 1) * 2
        )
        candles.append(candle)
    
    # Stop hunt spike (support'u delme)
    hunt_candle = MockCandle(
        open_price=candles[-1].close,
        close_price=support_level - 2,
        low_price=support_level - 10,  # Support'u 10 puan del (daha belirgin)
        high_price=candles[-1].close + 2
    )
    candles.append(hunt_candle)
    
    # Recovery
    recovery_candle = MockCandle(
        open_price=hunt_candle.close,
        close_price=support_level + 10
    )
    candles.append(recovery_candle)
    
    return candles


def generate_divergence_pattern(base_price: float, count: int = 20) -> tuple:
    """Divergence pattern'i üret (fiyat ve RSI için)"""
    candles = []
    prices = []
    rsi_values = []
    
    # İlk tepe
    for i in range(count // 2):
        price = base_price + (i * 2)
        candle = MockCandle(open_price=price - 1, close_price=price)
        candles.append(candle)
        prices.append(price)
        # RSI ilk tepede yüksek
        rsi_values.append(70 + i)
    
    # Düşüş
    for i in range(count // 4):
        price = prices[-1] - (i * 3)
        candle = MockCandle(open_price=price + 1, close_price=price)
        candles.append(candle)
        prices.append(price)
        rsi_values.append(50 - i * 2)
    
    # İkinci tepe (fiyat daha yüksek, RSI daha düşük = bearish divergence)
    for i in range(count // 4):
        price = prices[-1] + (i * 4)
        candle = MockCandle(open_price=price - 1, close_price=price)
        candles.append(candle)
        prices.append(price)
        # RSI ikinci tepede daha düşük
        rsi_values.append(60 - i)
    
    return candles, rsi_values


def generate_exhaustion_pattern(base_price: float, count: int = 30) -> List[MockCandle]:
    """Exhaustion pattern oluştur - ardışık mumlar ve momentum artışı"""
    candles = []
    
    # Normal mumlar
    for i in range(count // 2):
        price = base_price + i * 0.5
        candle = MockCandle(open_price=price, close_price=price + 0.3)
        candles.append(candle)
    
    # Exhaustion pattern - ardışık büyük yeşil mumlar
    for i in range(8):  # 8 ardışık yeşil mum
        price = candles[-1].close
        # Giderek büyüyen mumlar
        size = 2 + i * 0.5
        candle = MockCandle(open_price=price, close_price=price + size)
        candles.append(candle)
    
    # Son dev mum (spike)
    last_price = candles[-1].close
    spike_candle = MockCandle(open_price=last_price, close_price=last_price + 10)
    candles.append(spike_candle)
    
    return candles


def create_mock_indicators(rsi: float = 50, stoch_k: float = 50, 
                         macd_hist: float = 0, atr_value: float = 10) -> Dict[str, Any]:
    """Mock gösterge verileri oluştur"""
    return {
        'rsi': rsi,
        'stochastic': {
            'k': stoch_k,
            'd': stoch_k - 5,
            'k_values': [stoch_k - i for i in range(10)]
        },
        'macd': {
            'macd': 0.5,
            'signal': 0.3,
            'histogram': macd_hist,
            'histogram_values': [macd_hist - i * 0.1 for i in range(10)]
        },
        'atr': {
            'value': atr_value,
            'values': [atr_value - i * 0.5 for i in range(10)]
        },
        'bollinger': {
            'upper': 2050,
            'middle': 2000,
            'lower': 1950,
            'band_width': 5.0
        }
    }


def create_mock_key_levels(current_price: float) -> Dict[str, Any]:
    """Mock key level verileri oluştur"""
    return {
        'resistance': [current_price + 20, current_price + 40, current_price + 60],
        'support': [current_price - 20, current_price - 40, current_price - 60],
        'nearest_resistance': current_price + 20,
        'nearest_support': current_price - 20
    }


def create_mock_smc_analysis(signal: str = "NEUTRAL", strength: int = 50) -> Dict[str, Any]:
    """Mock Smart Money Concepts analizi oluştur"""
    return {
        "status": "success",
        "signal": signal,
        "strength": strength,
        "market_structure": {
            "trend": "bullish" if signal == "BUY" else "bearish" if signal == "SELL" else "neutral",
            "structure_break": signal != "NEUTRAL",
            "bos_count": 2 if signal != "NEUTRAL" else 0
        },
        "order_blocks": [
            {
                "type": "bullish" if signal == "BUY" else "bearish",
                "low": 1980 if signal == "BUY" else 2020,
                "high": 1990 if signal == "BUY" else 2030,
                "strength": strength,
                "fresh": True
            }
        ],
        "fair_value_gaps": [
            {
                "type": "bullish" if signal == "BUY" else "bearish",
                "low": 1985,
                "high": 1995,
                "filled": False,
                "strength": "high"
            }
        ],
        "liquidity_zones": [
            {
                "type": "buy_side" if signal == "BUY" else "sell_side",
                "level": 2010 if signal == "BUY" else 1990,
                "strength": 70
            }
        ]
    }


def create_mock_fibonacci_analysis(signal: str = "NEUTRAL", strength: int = 50) -> Dict[str, Any]:
    """Mock Fibonacci Retracement analizi oluştur"""
    base_price = 2000
    return {
        "status": "success",
        "signal": signal,
        "strength": strength,
        "bounce_potential": 80 if signal != "NEUTRAL" else 30,
        "nearest_level": {
            "level": "61.8%" if signal != "NEUTRAL" else "50.0%",
            "price": base_price * 0.618 if signal == "BUY" else base_price * 1.382,
            "distance": 2.1,
            "strength": "very_strong" if signal != "NEUTRAL" else "medium"
        },
        "fibonacci_levels": {
            "23.6%": {"price": base_price * 0.764, "strength": "weak"},
            "38.2%": {"price": base_price * 0.618, "strength": "medium"},
            "50.0%": {"price": base_price * 0.5, "strength": "strong"},
            "61.8%": {"price": base_price * 0.382, "strength": "very_strong"},
            "78.6%": {"price": base_price * 0.214, "strength": "medium"}
        }
    }


def create_mock_market_regime(regime_type: str = "NEUTRAL") -> Dict[str, Any]:
    """Mock Market Regime analizi oluştur"""
    return {
        "status": "success",
        "volatility_regime": {
            "level": "medium" if regime_type == "NEUTRAL" else "high",
            "increasing": regime_type != "NEUTRAL",
            "squeeze_potential": False
        },
        "trend_regime": {
            "direction": regime_type.lower() if regime_type != "NEUTRAL" else "neutral",
            "strength": 70 if regime_type != "NEUTRAL" else 40,
            "trend_strength": 65 if regime_type != "NEUTRAL" else 35
        },
        "momentum_regime": {
            "state": "accelerating" if regime_type != "NEUTRAL" else "stable",
            "momentum_alignment": regime_type != "NEUTRAL",
            "rsi_momentum": regime_type.lower() if regime_type != "NEUTRAL" else "neutral"
        },
        "adaptive_parameters": {
            "signal_threshold": 0.7 if regime_type != "NEUTRAL" else 0.6,
            "position_size_adjustment": 0.8 if regime_type != "NEUTRAL" else 1.0,
            "take_profit_multiplier": 1.2,
            "stop_loss_multiplier": 1.1
        },
        "overall_assessment": {
            "risk_level": "medium" if regime_type == "NEUTRAL" else "high",
            "opportunity_level": "high" if regime_type != "NEUTRAL" else "medium",
            "overall_score": 75 if regime_type != "NEUTRAL" else 50
        },
        "recommendations": {
            "position_sizing": "normal" if regime_type == "NEUTRAL" else "reduced",
            "timeframe_preference": "1h",
            "risk_management": "standard"
        }
    }


def create_mock_divergence_analysis(signal: str = "NEUTRAL", strength: int = 50) -> Dict[str, Any]:
    """Mock Advanced Divergence analizi oluştur"""
    from unittest.mock import Mock
    
    # Mock divergence objesi oluştur
    mock_divergence = Mock()
    mock_divergence.type = signal.lower() if signal != "NEUTRAL" else "none"
    mock_divergence.strength = strength
    mock_divergence.class_rating = "A" if strength > 80 else "B" if strength > 60 else "C"
    
    return {
        "status": "success",
        "overall_signal": signal,
        "signal_strength": strength,
        "confluence_score": 0.8 if signal != "NEUTRAL" else 0.3,
        "regular_divergences_count": 1 if signal != "NEUTRAL" else 0,
        "hidden_divergences_count": 0,
        "dominant_divergence": {
            "type": mock_divergence.type,
            "strength": mock_divergence.strength,
            "class_rating": mock_divergence.class_rating
        },
        "next_targets": [1980, 1960] if signal == "SELL" else [2020, 2040] if signal == "BUY" else [],
        "invalidation_levels": [2020] if signal == "SELL" else [1980] if signal == "BUY" else []
    }


def create_extreme_volatility_candles(base_price: float, count: int, volatility_pct: float = 0.05) -> List[MockCandle]:
    """Extreme volatilite candle'ları oluştur"""
    import random
    candles = []
    current_price = base_price
    
    for i in range(count):
        # Extreme volatility
        max_change = current_price * volatility_pct
        price_change = random.uniform(-max_change, max_change)
        
        open_price = current_price
        close_price = current_price + price_change
        
        # Wide ranges
        high_price = max(open_price, close_price) + abs(price_change) * 0.5
        low_price = min(open_price, close_price) - abs(price_change) * 0.5
        
        candles.append(MockCandle(
            open_price=open_price,
            close_price=close_price,
            high_price=high_price,
            low_price=low_price,
            timestamp=datetime.now() - timedelta(minutes=(count - i))
        ))
        
        current_price = close_price
    
    return candles


def create_flash_crash_scenario(base_price: float) -> List[MockCandle]:
    """Flash crash senaryosu oluştur"""
    candles = []
    
    # Normal trend (20 candle)
    for i in range(20):
        price = base_price + i * 2
        candles.append(MockCandle(open_price=price, close_price=price + 1.5))
    
    # Flash crash candle - %5 düşüş
    last_price = candles[-1].close
    crash_candle = MockCandle(
        open_price=last_price,
        close_price=last_price * 0.95,  # %5 düşüş
        high_price=last_price + 1,
        low_price=last_price * 0.93    # Daha da düşük low
    )
    candles.append(crash_candle)
    
    # Hızlı recovery (10 candle)
    recovery_target = crash_candle.close * 1.03
    for i in range(10):
        price = crash_candle.close + (recovery_target - crash_candle.close) * (i / 10)
        candles.append(MockCandle(
            open_price=price - 1,
            close_price=price,
            high_price=price + 2,
            low_price=price - 1.5
        ))
    
    return candles


def create_sideways_market_candles(base_price: float, range_size: float, count: int) -> List[MockCandle]:
    """Sideways (ranging) market candle'ları oluştur"""
    import math
    candles = []
    
    for i in range(count):
        # Sine wave pattern için range içinde
        cycle_position = (i % 20) / 20  # 20 candle'lık cycle
        sine_value = math.sin(cycle_position * 2 * math.pi)
        
        price_offset = sine_value * (range_size / 2)
        price = base_price + price_offset
        
        # Küçük mum gövdeleri
        body_size = range_size * 0.02  # Range'in %2'si
        open_price = price
        close_price = price + (body_size if i % 2 == 0 else -body_size)
        
        # Wick'ler range sınırları içinde
        high_price = max(open_price, close_price) + range_size * 0.01
        low_price = min(open_price, close_price) - range_size * 0.01
        
        candles.append(MockCandle(
            open_price=open_price,
            close_price=close_price,
            high_price=high_price,
            low_price=low_price,
            timestamp=datetime.now() - timedelta(minutes=(count - i))
        ))
    
    return candles


def create_strong_momentum_candles(base_price: float, direction: str, count: int) -> List[MockCandle]:
    """Güçlü momentum candle'ları oluştur"""
    candles = []
    current_price = base_price
    
    # Momentum acceleration - her candle öncekinden büyük
    for i in range(count):
        # Artan momentum
        momentum_factor = 1 + (i * 0.1)  # Her candle'da %0.1 artış
        base_size = current_price * 0.005  # %0.5 base
        candle_size = base_size * momentum_factor
        
        if direction.upper() == "BULLISH":
            open_price = current_price
            close_price = current_price + candle_size
        else:  # BEARISH
            open_price = current_price
            close_price = current_price - candle_size
        
        high_price = max(open_price, close_price) + candle_size * 0.1
        low_price = min(open_price, close_price) - candle_size * 0.1
        
        candles.append(MockCandle(
            open_price=open_price,
            close_price=close_price,
            high_price=high_price,
            low_price=low_price,
            timestamp=datetime.now() - timedelta(minutes=(count - i))
        ))
        
        current_price = close_price
    
    return candles