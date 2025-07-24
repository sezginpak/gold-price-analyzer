"""
HybridStrategy entegrasyon testleri
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from strategies.hybrid_strategy import HybridStrategy
from tests.test_helpers import (
    generate_trending_candles, generate_reversal_candles,
    generate_exhaustion_pattern, generate_stop_hunt_pattern,
    MockCandle
)
from models.market_data import MarketData


class TestHybridStrategyIntegration(unittest.TestCase):
    """HybridStrategy entegrasyon test sınıfı"""
    
    def setUp(self):
        """Her test öncesi kurulum"""
        self.strategy = HybridStrategy()
    
    def create_mock_market_data(self, usd_try=30.0, ons_usd=2000.0):
        """Mock market data oluştur"""
        gram_altin_price = (ons_usd * usd_try) / 31.1035  # Gram altın fiyatı hesapla
        
        return [
            MarketData(
                gram_altin=gram_altin_price,
                ons_usd=ons_usd,
                usd_try=usd_try,
                ons_try=ons_usd * usd_try
            )
        ]
    
    def test_basic_analysis(self):
        """Temel analiz testi"""
        candles = generate_trending_candles(2000, 30, "BULLISH")
        market_data = self.create_mock_market_data()
        
        result = self.strategy.analyze(candles, market_data, "15m")
        
        # Temel kontroller
        self.assertIn('signal', result)
        self.assertIn('confidence', result)
        self.assertIn('signal_strength', result)
        self.assertIn('position_size', result)
        
        # Tüm analizlerin mevcut olduğunu kontrol et
        self.assertIn('gram_analysis', result)
        self.assertIn('global_trend', result)
        self.assertIn('currency_risk', result)
        self.assertIn('divergence_analysis', result)
        self.assertIn('confluence_analysis', result)
        self.assertIn('structure_analysis', result)
        self.assertIn('momentum_analysis', result)
        self.assertIn('smart_money_analysis', result)
    
    def test_bullish_scenario(self):
        """Bullish senaryo testi"""
        # Güçlü bullish trend
        candles = generate_trending_candles(1950, 50, "BULLISH", 0.015)
        market_data = self.create_mock_market_data(usd_try=29.5, ons_usd=2050)
        
        result = self.strategy.analyze(candles, market_data, "1h")
        
        # Bullish sinyaller beklentisi
        if result['signal'] != 'HOLD':
            # Eğer sinyal varsa BUY olmalı
            self.assertEqual(result['signal'], 'BUY')
            self.assertGreater(result['confidence'], 0.3)
    
    def test_bearish_scenario(self):
        """Bearish senaryo testi"""
        # Güçlü bearish trend
        candles = generate_trending_candles(2100, 50, "BEARISH", 0.015)
        market_data = self.create_mock_market_data(usd_try=31.0, ons_usd=1950)
        
        result = self.strategy.analyze(candles, market_data, "1h")
        
        # Bearish sinyaller beklentisi
        if result['signal'] != 'HOLD':
            # Eğer sinyal varsa SELL olmalı
            self.assertEqual(result['signal'], 'SELL')
            self.assertGreater(result['confidence'], 0.3)
    
    def test_reversal_detection(self):
        """Dönüş noktası tespiti"""
        # Reversal pattern
        candles = generate_reversal_candles(2000, 40, 25)
        market_data = self.create_mock_market_data()
        
        result = self.strategy.analyze(candles, market_data, "4h")
        
        # Structure break olmalı
        structure = result.get('structure_analysis', {})
        if structure.get('structure_break'):
            self.assertIn(structure['break_type'], ['BULLISH_BREAK', 'BEARISH_BREAK'])
    
    def test_exhaustion_pattern_detection(self):
        """Exhaustion pattern tespiti"""
        candles = generate_exhaustion_pattern(2000)
        
        # Trend'i tamamla
        for i in range(20):
            candles.append(MockCandle(candles[-1].close, candles[-1].close - i))
        
        market_data = self.create_mock_market_data()
        result = self.strategy.analyze(candles, market_data, "15m")
        
        # Momentum exhaustion kontrolü
        momentum = result.get('momentum_analysis', {})
        if momentum.get('exhaustion_detected'):
            self.assertIn(momentum['exhaustion_type'], ['BULLISH', 'BEARISH'])
            self.assertGreater(momentum['exhaustion_score'], 0.5)
    
    def test_stop_hunt_integration(self):
        """Stop hunt pattern entegrasyonu"""
        support_level = 1980
        candles = generate_stop_hunt_pattern(2000, support_level)
        
        # Daha fazla candle ekle
        for i in range(15):
            candles.append(MockCandle(candles[-1].close + i, candles[-1].close + i + 1))
        
        market_data = self.create_mock_market_data()
        result = self.strategy.analyze(candles, market_data, "15m")
        
        # Smart money analizi
        smart_money = result.get('smart_money_analysis', {})
        if smart_money.get('stop_hunt_detected'):
            # Entry zone önerisi olmalı
            self.assertGreater(len(smart_money['entry_zones']), 0)
    
    def test_high_volatility_scenario(self):
        """Yüksek volatilite senaryosu"""
        candles = []
        base_price = 2000
        
        # Yüksek volatilite mumları
        for i in range(30):
            volatility = 30  # %1.5 volatilite
            open_price = base_price + i
            close_price = open_price + (volatility if i % 2 == 0 else -volatility)
            high_price = max(open_price, close_price) + volatility / 2
            low_price = min(open_price, close_price) - volatility / 2
            
            candles.append(MockCandle(open_price, close_price, high_price, low_price))
        
        market_data = self.create_mock_market_data(usd_try=31.5)  # Yüksek kur
        result = self.strategy.analyze(candles, market_data, "15m")
        
        # Yüksek volatilitede pozisyon boyutu azalmalı
        self.assertLess(result['position_size'], 1.0)
    
    def test_confluence_impact(self):
        """Confluence etkisi testi"""
        # Güçlü trend
        candles = generate_trending_candles(2000, 50, "BULLISH", 0.02)
        market_data = self.create_mock_market_data()
        
        result = self.strategy.analyze(candles, market_data, "1h")
        
        # Confluence analizi
        confluence = result.get('confluence_analysis', {})
        if confluence.get('confluence_score', 0) > 70:
            # Yüksek confluence = daha yüksek güven
            self.assertGreater(result['confidence'], 0.5)
    
    def test_risk_management(self):
        """Risk yönetimi testi"""
        candles = generate_trending_candles(2000, 30)
        market_data = self.create_mock_market_data(usd_try=32.0)  # Yüksek kur riski
        
        result = self.strategy.analyze(candles, market_data, "15m")
        
        # Risk kontrolleri
        self.assertIn('stop_loss', result)
        self.assertIn('take_profit', result)
        self.assertIn('risk_reward_ratio', result)
        
        # Stop loss mantıklı olmalı
        if result['signal'] == 'BUY':
            self.assertLess(result['stop_loss'], result['gram_price'])
            self.assertGreater(result['take_profit'], result['gram_price'])
        elif result['signal'] == 'SELL':
            self.assertGreater(result['stop_loss'], result['gram_price'])
            self.assertLess(result['take_profit'], result['gram_price'])
    
    def test_all_modules_working(self):
        """Tüm modüllerin çalıştığını kontrol et"""
        candles = generate_trending_candles(2000, 30)
        market_data = self.create_mock_market_data()
        
        result = self.strategy.analyze(candles, market_data, "15m")
        
        # Her modülün sonuç ürettiğini kontrol et
        modules_to_check = [
            'divergence_analysis',
            'confluence_analysis', 
            'structure_analysis',
            'momentum_analysis',
            'smart_money_analysis'
        ]
        
        for module in modules_to_check:
            self.assertIn(module, result)
            self.assertIsNotNone(result[module])
            self.assertIsInstance(result[module], dict)


if __name__ == '__main__':
    unittest.main()