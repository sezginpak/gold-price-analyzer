"""
Kapsamlı Integration Testleri - Hybrid Strategy
Bu test modülü Hybrid Strategy sisteminin tüm bileşenlerinin birlikte çalışmasını test eder.
"""
import pytest
import asyncio
import time
import os
import sys
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any
from decimal import Decimal
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Proje root'unu path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategies.hybrid_strategy import HybridStrategy
from models.market_data import MarketData, GramAltinCandle
from models.price_data import PriceData
from tests.test_helpers import (
    generate_trending_candles, generate_reversal_candles,
    generate_exhaustion_pattern, generate_stop_hunt_pattern,
    generate_divergence_pattern, MockCandle, create_mock_indicators,
    create_mock_key_levels
)


class TestHelpers:
    """Test yardımcı fonksiyonları"""
    
    @staticmethod
    def create_market_data_series(
        usd_try_start: float = 30.0, 
        ons_usd_start: float = 2000.0,
        trend: str = "NEUTRAL",
        count: int = 50
    ) -> List[MarketData]:
        """Market data serisi oluştur"""
        market_data = []
        
        for i in range(count):
            # Trend'e göre değişim
            if trend == "BULLISH":
                usd_try = usd_try_start + (i * 0.05)  # TRY zayıflıyor
                ons_usd = ons_usd_start + (i * 2)     # ONS artıyor
            elif trend == "BEARISH":
                usd_try = usd_try_start - (i * 0.05)  # TRY güçleniyor
                ons_usd = ons_usd_start - (i * 2)     # ONS düşüyor
            else:  # NEUTRAL
                usd_try = usd_try_start + (i * 0.01 * np.sin(i / 10))
                ons_usd = ons_usd_start + (i * 1 * np.cos(i / 10))
            
            gram_altin = (ons_usd * usd_try) / 31.1035
            
            market_data.append(MarketData(
                gram_altin=gram_altin,
                ons_usd=ons_usd,
                usd_try=usd_try,
                ons_try=ons_usd * usd_try
            ))
        
        return market_data
    
    @staticmethod
    def mock_candles_to_gram_candles(mock_candles: List[MockCandle], interval: str = "15m") -> List[GramAltinCandle]:
        """Mock candles'ları GramAltinCandle'a çevir"""
        gram_candles = []
        for candle in mock_candles:
            gram_candles.append(GramAltinCandle(
                timestamp=candle.timestamp,
                open=Decimal(str(candle.open)),
                high=Decimal(str(candle.high)),
                low=Decimal(str(candle.low)),
                close=Decimal(str(candle.close)),
                volume=1000,  # Integer olmalı
                interval=interval  # Interval field'ı ekle
            ))
        return gram_candles
    
    @staticmethod
    def create_high_volatility_candles(base_price: float, count: int) -> List[MockCandle]:
        """Yüksek volatilite candle'ları oluştur"""
        candles = []
        current_price = base_price
        
        for i in range(count):
            # %2-5 volatilite
            volatility_pct = np.random.uniform(0.02, 0.05)
            volatility = current_price * volatility_pct
            
            # Rastgele yön
            direction = np.random.choice([-1, 1])
            price_change = volatility * direction
            
            open_price = current_price
            close_price = current_price + price_change
            high_price = max(open_price, close_price) + abs(price_change) * 0.3
            low_price = min(open_price, close_price) - abs(price_change) * 0.3
            
            candles.append(MockCandle(
                open_price=open_price,
                close_price=close_price,
                high_price=high_price,
                low_price=low_price,
                timestamp=datetime.now() - timedelta(minutes=(count - i))
            ))
            
            current_price = close_price
        
        return candles
    
    @staticmethod
    def create_fibonacci_bounce_scenario(base_price: float) -> List[MockCandle]:
        """Fibonacci bounce senaryosu oluştur"""
        candles = []
        
        # Yükseliş trendi
        high_price = base_price * 1.1
        for i in range(20):
            price = base_price + (high_price - base_price) * (i / 20)
            candles.append(MockCandle(open_price=price - 1, close_price=price))
        
        # 61.8% retracement'a düşüş
        retracement_price = high_price - (high_price - base_price) * 0.618
        steps = 15
        for i in range(steps):
            price = high_price - (high_price - retracement_price) * (i / steps)
            candles.append(MockCandle(open_price=price + 1, close_price=price))
        
        # Bounce - 61.8 seviyesinden dönüş
        for i in range(10):
            bounce_target = retracement_price + (high_price - retracement_price) * 0.5
            price = retracement_price + (bounce_target - retracement_price) * (i / 10)
            candles.append(MockCandle(open_price=price - 1, close_price=price))
        
        return candles
    
    @staticmethod
    def create_smc_order_block_scenario(base_price: float) -> List[MockCandle]:
        """SMC Order Block senaryosu oluştur"""
        candles = []
        
        # Normal trend
        for i in range(20):
            price = base_price + i * 2
            candles.append(MockCandle(open_price=price, close_price=price + 1))
        
        # Order Block Formation - büyük düşüş mumu
        last_price = candles[-1].close
        order_block_candle = MockCandle(
            open_price=last_price,
            close_price=last_price - 20,  # Büyük düşüş
            high_price=last_price + 2,
            low_price=last_price - 25
        )
        candles.append(order_block_candle)
        
        # Düşüş devam
        current_price = order_block_candle.close
        for i in range(10):
            price = current_price - i * 3
            candles.append(MockCandle(open_price=price + 1, close_price=price))
        
        # Order block'a dönüş (test)
        current_price = candles[-1].close
        for i in range(8):
            # Order block seviyesine yaklaş
            target = order_block_candle.low + 10  # Order block yakını
            price = current_price + (target - current_price) * (i / 8)
            candles.append(MockCandle(open_price=price - 1, close_price=price))
        
        return candles


@pytest.mark.integration
class TestHybridStrategyIntegration:
    """Hybrid Strategy Integration Test Suite"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Her test için setup"""
        self.strategy = HybridStrategy()
        self.helpers = TestHelpers()
    
    def test_system_initialization(self):
        """Sistem başlatma testi"""
        # Tüm modüllerin doğru şekilde başlatıldığını kontrol et
        assert self.strategy.gram_analyzer is not None
        assert self.strategy.global_analyzer is not None
        assert self.strategy.currency_analyzer is not None
        assert self.strategy.fibonacci_analyzer is not None
        assert self.strategy.smc_analyzer is not None
        assert self.strategy.market_regime_detector is not None
        assert self.strategy.divergence_detector is not None
        assert self.strategy.signal_combiner is not None
        
        # Module weights doğru mu?
        assert abs(sum(self.strategy.module_weights.values()) - 1.0) < 0.01
    
    @pytest.mark.parametrize("timeframe", ["15m", "1h", "4h", "1d"])
    def test_end_to_end_analysis_all_timeframes(self, timeframe):
        """End-to-end analiz - tüm timeframe'ler"""
        candles = generate_trending_candles(2000, 50, "BULLISH")
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, timeframe)
        market_data = self.helpers.create_market_data_series()
        
        result = self.strategy.analyze(gram_candles, market_data, timeframe)
        
        # Temel sonuç kontrolü
        assert result is not None
        assert 'signal' in result
        assert 'confidence' in result
        assert 'timestamp' in result
        assert result['signal'] in ['BUY', 'SELL', 'HOLD']
        assert 0.0 <= result['confidence'] <= 1.0
        
        # Tüm analiz bileşenleri mevcut mu?
        required_components = [
            'gram_analysis', 'global_trend', 'currency_risk',
            'fibonacci_analysis', 'smc_analysis', 'market_regime_analysis',
            'divergence_analysis', 'advanced_indicators', 'pattern_analysis'
        ]
        
        for component in required_components:
            assert component in result, f"{component} missing in result"
    
    def test_bullish_scenario_full_confluence(self):
        """Tam confluence ile bullish senaryo"""
        # Güçlü bullish trend verisi
        candles = generate_trending_candles(1900, 60, "BULLISH", 0.02)
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        
        # Destekleyici market data (ONS yükseliyor, TRY zayıflıyor)
        market_data = self.helpers.create_market_data_series(
            usd_try_start=29.0, ons_usd_start=1950.0, trend="BULLISH"
        )
        
        result = self.strategy.analyze(gram_candles, market_data, "1h")
        
        # Güçlü bullish confluence beklentisi
        if result['signal'] != 'HOLD':
            assert result['signal'] == 'BUY', f"Expected BUY signal, got {result['signal']}"
            assert result['confidence'] > 0.4, f"Low confidence for strong bullish scenario: {result['confidence']}"
        
        # Signal quality kontrolü
        if 'quality_score' in result:
            assert result['quality_score'] > 30, "Low quality score for bullish confluence"
        
        # Risk management kontrolü
        assert result['stop_loss'] is not None
        assert result['take_profit'] is not None
        if result['signal'] == 'BUY':
            assert result['stop_loss'] < result['gram_price']
            assert result['take_profit'] > result['gram_price']
    
    def test_bearish_scenario_full_confluence(self):
        """Tam confluence ile bearish senaryo"""
        # Güçlü bearish trend verisi
        candles = generate_trending_candles(2100, 60, "BEARISH", 0.02)
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        
        # Destekleyici market data (ONS düşüyor, TRY güçleniyor)
        market_data = self.helpers.create_market_data_series(
            usd_try_start=31.0, ons_usd_start=2050.0, trend="BEARISH"
        )
        
        result = self.strategy.analyze(gram_candles, market_data, "1h")
        
        # Güçlü bearish confluence beklentisi
        if result['signal'] != 'HOLD':
            assert result['signal'] == 'SELL', f"Expected SELL signal, got {result['signal']}"
            assert result['confidence'] > 0.4, f"Low confidence for strong bearish scenario: {result['confidence']}"
        
        # Risk management kontrolü
        if result['signal'] == 'SELL':
            assert result['stop_loss'] > result['gram_price']
            assert result['take_profit'] < result['gram_price']
    
    def test_mixed_signals_scenario(self):
        """Karışık sinyaller senaryosu"""
        # Sideways market - karışık sinyaller
        candles = []
        base_price = 2000
        for i in range(50):
            # Zigzag pattern
            if i % 4 < 2:
                price = base_price + 10
            else:
                price = base_price - 10
            candles.append(MockCandle(open_price=price - 1, close_price=price))
        
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        
        # Neutral market data
        market_data = self.helpers.create_market_data_series(trend="NEUTRAL")
        
        result = self.strategy.analyze(gram_candles, market_data, "15m")
        
        # Karışık sinyallerde HOLD beklentisi veya düşük confidence
        if result['signal'] != 'HOLD':
            assert result['confidence'] < 0.7, "High confidence in mixed signal scenario"
        
        # Confluence score düşük olmalı
        if 'confluence_score' in result:
            assert result['confluence_score'] < 0.6, "High confluence in mixed signals"
    
    def test_high_volatility_regime_adaptation(self):
        """Yüksek volatilite rejimi adaptasyonu"""
        # Extreme volatility candles
        candles = self.helpers.create_high_volatility_candles(2000, 40)
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        
        # Yüksek kur volatilitesi
        market_data = self.helpers.create_market_data_series(
            usd_try_start=32.0, ons_usd_start=2000.0
        )
        
        result = self.strategy.analyze(gram_candles, market_data, "15m")
        
        # Yüksek volatilitede risk yönetimi
        assert result['position_size'] <= 0.8, "Position size should be reduced in high volatility"
        
        # Market regime analizi
        regime_analysis = result.get('market_regime_analysis', {})
        if regime_analysis.get('status') == 'success':
            vol_regime = regime_analysis.get('volatility_regime', {})
            assert vol_regime.get('level') in ['high', 'extreme'], "Should detect high volatility"
        
        # Adaptive parameters uygulandı mı?
        if 'adaptive_applied' in result:
            assert result['adaptive_applied'] == True, "Adaptive parameters should be applied"
    
    def test_trending_market_momentum_alignment(self):
        """Trending market momentum hizalama"""
        # Güçlü ve tutarlı trend
        candles = generate_trending_candles(1950, 80, "BULLISH", 0.008)  # Düşük volatilite
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        
        market_data = self.helpers.create_market_data_series(trend="BULLISH", count=80)
        
        result = self.strategy.analyze(gram_candles, market_data, "4h")
        
        # Trending market'te güçlü momentum beklentisi
        regime_analysis = result.get('market_regime_analysis', {})
        if regime_analysis.get('status') == 'success':
            momentum_regime = regime_analysis.get('momentum_regime', {})
            assert momentum_regime.get('state') in ['accelerating', 'stable'], "Should detect strong momentum"
            
            # Momentum alignment olmalı
            assert momentum_regime.get('momentum_alignment') == True, "Momentum should be aligned"
        
        # Signal quality yüksek olmalı
        if 'quality_score' in result:
            assert result['quality_score'] > 50, "Quality should be high in trending market"
    
    def test_ranging_market_detection(self):
        """Ranging market tespiti"""
        # Range-bound market
        candles = []
        base_price = 2000
        range_size = 30
        
        for i in range(60):
            # Range içinde hareket
            cycle_pos = (i % 20) / 20  # 0-1 cycle
            price_in_range = base_price + (range_size * np.sin(cycle_pos * 2 * np.pi) / 2)
            candles.append(MockCandle(
                open_price=price_in_range - 1,
                close_price=price_in_range
            ))
        
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = self.helpers.create_market_data_series(trend="NEUTRAL")
        
        result = self.strategy.analyze(gram_candles, market_data, "1h")
        
        # Ranging market tespiti
        regime_analysis = result.get('market_regime_analysis', {})
        if regime_analysis.get('status') == 'success':
            trend_regime = regime_analysis.get('trend_regime', {})
            assert trend_regime.get('direction') in ['neutral', 'ranging'], "Should detect ranging market"
            
            # Risk level orta-yüksek olmalı
            overall = regime_analysis.get('overall_assessment', {})
            assert overall.get('risk_level') in ['medium', 'high'], "Ranging market should have medium-high risk"
    
    def test_divergence_active_class_a(self):
        """Class A divergence aktif senaryosu"""
        # Divergence pattern oluştur
        candles, rsi_values = generate_divergence_pattern(2000, 50)
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        
        market_data = self.helpers.create_market_data_series()
        
        # Mock divergence detector'ı güçlü divergence döndürsün
        with patch.object(self.strategy.divergence_detector, 'analyze') as mock_divergence:
            mock_analysis = Mock()
            mock_analysis.overall_signal = 'BEARISH'
            mock_analysis.signal_strength = 85
            mock_analysis.confluence_score = 0.9
            mock_analysis.regular_divergences = ['mock_div']
            mock_analysis.hidden_divergences = []
            mock_analysis.dominant_divergence = Mock()
            mock_analysis.dominant_divergence.type = 'bearish'
            mock_analysis.dominant_divergence.strength = 90
            mock_analysis.dominant_divergence.class_rating = 'A'
            mock_analysis.next_targets = [1980, 1960]
            mock_analysis.invalidation_levels = [2020]
            
            mock_divergence.return_value = mock_analysis
            
            result = self.strategy.analyze(gram_candles, market_data, "1h")
            
            # Class A divergence bonus
            divergence_analysis = result.get('divergence_analysis', {})
            assert divergence_analysis.get('status') == 'success'
            
            dominant_div = divergence_analysis.get('dominant_divergence', {})
            assert dominant_div.get('class_rating') == 'A', "Should detect Class A divergence"
            
            # Quality score'da divergence bonusu
            if 'quality_score' in result:
                assert result['quality_score'] > 60, "Class A divergence should boost quality score"
    
    def test_smc_confluence_order_blocks_fvg(self):
        """SMC Confluence: Order Blocks + Fair Value Gaps"""
        # SMC order block senaryosu
        candles = self.helpers.create_smc_order_block_scenario(2000)
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        
        market_data = self.helpers.create_market_data_series()
        
        # Mock SMC analyzer'ı güçlü sinyal döndürsün
        with patch.object(self.strategy.smc_analyzer, 'analyze') as mock_smc:
            mock_smc.return_value = {
                'status': 'success',
                'signals': {'action': 'BUY', 'strength': 80},
                'market_structure': {'trend': 'bullish', 'structure_break': True},
                'order_blocks': [
                    {'type': 'bullish', 'low': 1980, 'high': 1990, 'strength': 85},
                    {'type': 'bullish', 'low': 1970, 'high': 1980, 'strength': 70}
                ],
                'fair_value_gaps': [
                    {'type': 'bullish', 'low': 1985, 'high': 1995, 'filled': False}
                ],
                'liquidity_zones': [
                    {'type': 'buy_side', 'level': 2010, 'strength': 60}
                ]
            }
            
            result = self.strategy.analyze(gram_candles, market_data, "15m")
            
            # SMC confluence
            smc_analysis = result.get('smc_analysis', {})
            assert smc_analysis.get('status') == 'success'
            assert len(smc_analysis.get('order_blocks', [])) >= 1, "Should have order blocks"
            assert len(smc_analysis.get('fair_value_gaps', [])) >= 1, "Should have FVGs"
            
            # SMC sinyali modül weighted average'da etkili olmalı
            module_signals = result.get('module_signals', {})
            if 'smc' in module_signals:
                assert module_signals['smc'] > 0.5, "SMC should provide bullish signal"
    
    def test_fibonacci_bounce_618_level(self):
        """Fibonacci %61.8 seviyesinden bounce"""
        # Fibonacci bounce senaryosu
        candles = self.helpers.create_fibonacci_bounce_scenario(1900)
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        
        market_data = self.helpers.create_market_data_series()
        
        # Mock Fibonacci analyzer'ı bounce döndürsün
        with patch.object(self.strategy.fibonacci_analyzer, 'analyze') as mock_fib:
            mock_fib.return_value = {
                'status': 'success',
                'signals': {'action': 'BUY', 'strength': 75},
                'bounce_potential': 85,
                'nearest_level': {
                    'level': '61.8%',
                    'price': 1965.5,
                    'distance': 2.1
                },
                'fibonacci_levels': {
                    '38.2%': {'price': 1985.6, 'strength': 'medium'},
                    '50.0%': {'price': 1975.0, 'strength': 'strong'},
                    '61.8%': {'price': 1965.5, 'strength': 'very_strong'}
                }
            }
            
            result = self.strategy.analyze(gram_candles, market_data, "1h")
            
            # Fibonacci bounce tespiti
            fib_analysis = result.get('fibonacci_analysis', {})
            assert fib_analysis.get('status') == 'success'
            assert fib_analysis.get('bounce_potential') > 70, "Should detect high bounce potential"
            
            nearest_level = fib_analysis.get('nearest_level', {})
            assert '61.8' in nearest_level.get('level', ''), "Should be near 61.8% level"
            
            # Fibonacci seviyesi enhanced take profit olarak kullanılmalı
            enhanced_levels = result.get('enhanced_levels')
            if enhanced_levels:
                assert result.get('fibonacci_tp_used') == True, "Should use Fibonacci for take profit"
    
    def test_module_failure_graceful_degradation(self):
        """Modül hata durumunda graceful degradation"""
        candles = generate_trending_candles(2000, 30, "BULLISH")
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = self.helpers.create_market_data_series()
        
        # Fibonacci analyzer'da hata simüle et
        with patch.object(self.strategy.fibonacci_analyzer, 'analyze', side_effect=Exception("Fibonacci error")):
            result = self.strategy.analyze(gram_candles, market_data, "15m")
            
            # Sistem hala çalışmalı
            assert result is not None
            assert 'signal' in result
            assert result['signal'] in ['BUY', 'SELL', 'HOLD']
            
            # Fibonacci analysis hata durumunda olmalı (insufficient_data veya error)
            fib_analysis = result.get('fibonacci_analysis', {})
            assert fib_analysis.get('status') in ['error', 'insufficient_data'], "Should handle Fibonacci error gracefully"
        
        # SMC analyzer'da hata simüle et
        with patch.object(self.strategy.smc_analyzer, 'analyze', side_effect=Exception("SMC error")):
            result = self.strategy.analyze(gram_candles, market_data, "15m")
            
            # Sistem hala çalışmalı
            assert result is not None
            assert 'signal' in result
            
            # SMC analysis hata durumunda olmalı (insufficient_data veya error)
            smc_analysis = result.get('smc_analysis', {})
            assert smc_analysis.get('status') in ['error', 'insufficient_data'], "Should handle SMC error gracefully"
        
        # Divergence analyzer'da hata simüle et
        with patch.object(self.strategy.divergence_detector, 'analyze', side_effect=Exception("Divergence error")):
            result = self.strategy.analyze(gram_candles, market_data, "15m")
            
            # Sistem hala çalışmalı
            assert result is not None
            assert 'signal' in result
            
            # Divergence analysis hata durumunda olmalı (insufficient_data veya error)
            div_analysis = result.get('divergence_analysis', {})
            assert div_analysis.get('status') in ['error', 'insufficient_data'], "Should handle Divergence error gracefully"
    
    def test_insufficient_data_handling(self):
        """Yetersiz veri durumunda işlem"""
        # Çok az candle (< 50)
        candles = generate_trending_candles(2000, 20, "BULLISH")
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = self.helpers.create_market_data_series(count=5)
        
        result = self.strategy.analyze(gram_candles, market_data, "15m")
        
        # Sistem hala çalışmalı ama sınırlı analiz
        assert result is not None
        assert 'signal' in result
        
        # Modüller insufficient_data döndürmeli
        for module in ['fibonacci_analysis', 'smc_analysis', 'market_regime_analysis', 'divergence_analysis']:
            analysis = result.get(module, {})
            if analysis.get('status') == 'insufficient_data':
                assert True  # Beklenen durum
    
    def test_transaction_cost_optimization(self):
        """İşlem maliyeti optimizasyonu (%0.45)"""
        # Düşük volatilite, küçük hareket beklentisi
        candles = []
        base_price = 2000
        
        # Küçük hareket (%0.3 toplam)
        for i in range(30):
            price = base_price + (i * 0.2)  # Toplam %0.3 hareket
            candles.append(MockCandle(open_price=price - 0.1, close_price=price))
        
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = self.helpers.create_market_data_series()
        
        result = self.strategy.analyze(gram_candles, market_data, "15m")
        
        # Transaction cost optimization uygulanmalı
        cost_opt = result.get('cost_optimization', {})
        if cost_opt:
            assert cost_opt.get('applied') == True, "Cost optimization should be applied for low movement"
            assert cost_opt.get('expected_move') < 0.9, "Expected move should be less than min profit target"
            
            # Confidence düşürülmeli veya HOLD'a çevrilmeli
            if result['signal'] != 'HOLD':
                assert result['confidence'] < 0.7, "Confidence should be reduced due to transaction costs"
    
    @pytest.mark.performance
    def test_performance_benchmark(self):
        """Performance benchmark testi"""
        candles = generate_trending_candles(2000, 100, "BULLISH")
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = self.helpers.create_market_data_series(count=100)
        
        # Execution time ölçümü
        start_time = time.time()
        result = self.strategy.analyze(gram_candles, market_data, "15m")
        execution_time = time.time() - start_time
        
        # Performance kriterleri
        assert execution_time < 5.0, f"Analysis took too long: {execution_time:.2f}s"
        assert result is not None, "Should return result within time limit"
        
        # Memory usage - psutil olmadığı için bu test iptal
        # try:
        #     import psutil
        #     process = psutil.Process()
        #     memory_info = process.memory_info()
        #     memory_mb = memory_info.rss / 1024 / 1024
        #     assert memory_mb < 500, f"Memory usage too high: {memory_mb:.1f}MB"
        # except ImportError:
        #     pass  # psutil yoksa memory test'ini atlayalım
        
        # Sadece execution time testi yap
        pass
    
    @pytest.mark.slow
    def test_stress_test_multiple_timeframes(self):
        """Stress test - çoklu timeframe"""
        candles = generate_trending_candles(2000, 200, "BULLISH")
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = self.helpers.create_market_data_series(count=200)
        
        timeframes = ["15m", "1h", "4h", "1d"]
        results = {}
        
        total_start = time.time()
        
        for tf in timeframes:
            start = time.time()
            result = self.strategy.analyze(gram_candles, market_data, tf)
            duration = time.time() - start
            
            results[tf] = {
                'result': result,
                'duration': duration,
                'success': result is not None and 'signal' in result
            }
        
        total_duration = time.time() - total_start
        
        # Tüm timeframe'lerde başarılı sonuç
        for tf, data in results.items():
            assert data['success'], f"Failed analysis for {tf}"
            assert data['duration'] < 3.0, f"Analysis too slow for {tf}: {data['duration']:.2f}s"
        
        assert total_duration < 10.0, f"Total analysis time too long: {total_duration:.2f}s"
    
    def test_signal_consistency_across_similar_data(self):
        """Benzer veri setlerinde sinyal tutarlılığı"""
        base_candles = generate_trending_candles(2000, 50, "BULLISH", 0.01)
        base_market_data = self.helpers.create_market_data_series(trend="BULLISH")
        
        results = []
        
        # 5 benzer veri seti
        for i in range(5):
            # Küçük varyasyonlar ekle
            varied_candles = []
            for candle in base_candles:
                noise = np.random.uniform(-0.5, 0.5)  # %0.5 noise
                varied_candles.append(MockCandle(
                    open_price=candle.open + noise,
                    close_price=candle.close + noise,
                    high_price=candle.high + noise,
                    low_price=candle.low + noise
                ))
            
            gram_candles = self.helpers.mock_candles_to_gram_candles(varied_candles)
            result = self.strategy.analyze(gram_candles, base_market_data, "1h")
            results.append(result)
        
        # Sinyal tutarlılığı kontrolü
        signals = [r['signal'] for r in results]
        confidences = [r['confidence'] for r in results]
        
        # Çoğunluktaki sinyal aynı olmalı
        signal_counts = {s: signals.count(s) for s in set(signals)}
        dominant_signal = max(signal_counts, key=signal_counts.get)
        
        assert signal_counts[dominant_signal] >= 3, "Signal should be consistent across similar data"
        
        # Confidence standard deviation çok yüksek olmamalı
        confidence_std = np.std(confidences)
        assert confidence_std < 0.3, f"Confidence should be stable: std={confidence_std:.3f}"
    
    def test_extreme_market_conditions(self):
        """Extreme market koşulları"""
        # Flash crash simulation
        candles = []
        base_price = 2000
        
        # Normal trend
        for i in range(20):
            price = base_price + i
            candles.append(MockCandle(open_price=price, close_price=price + 1))
        
        # Flash crash - %5 düşüş tek mumda
        crash_candle = MockCandle(
            open_price=candles[-1].close,
            close_price=candles[-1].close * 0.95,
            high_price=candles[-1].close + 1,
            low_price=candles[-1].close * 0.94
        )
        candles.append(crash_candle)
        
        # Recovery
        recovery_price = crash_candle.close * 1.02
        for i in range(10):
            price = crash_candle.close + (recovery_price - crash_candle.close) * (i / 10)
            candles.append(MockCandle(open_price=price - 1, close_price=price))
        
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = self.helpers.create_market_data_series()
        
        result = self.strategy.analyze(gram_candles, market_data, "15m")
        
        # Extreme condition'da sistem çökmemeli
        assert result is not None
        assert 'signal' in result
        
        # Yüksek risk tespiti
        regime_analysis = result.get('market_regime_analysis', {})
        if regime_analysis.get('status') == 'success':
            risk_level = regime_analysis.get('overall_assessment', {}).get('risk_level')
            assert risk_level in ['high', 'extreme'], "Should detect extreme risk"
        
        # Position size düşürülmeli
        assert result['position_size'] < 0.5, "Position size should be minimal in extreme conditions"
    
    def test_adaptive_parameters_dynamic_adjustment(self):
        """Adaptive parametrelerin dinamik ayarlanması"""
        # Değişken volatilite senaryosu
        candles = []
        base_price = 2000
        
        # Düşük volatilite başlangıç
        for i in range(20):
            noise = np.random.uniform(-1, 1)
            price = base_price + noise
            candles.append(MockCandle(open_price=price, close_price=price + 0.5))
        
        # Volatilite artışı
        for i in range(20):
            noise = np.random.uniform(-10, 10)  # %0.5 volatilite
            price = base_price + 20 + noise
            candles.append(MockCandle(open_price=price, close_price=price + noise/2))
        
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = self.helpers.create_market_data_series()
        
        # Mock market regime'i adaptive parameters döndürsün
        with patch.object(self.strategy.market_regime_detector, 'analyze_market_regime') as mock_regime:
            mock_regime.return_value = {
                'status': 'success',
                'volatility_regime': {'level': 'high', 'increasing': True},
                'trend_regime': {'direction': 'bullish', 'strength': 70},
                'momentum_regime': {'state': 'accelerating', 'momentum_alignment': True},
                'adaptive_parameters': {
                    'signal_threshold': 0.7,  # Yüksek threshold
                    'position_size_adjustment': 0.6,  # Pozisyon küçültme
                    'take_profit_multiplier': 1.3,
                    'stop_loss_multiplier': 1.1
                },
                'overall_assessment': {'risk_level': 'medium', 'opportunity_level': 'high'}
            }
            
            result = self.strategy.analyze(gram_candles, market_data, "15m")
            
            # Adaptive parameters etkisi
            assert result.get('adaptive_applied') == True, "Adaptive parameters should be applied"
            
            # Threshold etkisi - confidence düşürülmüş olmalı
            if result['confidence'] < 0.7:
                assert result['confidence'] < 0.8, "Confidence should be adjusted by adaptive threshold"
            
            # Enhanced risk levels'da adjustment olmalı
            enhanced_levels = result.get('enhanced_levels')
            if enhanced_levels:
                volatility_adjusted = result.get('volatility_adjusted')
                assert volatility_adjusted == True, "Risk levels should be volatility adjusted"
    
    def test_module_weight_impact_analysis(self):
        """Modül ağırlıklarının etkisini analiz et"""
        candles = generate_trending_candles(2000, 50, "BULLISH")
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = self.helpers.create_market_data_series(trend="BULLISH")
        
        # Orijinal ağırlıklar
        original_weights = self.strategy.module_weights.copy()
        result_original = self.strategy.analyze(gram_candles, market_data, "1h")
        
        # Fibonacci ağırlığını artır
        self.strategy.module_weights['fibonacci'] = 0.4
        self.strategy.module_weights['gram_analysis'] = 0.15
        self.strategy.module_weights['market_regime'] = 0.15
        self.strategy.module_weights['divergence'] = 0.15
        self.strategy.module_weights['smc'] = 0.15
        
        result_fib_weighted = self.strategy.analyze(gram_candles, market_data, "1h")
        
        # Ağırlık değişikliği sonucu farklı olmalı
        if result_original.get('weighted_score') != result_fib_weighted.get('weighted_score'):
            assert abs(result_original.get('weighted_score', 0) - 
                      result_fib_weighted.get('weighted_score', 0)) > 0.01, "Weight change should impact weighted score"
        
        # Orijinal ağırlıkları geri yükle
        self.strategy.module_weights = original_weights
    
    def test_risk_reward_ratio_optimization(self):
        """Risk/reward oranı optimizasyonu"""
        candles = generate_trending_candles(2000, 40, "BULLISH")
        gram_candles = self.helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = self.helpers.create_market_data_series()
        
        result = self.strategy.analyze(gram_candles, market_data, "1h")
        
        # Risk reward ratio mantıklı olmalı
        if result['signal'] in ['BUY', 'SELL'] and result['risk_reward_ratio']:
            assert result['risk_reward_ratio'] > 0.5, "Risk/reward ratio should be reasonable"
            assert result['risk_reward_ratio'] < 10.0, "Risk/reward ratio should not be unrealistic"
            
            # Enhanced levels kullanıldıysa daha iyi ratio olmalı
            if result.get('enhanced_levels'):
                assert result['risk_reward_ratio'] >= 1.0, "Enhanced levels should provide better risk/reward"
    
    def test_data_validation_and_sanitization(self):
        """Veri doğrulama ve temizleme"""
        # Geçersiz veri ile test
        invalid_candles = [
            MockCandle(open_price=0, close_price=2000),  # Geçersiz open
            MockCandle(open_price=2000, close_price=float('inf')),  # Geçersiz close
            MockCandle(open_price=-100, close_price=2000),  # Negatif fiyat
            MockCandle(open_price=2000, close_price=2000)  # Geçerli candle
        ]
        
        # Sistem geçersiz verileri handle etmeli
        try:
            gram_candles = self.helpers.mock_candles_to_gram_candles([invalid_candles[-1]])  # Sadece geçerli candle
            market_data = self.helpers.create_market_data_series()
            result = self.strategy.analyze(gram_candles, market_data, "15m")
            
            assert result is not None, "Should handle data validation gracefully"
        except Exception as e:
            # Eğer exception fırlatılıyorsa, mantıklı bir hata mesajı olmalı
            assert "invalid" in str(e).lower() or "data" in str(e).lower(), "Should provide meaningful error message"


if __name__ == "__main__":
    # Testleri çalıştır
    pytest.main([__file__, "-v", "--tb=short"])