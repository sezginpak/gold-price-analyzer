"""
Sinyal analizi ve strateji filtreleme modülü
"""
import logging
from datetime import datetime
from typing import Dict, Optional
from decimal import Decimal

from models.simulation import (
    SimulationConfig,
    StrategyType
)

logger = logging.getLogger("gold_analyzer")


class SignalAnalyzer:
    """Sinyal analizi ve strateji filtreleme işlemleri"""
    
    def should_open_position(
        self,
        config: SimulationConfig,
        signal_data: Dict,
        timeframe: str
    ) -> bool:
        """Pozisyon açılmalı mı kontrolü"""
        logger.debug(f"\n=== Should open position check for {timeframe} ===")
        logger.debug(f"Config - Strategy: {config.strategy_type.value}, Min confidence: {config.min_confidence}")
        
        # 1. Sinyal kontrolü
        signal = signal_data.get('signal')
        if not signal or signal == 'HOLD':
            logger.debug(f"No valid signal: {signal}")
            return False
        
        # 2. Confidence kontrolü
        confidence = signal_data.get('confidence', 0)
        logger.debug(f"Signal: {signal}, Confidence: {confidence}")
        logger.debug(f"Min confidence required: {config.min_confidence}")
        
        if confidence < config.min_confidence:
            logger.debug(f"Confidence too low: {confidence} < {config.min_confidence}")
            return False
        
        # 3. Strateji tipine göre ek filtreler
        logger.debug(f"✅ Basic checks passed, applying strategy filter...")
        if not self._apply_strategy_filter(config, signal_data, timeframe):
            logger.debug(f"❌ Strategy filter failed for {config.strategy_type.value}")
            return False
        
        logger.info(f"✅ Should open position for {timeframe}: {signal} @ confidence {confidence}")
        return True
    
    def _apply_strategy_filter(
        self,
        config: SimulationConfig,
        signal_data: Dict,
        timeframe: str
    ) -> bool:
        """Strateji tipine göre sinyal filtrele"""
        strategy = config.strategy_type
        indicators = signal_data.get('indicators', {})
        
        logger.debug(f"Applying {strategy.value} filter for {timeframe}")
        
        if strategy == StrategyType.MAIN:
            # Ana strateji - ek filtre yok
            logger.debug(f"{timeframe} - MAIN strategy: No additional filter")
            return True
        
        elif strategy == StrategyType.CONSERVATIVE:
            # Sadece yüksek güvenli sinyaller
            confidence = signal_data.get('confidence', 0)
            # Config'den min_confidence değerini al ve %50 daha yüksek bir eşik kullan
            min_conf = config.min_confidence
            conservative_threshold = min_conf * 1.5  # Conservative için %50 daha yüksek
            result = confidence >= conservative_threshold
            logger.debug(f"{timeframe} - CONSERVATIVE: confidence {confidence} >= {conservative_threshold} ? {result}")
            return result
        
        elif strategy == StrategyType.MOMENTUM:
            # RSI 30-70 dışında
            rsi = indicators.get('rsi')
            logger.debug(f"{timeframe} - MOMENTUM: RSI={rsi}")
            if rsi:
                result = rsi < 30 or rsi > 70
                logger.debug(f"{timeframe} - MOMENTUM: RSI {rsi} outside 30-70? {result}")
                return result
            return False
        
        elif strategy == StrategyType.MEAN_REVERSION:
            # Bollinger band dışında
            bb = indicators.get('bb', {})
            logger.debug(f"{timeframe} - MEAN_REVERSION: BB={bb}")
            
            if not bb:
                logger.debug(f"{timeframe} - MEAN_REVERSION: No BB data")
                return False
            
            price = signal_data.get('price')
            # BB verisi 'upper_band'/'lower_band' veya 'upper'/'lower' olabilir
            upper = bb.get('upper_band') or bb.get('upper')
            lower = bb.get('lower_band') or bb.get('lower')
            
            logger.debug(f"{timeframe} - MEAN_REVERSION: Upper={upper}, Lower={lower}, Price={price}")
            
            if price and upper and lower:
                result = price > upper or price < lower
                logger.debug(f"{timeframe} - MEAN_REVERSION: Price outside bands? {result}")
                return result
            
            return False
        
        return True
    
    def check_exit_conditions(
        self,
        position,
        current_price: Decimal,
        current_signal: Dict,
        config: SimulationConfig
    ) -> Optional[str]:
        """Pozisyon çıkış koşullarını kontrol et"""
        exit_reason = None
        
        # 1. Stop loss kontrolü
        if position.position_type == "LONG":
            if current_price <= position.stop_loss:
                exit_reason = "STOP_LOSS"
        else:
            if current_price >= position.stop_loss:
                exit_reason = "STOP_LOSS"
        
        # 2. Take profit kontrolü
        if not exit_reason:
            if position.position_type == "LONG":
                if current_price >= position.take_profit:
                    exit_reason = "TAKE_PROFIT"
            else:
                if current_price <= position.take_profit:
                    exit_reason = "TAKE_PROFIT"
        
        # 3. Trailing stop kontrolü
        if not exit_reason and position.trailing_stop:
            if position.position_type == "LONG":
                if current_price <= position.trailing_stop:
                    exit_reason = "TRAILING_STOP"
            else:
                if current_price >= position.trailing_stop:
                    exit_reason = "TRAILING_STOP"
        
        # 4. Ters sinyal kontrolü
        if not exit_reason:
            new_signal = current_signal.get('signal')
            if new_signal:
                if position.position_type == "LONG" and new_signal == "SELL":
                    exit_reason = "REVERSE_SIGNAL"
                elif position.position_type == "SHORT" and new_signal == "BUY":
                    exit_reason = "REVERSE_SIGNAL"
        
        # 5. Zaman limiti kontrolü
        if not exit_reason:
            time_limit = config.time_limits.get(position.timeframe, 168)
            holding_hours = (datetime.now() - position.entry_time).total_seconds() / 3600
            if holding_hours >= time_limit:
                exit_reason = "TIME_LIMIT"
        
        return exit_reason
    
    def update_trailing_stop(
        self,
        position,
        current_price: Decimal,
        config: SimulationConfig
    ) -> Optional[Decimal]:
        """Trailing stop güncelleme kontrolü"""
        if position.position_type == "LONG":
            # Kar kontrolü
            profit_pct = (current_price - position.entry_price) / position.entry_price
            
            # Aktivasyon seviyesine ulaştı mı?
            if profit_pct >= config.trailing_stop_activation:
                # Yeni trailing stop seviyesi
                new_trailing = current_price * (1 - config.trailing_stop_distance)
                
                # Mevcut trailing stop'tan yüksekse güncelle
                if not position.trailing_stop or new_trailing > position.trailing_stop:
                    return new_trailing
        
        else:  # SHORT
            # Kar kontrolü
            profit_pct = (position.entry_price - current_price) / position.entry_price
            
            # Aktivasyon seviyesine ulaştı mı?
            if profit_pct >= config.trailing_stop_activation:
                # Yeni trailing stop seviyesi
                new_trailing = current_price * (1 + config.trailing_stop_distance)
                
                # Mevcut trailing stop'tan düşükse güncelle
                if not position.trailing_stop or new_trailing < position.trailing_stop:
                    return new_trailing
        
        return None