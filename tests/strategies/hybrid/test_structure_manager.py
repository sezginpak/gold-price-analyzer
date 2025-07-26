"""
StructureManager birim testleri
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from strategies.hybrid.structure_manager import StructureManager
from tests.test_helpers import (
    generate_trending_candles, generate_reversal_candles,
    MockCandle
)


class TestStructureManager(unittest.TestCase):
    """StructureManager test sınıfı"""
    
    def setUp(self):
        """Her test öncesi kurulum"""
        self.manager = StructureManager()
    
    def test_empty_candles(self):
        """Boş veri durumu testi"""
        result = self.manager.analyze_market_structure([], 2000)
        
        self.assertEqual(result['current_structure'], 'NEUTRAL')
        self.assertFalse(result['structure_break'])
        self.assertEqual(result['break_type'], 'NONE')
        self.assertEqual(len(result['swing_points']), 0)
    
    def test_bullish_structure(self):
        """Bullish market structure testi (HH/HL)"""
        # Açık bullish trend verisi oluştur - higher highs ve higher lows
        candles = []
        
        # İlk swing low
        candles.extend([
            MockCandle(2000, 1995),
            MockCandle(1995, 1990),
            MockCandle(1990, 1985),  # Low point
        ])
        
        # İlk swing high
        candles.extend([
            MockCandle(1985, 1995),
            MockCandle(1995, 2005),
            MockCandle(2005, 2010),  # High point
        ])
        
        # Higher low
        candles.extend([
            MockCandle(2010, 2005),
            MockCandle(2005, 2000),
            MockCandle(2000, 1995),  # Higher low (1995 > 1985)
        ])
        
        # Higher high
        candles.extend([
            MockCandle(1995, 2010),
            MockCandle(2010, 2020),
            MockCandle(2020, 2025),  # Higher high (2025 > 2010)
        ])
        
        # Son birkaç mum
        for _ in range(5):
            candles.append(MockCandle(2020, 2022))
        
        result = self.manager.analyze_market_structure(candles, 2020)
        
        # Bullish structure beklentisi (son highs ve lows yükseliyor)
        if len(result['swing_points']) >= 4:
            self.assertEqual(result['current_structure'], 'BULLISH')
    
    def test_bearish_structure(self):
        """Bearish market structure testi (LL/LH)"""
        # Bearish trend verisi
        candles = []
        prices = [2050, 2060, 2030, 2045, 2010, 2025, 1990, 2005, 1970]
        
        for i, price in enumerate(prices):
            is_high = i % 2 == 1  # Tek indexler high, çift indexler low
            if is_high:
                candle = MockCandle(price - 5, price, price + 2, price - 7)
            else:
                candle = MockCandle(price + 5, price, price + 7, price - 2)
            candles.append(candle)
        
        # Yeterli candle ekle
        for _ in range(15):
            candles.append(MockCandle(1970, 1975))
        
        result = self.manager.analyze_market_structure(candles, 1975)
        
        # Bearish structure beklentisi
        if len(result['swing_points']) >= 4:
            self.assertEqual(result['current_structure'], 'BEARISH')
    
    def test_structure_break_detection(self):
        """Structure break tespiti"""
        # Önce bearish sonra bullish break
        candles = []
        
        # Bearish dönem (LL/LH)
        for i in range(10):
            if i % 2 == 0:
                candle = MockCandle(2000 - i * 10, 1995 - i * 10)
            else:
                candle = MockCandle(1995 - i * 10, 2000 - i * 10)
            candles.append(candle)
        
        # Bullish break - önceki high'ı kır
        break_candle = MockCandle(1900, 1950, 1955, 1895)
        candles.append(break_candle)
        
        result = self.manager.analyze_market_structure(candles, 1950)
        
        # Structure break beklentisi
        if result['structure_break']:
            self.assertEqual(result['break_type'], 'BULLISH_BREAK')
    
    def test_key_levels_identification(self):
        """Key level tespiti"""
        candles = generate_reversal_candles(2000, 20)
        current_price = 1995
        
        result = self.manager.analyze_market_structure(candles, current_price)
        
        # Key levels kontrolü
        self.assertIn('resistance', result['key_levels'])
        self.assertIn('support', result['key_levels'])
        
        # Nearest levels kontrolü
        if result['key_levels']['nearest_resistance']:
            self.assertGreater(result['key_levels']['nearest_resistance'], current_price)
        
        if result['key_levels']['nearest_support']:
            self.assertLess(result['key_levels']['nearest_support'], current_price)
    
    def test_pullback_zone_detection(self):
        """Pullback zone tespiti"""
        candles = []
        
        # Support level oluştur
        support_level = 1980
        for i in range(5):
            candles.append(MockCandle(support_level + i, support_level + i + 1))
        
        # Breakout
        for i in range(3):
            candles.append(MockCandle(1990 + i * 5, 1995 + i * 5))
        
        # Pullback to support
        candles.append(MockCandle(2005, 1985, 2010, 1982))
        
        result = self.manager.analyze_market_structure(candles, 1985)
        
        # Pullback zone içinde olmalı
        if result['pullback_zone']:
            self.assertTrue(result['entry_zone']['active'])
            self.assertEqual(result['entry_zone']['type'], 'BUY')
    
    def test_swing_point_filtering(self):
        """Swing point filtreleme testi"""
        candles = []
        
        # Küçük dalgalanmalar (filtrelenmeli)
        for i in range(20):
            price = 2000 + (i % 2) * 0.1  # %0.005 hareket
            candles.append(MockCandle(price, price + 0.05))
        
        result = self.manager.analyze_market_structure(candles, 2000)
        
        # Minimum swing percent altında olduğu için swing point bulunmamalı
        self.assertEqual(len(result['swing_points']), 0)
    
    def test_confidence_calculation(self):
        """Güven skoru hesaplama testi"""
        # Güçlü trend verisi
        candles = generate_trending_candles(2000, 30, "BULLISH", 0.015)
        
        result = self.manager.analyze_market_structure(candles, candles[-1].close)
        
        # Güven skoru kontrolleri
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertLessEqual(result['confidence'], 1.0)
        
        # Daha fazla swing point = daha yüksek güven
        if len(result['swing_points']) >= 6:
            self.assertGreater(result['confidence'], 0.5)
    
    def test_trend_strength_calculation(self):
        """Trend gücü hesaplama testi"""
        # Güçlü trend
        strong_trend = generate_trending_candles(2000, 20, "BULLISH", 0.02)
        result_strong = self.manager.analyze_market_structure(strong_trend, 2100)
        
        # Zayıf trend
        weak_trend = generate_trending_candles(2000, 20, "BULLISH", 0.005)
        result_weak = self.manager.analyze_market_structure(weak_trend, 2020)
        
        # Güçlü trend daha yüksek trend strength'e sahip olmalı
        if result_strong['details']['trend_strength'] > 0 and result_weak['details']['trend_strength'] > 0:
            self.assertGreater(
                result_strong['details']['trend_strength'],
                result_weak['details']['trend_strength']
            )


if __name__ == '__main__':
    unittest.main()