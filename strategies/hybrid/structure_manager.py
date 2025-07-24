"""
Structure Manager - Market structure break analizi
"""
from typing import Dict, List, Any, Optional, Tuple
import logging
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)


class StructureManager:
    """Market structure (HH/HL, LL/LH) analizi ve structure break tespiti"""
    
    def __init__(self):
        # Structure analiz parametreleri
        self.min_swing_percent = 0.5  # Minimum %0.5 hareket
        self.lookback_candles = 20
        self.structure_history = deque(maxlen=10)
        
    def analyze_market_structure(self, 
                                candles: List,
                                current_price: float) -> Dict[str, Any]:
        """
        Market structure analizi yap
        
        Returns:
            {
                'current_structure': str (BULLISH/BEARISH/NEUTRAL),
                'structure_break': bool,
                'break_type': str (BULLISH_BREAK/BEARISH_BREAK/NONE),
                'key_levels': Dict[str, float],
                'swing_points': List[Dict],
                'pullback_zone': bool,
                'entry_zone': Dict,
                'confidence': float,
                'details': Dict
            }
        """
        if not candles or len(candles) < self.lookback_candles:
            return self._empty_structure_result()
            
        # Swing noktalarını bul
        swing_points = self._find_swing_points(candles)
        
        if len(swing_points) < 4:
            return self._empty_structure_result()
            
        # Market structure belirle
        current_structure = self._determine_structure(swing_points)
        
        # Structure break kontrolü
        structure_break, break_type = self._check_structure_break(
            swing_points, current_price, current_structure
        )
        
        # Key level'ları belirle
        key_levels = self._identify_key_levels(swing_points, current_price)
        
        # Pullback zone kontrolü
        pullback_zone, entry_zone = self._check_pullback_zone(
            current_price, key_levels, structure_break, break_type
        )
        
        # Güven skoru
        confidence = self._calculate_confidence(
            swing_points, structure_break, pullback_zone
        )
        
        # Structure history güncelle
        self.structure_history.append({
            'structure': current_structure,
            'break': structure_break,
            'timestamp': candles[-1].timestamp if hasattr(candles[-1], 'timestamp') else None
        })
        
        return {
            'current_structure': current_structure,
            'structure_break': structure_break,
            'break_type': break_type,
            'key_levels': key_levels,
            'swing_points': self._format_swing_points(swing_points),
            'pullback_zone': pullback_zone,
            'entry_zone': entry_zone,
            'confidence': confidence,
            'details': {
                'swing_count': len(swing_points),
                'last_swing': swing_points[-1] if swing_points else None,
                'structure_history': list(self.structure_history)[-3:],
                'trend_strength': self._calculate_trend_strength(swing_points)
            }
        }
    
    def _find_swing_points(self, candles: List) -> List[Dict]:
        """Swing high ve low noktalarını bul"""
        swing_points = []
        
        for i in range(2, len(candles) - 2):
            # Swing High kontrolü
            if (candles[i].high > candles[i-1].high and 
                candles[i].high > candles[i-2].high and
                candles[i].high > candles[i+1].high and 
                candles[i].high > candles[i+2].high):
                
                swing_points.append({
                    'type': 'HIGH',
                    'price': float(candles[i].high),
                    'index': i,
                    'candle': candles[i]
                })
            
            # Swing Low kontrolü
            elif (candles[i].low < candles[i-1].low and 
                  candles[i].low < candles[i-2].low and
                  candles[i].low < candles[i+1].low and 
                  candles[i].low < candles[i+2].low):
                
                swing_points.append({
                    'type': 'LOW',
                    'price': float(candles[i].low),
                    'index': i,
                    'candle': candles[i]
                })
        
        # Minimum swing gücü filtresi
        filtered_swings = []
        for i, swing in enumerate(swing_points):
            if i == 0:
                filtered_swings.append(swing)
                continue
                
            prev_swing = filtered_swings[-1]
            price_change = abs(swing['price'] - prev_swing['price'])
            # Division by zero kontrolü
            if prev_swing['price'] != 0:
                percent_change = (price_change / prev_swing['price']) * 100
            else:
                percent_change = 0
            
            if percent_change >= self.min_swing_percent:
                filtered_swings.append(swing)
        
        return filtered_swings
    
    def _determine_structure(self, swing_points: List[Dict]) -> str:
        """HH/HL veya LL/LH pattern'e göre structure belirle"""
        if len(swing_points) < 4:
            return "NEUTRAL"
        
        # Son 4 swing point'i al
        recent_swings = swing_points[-4:]
        
        # High ve Low'ları ayır
        highs = [s for s in recent_swings if s['type'] == 'HIGH']
        lows = [s for s in recent_swings if s['type'] == 'LOW']
        
        if len(highs) >= 2 and len(lows) >= 2:
            # Bullish structure: Higher High + Higher Low
            if (highs[-1]['price'] > highs[-2]['price'] and 
                lows[-1]['price'] > lows[-2]['price']):
                return "BULLISH"
            
            # Bearish structure: Lower Low + Lower High
            elif (lows[-1]['price'] < lows[-2]['price'] and 
                  highs[-1]['price'] < highs[-2]['price']):
                return "BEARISH"
        
        return "NEUTRAL"
    
    def _check_structure_break(self, swing_points: List[Dict], 
                              current_price: float, 
                              current_structure: str) -> Tuple[bool, str]:
        """Structure break kontrolü"""
        if len(swing_points) < 2:
            return False, "NONE"
        
        # Son swing point'leri al
        last_high = None
        last_low = None
        
        for swing in reversed(swing_points):
            if swing['type'] == 'HIGH' and last_high is None:
                last_high = swing
            elif swing['type'] == 'LOW' and last_low is None:
                last_low = swing
            
            if last_high and last_low:
                break
        
        # Bullish structure break: Önceki high'ı kırma
        if current_structure == "BEARISH" and last_high:
            if current_price > last_high['price']:
                return True, "BULLISH_BREAK"
        
        # Bearish structure break: Önceki low'u kırma
        elif current_structure == "BULLISH" and last_low:
            if current_price < last_low['price']:
                return True, "BEARISH_BREAK"
        
        return False, "NONE"
    
    def _identify_key_levels(self, swing_points: List[Dict], 
                            current_price: float) -> Dict[str, float]:
        """Önemli seviyeleri belirle"""
        key_levels = {
            'resistance': [],
            'support': [],
            'nearest_resistance': None,
            'nearest_support': None
        }
        
        # Tüm high ve low'ları topla
        highs = [s['price'] for s in swing_points if s['type'] == 'HIGH']
        lows = [s['price'] for s in swing_points if s['type'] == 'LOW']
        
        # Resistance seviyeleri (mevcut fiyatın üstündeki high'lar)
        key_levels['resistance'] = sorted([h for h in highs if h > current_price])
        if key_levels['resistance']:
            key_levels['nearest_resistance'] = key_levels['resistance'][0]
        
        # Support seviyeleri (mevcut fiyatın altındaki low'lar)
        key_levels['support'] = sorted([l for l in lows if l < current_price], reverse=True)
        if key_levels['support']:
            key_levels['nearest_support'] = key_levels['support'][0]
        
        return key_levels
    
    def _check_pullback_zone(self, current_price: float, 
                            key_levels: Dict, structure_break: bool,
                            break_type: str) -> Tuple[bool, Dict]:
        """Pullback zone ve entry fırsatı kontrolü"""
        pullback_zone = False
        entry_zone = {
            'active': False,
            'type': None,
            'entry_price': None,
            'stop_loss': None,
            'risk_reward': 0
        }
        
        # Structure break sonrası pullback kontrolü
        if structure_break:
            if break_type == "BULLISH_BREAK" and key_levels['nearest_support']:
                # Bullish break sonrası support'a pullback
                distance_to_support = abs(current_price - key_levels['nearest_support'])
                support_proximity = (distance_to_support / current_price) * 100
                
                if support_proximity < 0.5:  # %0.5'ten yakın
                    pullback_zone = True
                    entry_zone = {
                        'active': True,
                        'type': 'BUY',
                        'entry_price': current_price,
                        'stop_loss': key_levels['nearest_support'] * 0.995,
                        'risk_reward': 2.0
                    }
            
            elif break_type == "BEARISH_BREAK" and key_levels['nearest_resistance']:
                # Bearish break sonrası resistance'a pullback
                distance_to_resistance = abs(current_price - key_levels['nearest_resistance'])
                resistance_proximity = (distance_to_resistance / current_price) * 100
                
                if resistance_proximity < 0.5:  # %0.5'ten yakın
                    pullback_zone = True
                    entry_zone = {
                        'active': True,
                        'type': 'SELL',
                        'entry_price': current_price,
                        'stop_loss': key_levels['nearest_resistance'] * 1.005,
                        'risk_reward': 2.0
                    }
        
        return pullback_zone, entry_zone
    
    def _calculate_confidence(self, swing_points: List[Dict], 
                             structure_break: bool, 
                             pullback_zone: bool) -> float:
        """Structure analizi güven skoru"""
        confidence = 0.5  # Base confidence
        
        # Swing point sayısına göre
        if len(swing_points) >= 6:
            confidence += 0.1
        if len(swing_points) >= 8:
            confidence += 0.1
        
        # Structure break varsa
        if structure_break:
            confidence += 0.2
        
        # Pullback zone'daysa
        if pullback_zone:
            confidence += 0.1
        
        # Son 3 structure tutarlıysa
        if len(self.structure_history) >= 3:
            recent_structures = [h['structure'] for h in list(self.structure_history)[-3:]]
            if len(set(recent_structures)) == 1:  # Hepsi aynı
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_trend_strength(self, swing_points: List[Dict]) -> float:
        """Trend gücünü hesapla"""
        if len(swing_points) < 4:
            return 0.0
        
        # Son 4 swing'in fiyat değişimlerini hesapla
        price_changes = []
        for i in range(1, min(4, len(swing_points))):
            change = (swing_points[-i]['price'] - swing_points[-i-1]['price']) / swing_points[-i-1]['price']
            price_changes.append(change)
        
        # Ortalama değişim = trend gücü
        avg_change = np.mean(np.abs(price_changes))
        return min(avg_change * 100, 100)  # Yüzde olarak, max 100
    
    def _format_swing_points(self, swing_points: List[Dict]) -> List[Dict]:
        """Swing point'leri formatla"""
        formatted = []
        for i, point in enumerate(swing_points[-5:]):  # Son 5 swing
            formatted.append({
                'type': point['type'],
                'price': point['price'],
                'index': point['index'],
                'order': i + 1
            })
        return formatted
    
    def _empty_structure_result(self) -> Dict:
        """Boş structure sonucu"""
        return {
            'current_structure': 'NEUTRAL',
            'structure_break': False,
            'break_type': 'NONE',
            'key_levels': {
                'resistance': [],
                'support': [],
                'nearest_resistance': None,
                'nearest_support': None
            },
            'swing_points': [],
            'pullback_zone': False,
            'entry_zone': {
                'active': False,
                'type': None,
                'entry_price': None,
                'stop_loss': None,
                'risk_reward': 0
            },
            'confidence': 0.0,
            'details': {
                'swing_count': 0,
                'last_swing': None,
                'structure_history': [],
                'trend_strength': 0.0
            }
        }