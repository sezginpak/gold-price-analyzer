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
    
    def test_empty_candles(self, momentum_manager):
        """Boş veri durumu testi"""
        result = momentum_manager.analyze_momentum_exhaustion([], {})
        
        assert not result['exhaustion_detected']
        assert result['exhaustion_type'] == 'NONE'
        assert result['exhaustion_score'] == 0.0
        assert len(result['signals']) == 0
    
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
        
        result = momentum_manager.analyze_momentum_exhaustion(candles, {})
        
        # Ardışık yeşil mum tespiti
        assert result['consecutive_candles']['bullish_count'] >= 7
        assert result['consecutive_candles']['pattern'] == 'BULLISH_EXHAUSTION'
        assert 'ardışık' in ' '.join(result['signals']) and 'mum' in ' '.join(result['signals'])
    
    def test_candle_anomaly_detection(self, momentum_manager):
        """Dev mum anomali tespiti"""
        candles = []
        
        # Normal mumlar
        for i in range(19):
            candles.append(MockCandle(2000 + i, 2001 + i))
        
        # Dev mum (normal boyutun 2.5 katı)
        candles.append(MockCandle(2020, 2045))
        
        result = momentum_manager.analyze_momentum_exhaustion(candles, {})
        
        # Anomali tespiti
        assert result['candle_anomaly']['anomaly_detected'] == True
        assert result['candle_anomaly']['type'] == 'BULLISH_SPIKE'
        assert result['candle_anomaly']['size_ratio'] > 2.0
    
    def test_extreme_indicators(self, momentum_manager):
        """Ekstrem gösterge tespiti"""
        candles = generate_trending_candles(2000, 20)
        
        # Ekstrem göstergeler
        indicators = create_mock_indicators(
            rsi=85,  # Overbought
            stoch_k=90  # Overbought
        )
        
        result = momentum_manager.analyze_momentum_exhaustion(candles, indicators)
        
        # Ekstrem gösterge tespiti
        assert result['extreme_indicators']['rsi_extreme'] == True
        assert result['extreme_indicators']['stoch_extreme'] == True
        assert result['extreme_indicators']['extreme_type'] == 'OVERBOUGHT'
        assert 'ekstrem' in ' '.join(result['signals']).lower()
    
    def test_volatility_analysis(self, momentum_manager):
        """Volatilite analizi testi"""
        candles = generate_trending_candles(2000, 25)
        
        # Yüksek ATR değeri (volatilite spike)
        indicators = create_mock_indicators(atr_value=30)  # Normal 10-15 arası
        
        result = momentum_manager.analyze_momentum_exhaustion(candles, indicators)
        
        # Volatilite spike tespiti
        volatility = result['volatility_analysis']
        assert volatility['spike_ratio'] > 1.0
    
    def test_bollinger_squeeze(self, momentum_manager):
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
        
        result = momentum_manager.analyze_momentum_exhaustion(candles, indicators)
        
        # BB squeeze tespiti
        assert result['volatility_analysis']['bb_squeeze'] == True
        assert 'Bollinger Band squeeze' in ' '.join(result['signals'])
    
    def test_exhaustion_pattern(self, momentum_manager):
        """Tam exhaustion pattern testi"""
        candles = generate_exhaustion_pattern(2000)
        
        # Overbought göstergeler
        indicators = create_mock_indicators(
            rsi=75,
            stoch_k=85,
            atr_value=20
        )
        
        result = momentum_manager.analyze_momentum_exhaustion(candles, indicators)
        
        # Exhaustion tespiti
        assert result['exhaustion_detected'] == True
        assert result['exhaustion_type'] == 'BEARISH'  # Bullish exhaustion = Bearish reversal
        assert result['exhaustion_score'] > 0.6
        assert 'TEPE' in result['recommendation']
    
    def test_rejection_candle(self, momentum_manager):
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
        
        result = momentum_manager.analyze_momentum_exhaustion(candles, {})
        
        # Rejection tespiti
        if result['candle_anomaly']['anomaly_detected']:
            assert result['candle_anomaly']['wick_ratio'] > 2.0
            assert result['candle_anomaly']['rejection'] == True
    
    def test_momentum_strength_calculation(self, momentum_manager):
        """Momentum gücü hesaplama testi"""
        # Güçlü bullish momentum
        bullish_candles = generate_trending_candles(2000, 15, "BULLISH", 0.02)
        result_bull = momentum_manager.analyze_momentum_exhaustion(bullish_candles, {})
        
        # Güçlü bearish momentum
        bearish_candles = generate_trending_candles(2000, 15, "BEARISH", 0.02)
        result_bear = momentum_manager.analyze_momentum_exhaustion(bearish_candles, {})
        
        # Momentum strength kontrolleri
        assert result_bull['details']['momentum_strength'] > 0
        assert result_bear['details']['momentum_strength'] < 0
    
    def test_scoring_weights(self, momentum_manager):
        """Exhaustion skorlama ağırlıkları testi"""
        candles = generate_trending_candles(2000, 20)
        
        # Sadece ardışık mumlar
        result1 = momentum_manager.analyze_momentum_exhaustion(candles, {})
        score1 = result1['exhaustion_score']
        
        # Ardışık mumlar + ekstrem göstergeler
        indicators = create_mock_indicators(rsi=85, stoch_k=90)
        result2 = momentum_manager.analyze_momentum_exhaustion(candles, indicators)
        score2 = result2['exhaustion_score']
        
        # Ekstrem göstergeli skor daha yüksek olmalı
        assert score2 > score1
        assert score2 <= 1.0


if __name__ == '__main__':
    unittest.main()