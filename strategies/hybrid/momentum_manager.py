"""
Momentum Manager - Momentum exhaustion ve volatilite analizi
"""
from typing import Dict, List, Any, Optional, Tuple
import logging
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)


class MomentumManager:
    """Momentum exhaustion tespiti ve volatilite analizi"""
    
    def __init__(self):
        # Parametreler
        self.consecutive_threshold = 5  # Ardışık mum eşiği
        self.candle_size_multiplier = 2.0  # Dev mum çarpanı
        self.atr_expansion_threshold = 1.5  # ATR genişleme eşiği
        self.bb_squeeze_threshold = 1.0  # BB daralma eşiği (%)
        
        # Geçmiş veriler
        self.momentum_history = deque(maxlen=20)
        
    def analyze_momentum_exhaustion(self, 
                                   candles: List,
                                   indicators: Dict) -> Dict[str, Any]:
        """
        Momentum exhaustion analizi
        
        Returns:
            {
                'exhaustion_detected': bool,
                'exhaustion_type': str (BULLISH/BEARISH/NONE),
                'exhaustion_score': float (0-1),
                'signals': List[str],
                'consecutive_candles': Dict,
                'candle_anomaly': Dict,
                'extreme_indicators': Dict,
                'volatility_analysis': Dict,
                'recommendation': str,
                'details': Dict
            }
        """
        if not candles or len(candles) < 10:
            return self._empty_exhaustion_result()
        
        # 1. Ardışık mum analizi
        consecutive_analysis = self._analyze_consecutive_candles(candles)
        
        # 2. Mum büyüklüğü anomalisi
        candle_anomaly = self._analyze_candle_anomaly(candles)
        
        # 3. Ekstrem gösterge durumu
        extreme_indicators = self._analyze_extreme_indicators(indicators)
        
        # 4. Volatilite analizi (ATR + BB)
        volatility_analysis = self._analyze_volatility(candles, indicators)
        
        # 5. Exhaustion skoru hesapla
        exhaustion_score, exhaustion_type = self._calculate_exhaustion_score(
            consecutive_analysis, candle_anomaly, 
            extreme_indicators, volatility_analysis
        )
        
        # 6. Sinyaller oluştur
        signals = self._generate_exhaustion_signals(
            consecutive_analysis, candle_anomaly, 
            extreme_indicators, volatility_analysis
        )
        
        # 7. Öneri oluştur
        recommendation = self._generate_recommendation(
            exhaustion_type, exhaustion_score, signals
        )
        
        # History güncelle
        self.momentum_history.append({
            'exhaustion_score': exhaustion_score,
            'type': exhaustion_type,
            'timestamp': candles[-1].timestamp if hasattr(candles[-1], 'timestamp') else None
        })
        
        return {
            'exhaustion_detected': exhaustion_score >= 0.6,
            'exhaustion_type': exhaustion_type,
            'exhaustion_score': exhaustion_score,
            'signals': signals,
            'consecutive_candles': consecutive_analysis,
            'candle_anomaly': candle_anomaly,
            'extreme_indicators': extreme_indicators,
            'volatility_analysis': volatility_analysis,
            'recommendation': recommendation,
            'details': {
                'signal_count': len(signals),
                'history': list(self.momentum_history)[-5:],
                'momentum_strength': self._calculate_momentum_strength(candles)
            }
        }
    
    def _analyze_consecutive_candles(self, candles: List) -> Dict:
        """Ardışık aynı yönlü mum analizi"""
        if len(candles) < 5:
            return {'bullish_count': 0, 'bearish_count': 0, 'pattern': 'NONE'}
        
        # Son 10 mumu kontrol et
        recent_candles = candles[-10:]
        
        # Ardışık yeşil/kırmızı sayısı
        current_bullish = 0
        current_bearish = 0
        max_bullish = 0
        max_bearish = 0
        
        for candle in recent_candles:
            is_bullish = float(candle.close) > float(candle.open)
            
            if is_bullish:
                current_bullish += 1
                current_bearish = 0
                max_bullish = max(max_bullish, current_bullish)
            else:
                current_bearish += 1
                current_bullish = 0
                max_bearish = max(max_bearish, current_bearish)
        
        # Pattern belirleme
        pattern = 'NONE'
        if max_bullish >= self.consecutive_threshold:
            pattern = 'BULLISH_EXHAUSTION'
        elif max_bearish >= self.consecutive_threshold:
            pattern = 'BEARISH_EXHAUSTION'
        
        return {
            'bullish_count': max_bullish,
            'bearish_count': max_bearish,
            'pattern': pattern,
            'last_direction': 'BULLISH' if current_bullish > 0 else 'BEARISH'
        }
    
    def _analyze_candle_anomaly(self, candles: List) -> Dict:
        """Dev mum ve anomali tespiti"""
        if len(candles) < 20:
            return {'anomaly_detected': False, 'type': 'NONE'}
        
        # Son 20 mumun ortalama büyüklüğü
        candle_sizes = []
        for candle in candles[-20:-1]:  # Son hariç
            size = abs(float(candle.close) - float(candle.open))
            candle_sizes.append(size)
        
        avg_size = np.mean(candle_sizes)
        
        # Son mumun büyüklüğü
        last_candle = candles[-1]
        last_size = abs(float(last_candle.close) - float(last_candle.open))
        
        # Anomali kontrolü
        is_anomaly = last_size > avg_size * self.candle_size_multiplier
        
        # Anomali tipi
        anomaly_type = 'NONE'
        if is_anomaly:
            if float(last_candle.close) > float(last_candle.open):
                anomaly_type = 'BULLISH_SPIKE'
            else:
                anomaly_type = 'BEARISH_SPIKE'
        
        # Wick analizi (gölge/beden oranı)
        body_size = last_size
        total_range = float(last_candle.high) - float(last_candle.low)
        wick_ratio = (total_range - body_size) / body_size if body_size > 0 else 0
        
        return {
            'anomaly_detected': is_anomaly,
            'type': anomaly_type,
            'size_ratio': last_size / avg_size if avg_size > 0 else 1,
            'wick_ratio': wick_ratio,
            'rejection': wick_ratio > 2.0  # Güçlü rejection
        }
    
    def _analyze_extreme_indicators(self, indicators: Dict) -> Dict:
        """RSI, Stochastic vb. ekstrem durumları"""
        extremes = {
            'rsi_extreme': False,
            'stoch_extreme': False,
            'triple_extreme': False,
            'extreme_type': 'NONE'
        }
        
        # RSI kontrolü
        rsi_value = indicators.get('rsi')
        if rsi_value:
            if rsi_value > 70:
                extremes['rsi_extreme'] = True
                extremes['extreme_type'] = 'OVERBOUGHT'
            elif rsi_value < 30:
                extremes['rsi_extreme'] = True
                extremes['extreme_type'] = 'OVERSOLD'
        
        # Stochastic kontrolü
        stoch_data = indicators.get('stochastic', {})
        stoch_k = stoch_data.get('k')
        if stoch_k:
            if stoch_k > 80:
                extremes['stoch_extreme'] = True
                if extremes['extreme_type'] != 'OVERSOLD':
                    extremes['extreme_type'] = 'OVERBOUGHT'
            elif stoch_k < 20:
                extremes['stoch_extreme'] = True
                if extremes['extreme_type'] != 'OVERBOUGHT':
                    extremes['extreme_type'] = 'OVERSOLD'
        
        # MACD kontrolü (opsiyonel)
        macd_data = indicators.get('macd', {})
        macd_hist = macd_data.get('histogram')
        
        # Triple extreme kontrolü
        extreme_count = 0
        if extremes['rsi_extreme']:
            extreme_count += 1
        if extremes['stoch_extreme']:
            extreme_count += 1
        if macd_hist and abs(macd_hist) > 0.5:  # MACD extreme threshold
            extreme_count += 1
        
        extremes['triple_extreme'] = extreme_count >= 2
        
        return extremes
    
    def _analyze_volatility(self, candles: List, indicators: Dict) -> Dict:
        """ATR expansion ve BB squeeze analizi"""
        volatility = {
            'atr_expansion': False,
            'bb_squeeze': False,
            'volatility_spike': False,
            'spike_ratio': 1.0
        }
        
        # ATR analizi
        atr_value = indicators.get('atr', {}).get('value', 0)
        if atr_value and len(candles) >= 20:
            # Basit ATR ortalaması (gerçek implementasyonda historical ATR kullanılmalı)
            recent_ranges = []
            for i in range(1, min(20, len(candles))):
                candle = candles[-i]
                tr = float(candle.high) - float(candle.low)
                recent_ranges.append(tr)
            
            if recent_ranges:
                avg_range = np.mean(recent_ranges)
                spike_ratio = atr_value / avg_range if avg_range > 0 else 1
                
                volatility['spike_ratio'] = spike_ratio
                volatility['atr_expansion'] = spike_ratio >= self.atr_expansion_threshold
                volatility['volatility_spike'] = volatility['atr_expansion']
        
        # Bollinger Band squeeze
        bb_data = indicators.get('bollinger', {})
        if bb_data:
            upper = bb_data.get('upper', 0)
            lower = bb_data.get('lower', 0)
            middle = bb_data.get('middle', 1)
            
            if upper and lower and middle:
                band_width = ((upper - lower) / middle) * 100
                volatility['bb_squeeze'] = band_width < self.bb_squeeze_threshold
                volatility['band_width'] = band_width
        
        return volatility
    
    def _calculate_exhaustion_score(self, consecutive: Dict, anomaly: Dict,
                                   indicators: Dict, volatility: Dict) -> Tuple[float, str]:
        """Exhaustion skorunu hesapla"""
        score = 0.0
        weights = {
            'consecutive': 0.3,
            'anomaly': 0.2,
            'indicators': 0.3,
            'volatility': 0.2
        }
        
        # 1. Ardışık mum skoru
        if consecutive['pattern'] != 'NONE':
            consecutive_score = min(max(consecutive['bullish_count'], 
                                      consecutive['bearish_count']) / 7, 1.0)
            score += weights['consecutive'] * consecutive_score
        
        # 2. Anomali skoru
        if anomaly['anomaly_detected']:
            anomaly_score = min(anomaly['size_ratio'] / 3, 1.0)
            if anomaly['rejection']:
                anomaly_score = min(anomaly_score * 1.5, 1.0)
            score += weights['anomaly'] * anomaly_score
        
        # 3. Ekstrem gösterge skoru
        if indicators['triple_extreme']:
            score += weights['indicators'] * 1.0
        elif indicators['rsi_extreme'] or indicators['stoch_extreme']:
            score += weights['indicators'] * 0.6
        
        # 4. Volatilite skoru
        if volatility['volatility_spike']:
            score += weights['volatility'] * volatility['spike_ratio'] / 2
        if volatility['bb_squeeze']:
            score += weights['volatility'] * 0.5
        
        # Exhaustion tipi belirleme
        exhaustion_type = 'NONE'
        if score >= 0.4:
            if consecutive['pattern'] == 'BULLISH_EXHAUSTION' or indicators['extreme_type'] == 'OVERBOUGHT':
                exhaustion_type = 'BEARISH'  # Bullish exhaustion = Bearish reversal beklentisi
            elif consecutive['pattern'] == 'BEARISH_EXHAUSTION' or indicators['extreme_type'] == 'OVERSOLD':
                exhaustion_type = 'BULLISH'  # Bearish exhaustion = Bullish reversal beklentisi
        
        return round(score, 3), exhaustion_type
    
    def _generate_exhaustion_signals(self, consecutive: Dict, anomaly: Dict,
                                    indicators: Dict, volatility: Dict) -> List[str]:
        """Exhaustion sinyalleri oluştur"""
        signals = []
        
        # Ardışık mum sinyali
        if consecutive['pattern'] == 'BULLISH_EXHAUSTION':
            signals.append(f"{consecutive['bullish_count']} ardışık yeşil mum - Tepe yakın")
        elif consecutive['pattern'] == 'BEARISH_EXHAUSTION':
            signals.append(f"{consecutive['bearish_count']} ardışık kırmızı mum - Dip yakın")
        
        # Dev mum sinyali
        if anomaly['anomaly_detected']:
            if anomaly['type'] == 'BULLISH_SPIKE':
                signals.append(f"Bullish spike (x{anomaly['size_ratio']:.1f}) - Dikkat")
            elif anomaly['type'] == 'BEARISH_SPIKE':
                signals.append(f"Bearish spike (x{anomaly['size_ratio']:.1f}) - Dikkat")
            
            if anomaly['rejection']:
                signals.append("Güçlü rejection mumu tespit edildi")
        
        # Gösterge sinyalleri
        if indicators['triple_extreme']:
            signals.append(f"Çoklu ekstrem gösterge - {indicators['extreme_type']}")
        elif indicators['rsi_extreme']:
            signals.append(f"RSI ekstrem bölgede - {indicators['extreme_type']}")
        elif indicators['stoch_extreme']:
            signals.append(f"Stochastic ekstrem bölgede - {indicators['extreme_type']}")
        
        # Volatilite sinyalleri
        if volatility['volatility_spike']:
            signals.append(f"Volatilite spike (ATR x{volatility['spike_ratio']:.1f})")
        if volatility['bb_squeeze']:
            signals.append("Bollinger Band squeeze - Patlama beklentisi")
        
        return signals
    
    def _generate_recommendation(self, exhaustion_type: str, 
                                score: float, signals: List[str]) -> str:
        """Momentum exhaustion önerisi"""
        if score < 0.4:
            return "Momentum güçlü - Trend devam edebilir"
        elif score < 0.6:
            if exhaustion_type == 'BULLISH':
                return "Momentum zayıflıyor - Dip yakın olabilir"
            elif exhaustion_type == 'BEARISH':
                return "Momentum zayıflıyor - Tepe yakın olabilir"
            else:
                return "Momentum kararsız - Dikkatli ol"
        else:
            if exhaustion_type == 'BULLISH':
                return "GÜÇLÜ DİP SİNYALİ - Alım fırsatı yakın"
            elif exhaustion_type == 'BEARISH':
                return "GÜÇLÜ TEPE SİNYALİ - Satış fırsatı yakın"
            else:
                return "Yüksek exhaustion - Dönüş beklentisi"
    
    def _calculate_momentum_strength(self, candles: List) -> float:
        """Momentum gücü hesapla"""
        if len(candles) < 10:
            return 0.0
        
        # Son 10 mumun yönsel hareketi
        bullish_moves = 0
        bearish_moves = 0
        total_move = 0
        
        for i in range(1, min(10, len(candles))):
            candle = candles[-i]
            prev_candle = candles[-i-1]
            
            change = float(candle.close) - float(prev_candle.close)
            total_move += abs(change)
            
            if change > 0:
                bullish_moves += change
            else:
                bearish_moves += abs(change)
        
        if total_move > 0:
            if bullish_moves > bearish_moves:
                return (bullish_moves / total_move) * 100
            else:
                return -(bearish_moves / total_move) * 100
        
        return 0.0
    
    def _empty_exhaustion_result(self) -> Dict:
        """Boş exhaustion sonucu"""
        return {
            'exhaustion_detected': False,
            'exhaustion_type': 'NONE',
            'exhaustion_score': 0.0,
            'signals': [],
            'consecutive_candles': {'bullish_count': 0, 'bearish_count': 0, 'pattern': 'NONE'},
            'candle_anomaly': {'anomaly_detected': False, 'type': 'NONE'},
            'extreme_indicators': {'rsi_extreme': False, 'stoch_extreme': False, 'triple_extreme': False},
            'volatility_analysis': {'atr_expansion': False, 'bb_squeeze': False, 'volatility_spike': False},
            'recommendation': 'Yetersiz veri',
            'details': {
                'signal_count': 0,
                'history': [],
                'momentum_strength': 0.0
            }
        }