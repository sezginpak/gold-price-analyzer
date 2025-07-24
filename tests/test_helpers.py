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
        close_price=support_level + 2,
        low_price=support_level - 5  # Support'u 5 puan del
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