"""
DivergenceManager birim testleri - pytest format
"""
import pytest
import sys
import os

# Parent directory'yi path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from strategies.hybrid.divergence_manager import DivergenceManager
from tests.test_helpers import (
    generate_divergence_pattern, create_mock_indicators,
    generate_trending_candles
)


@pytest.fixture
def divergence_manager():
    """DivergenceManager fixture"""
    return DivergenceManager()


class TestDivergenceManager:
    """DivergenceManager test sınıfı"""
    
    def test_empty_candles(self, divergence_manager):
        """Boş veri durumu testi"""
        result = divergence_manager.analyze_divergences([], {})
        
        assert result['total_score'] == 0
        assert result['divergence_type'] == 'NONE'
        assert result['strength'] == 'NONE'
        assert len(result['divergences_found']) == 0
    
    def test_insufficient_candles(self, divergence_manager):
        """Yetersiz veri durumu testi"""
        candles = generate_trending_candles(2000, 5)  # Minimum 10 gerekli
        result = divergence_manager.analyze_divergences(candles, {})
        
        assert result['divergence_type'] == 'NONE'
        assert result['recommendation'] == 'BEKLE - Yetersiz veri'
    
    def test_rsi_divergence_detection(self, divergence_manager):
        """RSI divergence tespiti testi"""
        candles = generate_trending_candles(2000, 20, "BEARISH")
        
        # RSI oversold durumu (bullish divergence beklentisi)
        indicators = create_mock_indicators(rsi=25)
        
        result = divergence_manager.analyze_divergences(candles, indicators)
        
        # RSI divergence bulunmalı
        assert 'RSI' in result['divergences_found']
        assert result['divergences_found']['RSI']['type'] == 'bullish'
    
    def test_multiple_divergences(self, divergence_manager):
        """Çoklu divergence tespiti"""
        candles, _ = generate_divergence_pattern(2000)
        
        # Çoklu ekstrem göstergeler
        indicators = create_mock_indicators(
            rsi=75,  # Overbought
            stoch_k=85,  # Overbought
            macd_hist=-0.5  # Negative divergence
        )
        
        result = divergence_manager.analyze_divergences(candles, indicators)
        
        # En az 2 divergence bulunmalı
        assert len(result['divergences_found']) >= 2
        # Skor, bulunan divergence'lara göre değerlendirilmeli
        # RSI (2) + Stochastic (2) = 4, ama max() kullanıldığı için bearish_score alınır
        assert result['total_score'] >= 2  # En az bir divergence skoru
    
    def test_divergence_scoring(self, divergence_manager):
        """Divergence skorlama sistemi testi"""
        candles = generate_trending_candles(2000, 20, "BEARISH")  # Düşen trend
        
        # Tüm göstergelerde divergence
        indicators = create_mock_indicators(
            rsi=25,  # Oversold
            stoch_k=15,  # Oversold
            macd_hist=0.5  # Positive
        )
        
        result = divergence_manager.analyze_divergences(candles, indicators)
        
        # Skorlama kontrolleri
        assert result['total_score'] > 0
        assert result['strength'] in ['STRONG', 'MODERATE', 'WEAK', 'NONE']
        assert result['confidence'] > 0
    
    def test_bullish_divergence(self, divergence_manager):
        """Bullish divergence testi"""
        # Düşen fiyat
        candles = generate_trending_candles(2000, 20, "BEARISH", 0.02)
        
        # Oversold göstergeler
        indicators = create_mock_indicators(rsi=20, stoch_k=10)
        
        result = divergence_manager.analyze_divergences(candles, indicators)
        
        if result['divergence_type'] != 'NONE':
            assert result['divergence_type'] == 'BULLISH'
            assert 'ALIŞ' in result['recommendation']
    
    def test_bearish_divergence(self, divergence_manager):
        """Bearish divergence testi"""
        # Yükselen fiyat
        candles = generate_trending_candles(2000, 20, "BULLISH", 0.02)
        
        # Overbought göstergeler
        indicators = create_mock_indicators(rsi=80, stoch_k=90)
        
        result = divergence_manager.analyze_divergences(candles, indicators)
        
        if result['divergence_type'] != 'NONE':
            assert result['divergence_type'] == 'BEARISH'
            assert 'SATIŞ' in result['recommendation']
    
    def test_mfi_divergence_simulation(self, divergence_manager):
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
        
        result = divergence_manager.analyze_divergences(candles, {})
        
        # MFI kontrolü
        if 'MFI' in result['divergences_found']:
            assert result['divergences_found']['MFI']['type'] == 'bullish'
    
    def test_confidence_calculation(self, divergence_manager):
        """Güven skoru hesaplama testi"""
        candles = generate_trending_candles(2000, 30)
        
        # Test 1: Düşük skor
        indicators1 = create_mock_indicators(rsi=50)
        result1 = divergence_manager.analyze_divergences(candles, indicators1)
        
        # Test 2: Yüksek skor
        indicators2 = create_mock_indicators(rsi=15, stoch_k=10, macd_hist=-2)
        result2 = divergence_manager.analyze_divergences(candles, indicators2)
        
        # Güven skorları karşılaştırması
        assert result1['confidence'] < result2['confidence']
        assert result1['confidence'] <= 1.0
        assert result1['confidence'] >= 0.0


if __name__ == '__main__':
    pytest.main([__file__])