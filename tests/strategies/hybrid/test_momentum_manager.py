"""
MomentumManager birim testleri
"""
import pytest
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from strategies.hybrid.momentum_manager import MomentumManager
from tests.test_helpers import (
    generate_exhaustion_pattern, create_mock_indicators,
    MockCandle, generate_trending_candles
)


@pytest.fixture
def momentum_manager():
    """MomentumManager fixture"""
    return MomentumManager()


class TestMomentumManager:
    """MomentumManager test sınıfı"""
    
    def test_empty_candles(self):
        """Boş veri durumu testi"""
        result = self.manager.analyze_momentum_exhaustion([], {})
        
        self.assertFalse(result['exhaustion_detected'])
        self.assertEqual(result['exhaustion_type'], 'NONE')
        self.assertEqual(result['exhaustion_score'], 0.0)
        self.assertEqual(len(result['signals']), 0)
    
    def test_consecutive_candles_detection(self, momentum_manager):
        """Ardışık mum tespiti"""
        candles = []
        
        # Önce bazı normal mumlar ekle (minimum gereksinim için)
        for i in range(5):
            candles.append(MockCandle(1990 + i, 1991 + i))
        
        # 7 ardışık yeşil mum
        for i in range(7):
            candles.append(MockCandle(2000 + i * 5, 2005 + i * 5))
        
        # Birkaç karışık mum
        candles.append(MockCandle(2040, 2038))
        candles.append(MockCandle(2038, 2042))
        
        result = self.manager.analyze_momentum_exhaustion(candles, {})
        
        # Ardışık yeşil mum tespiti
        self.assertEqual(result['consecutive_candles']['bullish_count'], 7)
        self.assertEqual(result['consecutive_candles']['pattern'], 'BULLISH_EXHAUSTION')
        self.assertIn('7 ardışık yeşil mum', ' '.join(result['signals']))
    
    def test_candle_anomaly_detection(self):
        """Dev mum anomali tespiti"""
        candles = []
        
        # Normal mumlar
        for i in range(19):
            candles.append(MockCandle(2000 + i, 2001 + i))
        
        # Dev mum (normal boyutun 2.5 katı)
        candles.append(MockCandle(2020, 2045))
        
        result = self.manager.analyze_momentum_exhaustion(candles, {})
        
        # Anomali tespiti
        self.assertTrue(result['candle_anomaly']['anomaly_detected'])
        self.assertEqual(result['candle_anomaly']['type'], 'BULLISH_SPIKE')
        self.assertGreater(result['candle_anomaly']['size_ratio'], 2.0)
    
    def test_extreme_indicators(self):
        """Ekstrem gösterge tespiti"""
        candles = generate_trending_candles(2000, 20)
        
        # Ekstrem göstergeler
        indicators = create_mock_indicators(
            rsi=85,  # Overbought
            stoch_k=90  # Overbought
        )
        
        result = self.manager.analyze_momentum_exhaustion(candles, indicators)
        
        # Ekstrem gösterge tespiti
        self.assertTrue(result['extreme_indicators']['rsi_extreme'])
        self.assertTrue(result['extreme_indicators']['stoch_extreme'])
        self.assertEqual(result['extreme_indicators']['extreme_type'], 'OVERBOUGHT')
        self.assertIn('ekstrem', ' '.join(result['signals']).lower())
    
    def test_volatility_analysis(self):
        """Volatilite analizi testi"""
        candles = generate_trending_candles(2000, 25)
        
        # Yüksek ATR değeri (volatilite spike)
        indicators = create_mock_indicators(atr_value=30)  # Normal 10-15 arası
        
        result = self.manager.analyze_momentum_exhaustion(candles, indicators)
        
        # Volatilite spike tespiti
        volatility = result['volatility_analysis']
        self.assertGreater(volatility['spike_ratio'], 1.0)
    
    def test_bollinger_squeeze(self):
        """Bollinger Band squeeze tespiti"""
        candles = generate_trending_candles(2000, 20)
        
        # Dar Bollinger Band (squeeze)
        indicators = {
            'bollinger': {
                'upper': 2005,
                'middle': 2000,
                'lower': 1995,
                'band_width': 0.5  # %0.5 - çok dar
            }
        }
        
        result = self.manager.analyze_momentum_exhaustion(candles, indicators)
        
        # BB squeeze tespiti
        self.assertTrue(result['volatility_analysis']['bb_squeeze'])
        self.assertIn('Bollinger Band squeeze', ' '.join(result['signals']))
    
    def test_exhaustion_pattern(self):
        """Tam exhaustion pattern testi"""
        candles = generate_exhaustion_pattern(2000)
        
        # Overbought göstergeler
        indicators = create_mock_indicators(
            rsi=75,
            stoch_k=85,
            atr_value=20
        )
        
        result = self.manager.analyze_momentum_exhaustion(candles, indicators)
        
        # Exhaustion tespiti
        self.assertTrue(result['exhaustion_detected'])
        self.assertEqual(result['exhaustion_type'], 'BEARISH')  # Bullish exhaustion = Bearish reversal
        self.assertGreater(result['exhaustion_score'], 0.6)
        self.assertIn('TEPE', result['recommendation'])
    
    def test_rejection_candle(self):
        """Rejection mumu tespiti"""
        candles = generate_trending_candles(2000, 10)
        
        # Rejection mumu ekle (uzun wick)
        rejection = MockCandle(
            open_price=2050,
            close_price=2051,
            high_price=2070,  # Uzun üst gölge
            low_price=2048
        )
        candles.append(rejection)
        
        result = self.manager.analyze_momentum_exhaustion(candles, {})
        
        # Rejection tespiti
        if result['candle_anomaly']['anomaly_detected']:
            self.assertGreater(result['candle_anomaly']['wick_ratio'], 2.0)
            self.assertTrue(result['candle_anomaly']['rejection'])
    
    def test_momentum_strength_calculation(self):
        """Momentum gücü hesaplama testi"""
        # Güçlü bullish momentum
        bullish_candles = generate_trending_candles(2000, 15, "BULLISH", 0.02)
        result_bull = self.manager.analyze_momentum_exhaustion(bullish_candles, {})
        
        # Güçlü bearish momentum
        bearish_candles = generate_trending_candles(2000, 15, "BEARISH", 0.02)
        result_bear = self.manager.analyze_momentum_exhaustion(bearish_candles, {})
        
        # Momentum strength kontrolleri
        self.assertGreater(result_bull['details']['momentum_strength'], 0)
        self.assertLess(result_bear['details']['momentum_strength'], 0)
    
    def test_scoring_weights(self):
        """Exhaustion skorlama ağırlıkları testi"""
        candles = generate_trending_candles(2000, 20)
        
        # Sadece ardışık mumlar
        result1 = self.manager.analyze_momentum_exhaustion(candles, {})
        score1 = result1['exhaustion_score']
        
        # Ardışık mumlar + ekstrem göstergeler
        indicators = create_mock_indicators(rsi=85, stoch_k=90)
        result2 = self.manager.analyze_momentum_exhaustion(candles, indicators)
        score2 = result2['exhaustion_score']
        
        # Ekstrem göstergeli skor daha yüksek olmalı
        self.assertGreater(score2, score1)
        self.assertLessEqual(score2, 1.0)


if __name__ == '__main__':
    unittest.main()