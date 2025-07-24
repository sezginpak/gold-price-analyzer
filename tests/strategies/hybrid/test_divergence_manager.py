"""
DivergenceManager birim testleri
"""
import unittest
import sys
import os

# Parent directory'yi path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from strategies.hybrid.divergence_manager import DivergenceManager
from tests.test_helpers import (
    generate_divergence_pattern, create_mock_indicators,
    generate_trending_candles
)


class TestDivergenceManager(unittest.TestCase):
    """DivergenceManager test sınıfı"""
    
    def setUp(self):
        """Her test öncesi kurulum"""
        self.manager = DivergenceManager()
    
    def test_empty_candles(self):
        """Boş veri durumu testi"""
        result = self.manager.analyze_divergences([], {})
        
        self.assertEqual(result['total_score'], 0)
        self.assertEqual(result['divergence_type'], 'NONE')
        self.assertEqual(result['strength'], 'NONE')
        self.assertEqual(len(result['divergences_found']), 0)
    
    def test_insufficient_candles(self):
        """Yetersiz veri durumu testi"""
        candles = generate_trending_candles(2000, 5)  # Minimum 10 gerekli
        result = self.manager.analyze_divergences(candles, {})
        
        self.assertEqual(result['divergence_type'], 'NONE')
        self.assertEqual(result['recommendation'], 'BEKLE - Yetersiz veri')
    
    def test_rsi_divergence_detection(self):
        """RSI divergence tespiti testi"""
        candles = generate_trending_candles(2000, 20, "BEARISH")
        
        # RSI oversold durumu (bullish divergence beklentisi)
        indicators = create_mock_indicators(rsi=25)
        
        result = self.manager.analyze_divergences(candles, indicators)
        
        # RSI divergence bulunmalı
        self.assertIn('RSI', result['divergences_found'])
        self.assertEqual(result['divergences_found']['RSI']['type'], 'bullish')
    
    def test_multiple_divergences(self):
        """Çoklu divergence tespiti"""
        candles, _ = generate_divergence_pattern(2000)
        
        # Çoklu ekstrem göstergeler
        indicators = create_mock_indicators(
            rsi=75,  # Overbought
            stoch_k=85,  # Overbought
            macd_hist=-0.5  # Negative divergence
        )
        
        result = self.manager.analyze_divergences(candles, indicators)
        
        # En az 2 divergence bulunmalı
        self.assertGreaterEqual(len(result['divergences_found']), 2)
        self.assertGreaterEqual(result['total_score'], 4)  # Moderate veya strong
    
    def test_divergence_scoring(self):
        """Divergence skorlama sistemi testi"""
        candles = generate_trending_candles(2000, 20)
        
        # Tüm göstergelerde divergence
        indicators = create_mock_indicators(
            rsi=25,  # Oversold
            stoch_k=15,  # Oversold
            macd_hist=0.5  # Positive
        )
        
        result = self.manager.analyze_divergences(candles, indicators)
        
        # Skorlama kontrolleri
        self.assertGreater(result['total_score'], 0)
        self.assertIn(result['strength'], ['STRONG', 'MODERATE', 'WEAK', 'NONE'])
        self.assertGreater(result['confidence'], 0)
    
    def test_bullish_divergence(self):
        """Bullish divergence testi"""
        # Düşen fiyat
        candles = generate_trending_candles(2000, 20, "BEARISH", 0.02)
        
        # Oversold göstergeler
        indicators = create_mock_indicators(rsi=20, stoch_k=10)
        
        result = self.manager.analyze_divergences(candles, indicators)
        
        if result['divergence_type'] != 'NONE':
            self.assertEqual(result['divergence_type'], 'BULLISH')
            self.assertIn('ALIŞ', result['recommendation'])
    
    def test_bearish_divergence(self):
        """Bearish divergence testi"""
        # Yükselen fiyat
        candles = generate_trending_candles(2000, 20, "BULLISH", 0.02)
        
        # Overbought göstergeler
        indicators = create_mock_indicators(rsi=80, stoch_k=90)
        
        result = self.manager.analyze_divergences(candles, indicators)
        
        if result['divergence_type'] != 'NONE':
            self.assertEqual(result['divergence_type'], 'BEARISH')
            self.assertIn('SATIŞ', result['recommendation'])
    
    def test_mfi_divergence_simulation(self):
        """MFI divergence simülasyonu testi"""
        # Yüksek volatilite pattern
        candles = []
        base_price = 2000
        
        # Düşük volatilite dönemi
        for i in range(10):
            candles.append(type('MockCandle', (), {
                'open': base_price + i * 0.5,
                'close': base_price + i * 0.5 + 0.1,
                'high': base_price + i * 0.5 + 0.2,
                'low': base_price + i * 0.5 - 0.1
            })())
        
        # Yüksek volatilite dönemi (fiyat düşerken)
        for i in range(10):
            candles.append(type('MockCandle', (), {
                'open': base_price + 5 - i * 2,
                'close': base_price + 5 - i * 2 - 1,
                'high': base_price + 5 - i * 2 + 3,
                'low': base_price + 5 - i * 2 - 4
            })())
        
        result = self.manager.analyze_divergences(candles, {})
        
        # MFI kontrolü
        if 'MFI' in result['divergences_found']:
            self.assertEqual(result['divergences_found']['MFI']['type'], 'bullish')
    
    def test_confidence_calculation(self):
        """Güven skoru hesaplama testi"""
        candles = generate_trending_candles(2000, 30)
        
        # Test 1: Düşük skor
        indicators1 = create_mock_indicators(rsi=50)
        result1 = self.manager.analyze_divergences(candles, indicators1)
        
        # Test 2: Yüksek skor
        indicators2 = create_mock_indicators(rsi=15, stoch_k=10, macd_hist=-2)
        result2 = self.manager.analyze_divergences(candles, indicators2)
        
        # Güven skorları karşılaştırması
        self.assertLess(result1['confidence'], result2['confidence'])
        self.assertLessEqual(result1['confidence'], 1.0)
        self.assertGreaterEqual(result1['confidence'], 0.0)


if __name__ == '__main__':
    unittest.main()