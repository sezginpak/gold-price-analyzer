"""
Smart Money Manager - Kurumsal hareketleri ve manipülasyonları tespit
"""
from typing import Dict, List, Any, Optional, Tuple
import logging
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)


class SmartMoneyManager:
    """Smart money konseptleri: Stop hunt, order block, fair value gap vb."""
    
    def __init__(self):
        # Parametreler
        self.stop_hunt_threshold = 0.3  # %0.3 spike
        self.order_block_min_size = 0.5  # %0.5 minimum blok büyüklüğü
        self.fvg_min_gap = 0.1  # %0.1 minimum gap
        self.liquidity_sweep_pct = 0.2  # %0.2 sweep mesafesi
        
        # Geçmiş veriler
        self.smart_money_history = deque(maxlen=50)
        self.order_blocks = deque(maxlen=10)
        
    def analyze_smart_money(self, 
                           candles: List,
                           key_levels: Dict) -> Dict[str, Any]:
        """
        Smart money konseptleri analizi
        
        Returns:
            {
                'stop_hunt_detected': bool,
                'stop_hunt_details': Dict,
                'order_blocks': List[Dict],
                'fair_value_gaps': List[Dict],
                'liquidity_sweeps': List[Dict],
                'manipulation_score': float,
                'smart_money_direction': str,
                'entry_zones': List[Dict],
                'recommendation': str,
                'details': Dict
            }
        """
        if not candles or len(candles) < 20:
            return self._empty_smart_money_result()
        
        # 1. Stop hunt pattern tespiti
        stop_hunt_details = self._detect_stop_hunt(candles, key_levels)
        
        # 2. Order block tespiti
        order_blocks = self._find_order_blocks(candles)
        
        # 3. Fair Value Gap (FVG) tespiti
        fair_value_gaps = self._find_fair_value_gaps(candles)
        
        # 4. Liquidity sweep analizi
        liquidity_sweeps = self._analyze_liquidity_sweeps(candles, key_levels)
        
        # 5. Manipulation skoru hesapla
        manipulation_score = self._calculate_manipulation_score(
            stop_hunt_details, order_blocks, fair_value_gaps, liquidity_sweeps
        )
        
        # 6. Smart money yönü belirle
        smart_money_direction = self._determine_smart_money_direction(
            stop_hunt_details, order_blocks, liquidity_sweeps
        )
        
        # 7. Entry zone'ları belirle
        entry_zones = self._identify_entry_zones(
            order_blocks, fair_value_gaps, stop_hunt_details
        )
        
        # 8. Öneri oluştur
        recommendation = self._generate_recommendation(
            manipulation_score, smart_money_direction, entry_zones
        )
        
        # History güncelle
        self.smart_money_history.append({
            'manipulation_score': manipulation_score,
            'direction': smart_money_direction,
            'timestamp': candles[-1].timestamp if hasattr(candles[-1], 'timestamp') else None
        })
        
        return {
            'stop_hunt_detected': stop_hunt_details['detected'],
            'stop_hunt_details': stop_hunt_details,
            'order_blocks': order_blocks,
            'fair_value_gaps': fair_value_gaps,
            'liquidity_sweeps': liquidity_sweeps,
            'manipulation_score': manipulation_score,
            'smart_money_direction': smart_money_direction,
            'entry_zones': entry_zones,
            'recommendation': recommendation,
            'details': {
                'total_patterns': len(order_blocks) + len(fair_value_gaps) + len(liquidity_sweeps),
                'history': list(self.smart_money_history)[-5:],
                'institutional_bias': self._calculate_institutional_bias(candles)
            }
        }
    
    def _detect_stop_hunt(self, candles: List, key_levels: Dict) -> Dict:
        """Stop hunt pattern tespiti"""
        if len(candles) < 5:
            return {'detected': False, 'type': 'NONE'}
        
        last_candles = candles[-5:]
        current_price = float(candles[-1].close)
        
        # Yakın support/resistance seviyeleri
        nearest_support = key_levels.get('nearest_support')
        nearest_resistance = key_levels.get('nearest_resistance')
        
        stop_hunt = {
            'detected': False,
            'type': 'NONE',
            'level': None,
            'spike_candle': None,
            'recovery': False
        }
        
        # Son 5 mumda spike ve recovery kontrolü
        for i in range(len(last_candles) - 1):
            candle = last_candles[i]
            high = float(candle.high)
            low = float(candle.low)
            
            # Bullish stop hunt (support'u delip toparlanma)
            if nearest_support and not stop_hunt['detected']:
                support_distance = (nearest_support - low) / nearest_support
                if support_distance > self.stop_hunt_threshold / 100:
                    # Recovery kontrolü - sonraki mumlardan en az biri support üzerinde kapanmalı
                    recovery_candles = last_candles[i+1:]
                    for rec_candle in recovery_candles:
                        if float(rec_candle.close) > nearest_support:
                            stop_hunt = {
                                'detected': True,
                                'type': 'BULLISH_STOP_HUNT',
                                'level': nearest_support,
                                'spike_candle': i,
                                'recovery': True,
                                'entry_price': current_price
                            }
                            break
            
            # Bearish stop hunt (resistance'ı delip düşüş)
            if nearest_resistance and not stop_hunt['detected']:
                resistance_distance = (high - nearest_resistance) / nearest_resistance
                if resistance_distance > self.stop_hunt_threshold / 100:
                    # Recovery kontrolü
                    recovery_candles = last_candles[i+1:]
                    for rec_candle in recovery_candles:
                        if float(rec_candle.close) < nearest_resistance:
                            stop_hunt = {
                                'detected': True,
                                'type': 'BEARISH_STOP_HUNT',
                                'level': nearest_resistance,
                                'spike_candle': i,
                                'recovery': True,
                                'entry_price': current_price
                            }
                            break
        
        return stop_hunt
    
    def _find_order_blocks(self, candles: List) -> List[Dict]:
        """Order block (kurumsal blok) tespiti"""
        order_blocks = []
        
        if len(candles) < 10:
            return order_blocks
        
        # Son 20 mumu kontrol et
        search_candles = candles[-20:-1]  # Son hariç
        
        for i in range(1, len(search_candles) - 1):
            prev_candle = search_candles[i-1]
            candle = search_candles[i]
            next_candle = search_candles[i+1]
            
            candle_range = float(candle.high) - float(candle.low)
            candle_body = abs(float(candle.close) - float(candle.open))
            
            # Büyük hacimli mum (body/range oranı yüksek)
            if candle_range > 0 and candle_body / candle_range > 0.7:
                # Bullish order block
                if (float(candle.close) > float(candle.open) and
                    float(next_candle.close) > float(candle.high)):
                    
                    ob_size = (candle_range / float(candle.close)) * 100
                    if ob_size >= self.order_block_min_size:
                        order_blocks.append({
                            'type': 'BULLISH_OB',
                            'high': float(candle.high),
                            'low': float(candle.low),
                            'mid': (float(candle.high) + float(candle.low)) / 2,
                            'strength': min(ob_size / self.order_block_min_size, 2.0),
                            'tested': self._is_level_tested(candles[i+1:], float(candle.low)),
                            'index': len(candles) - 20 + i
                        })
                
                # Bearish order block
                elif (float(candle.close) < float(candle.open) and
                      float(next_candle.close) < float(candle.low)):
                    
                    ob_size = (candle_range / float(candle.close)) * 100
                    if ob_size >= self.order_block_min_size:
                        order_blocks.append({
                            'type': 'BEARISH_OB',
                            'high': float(candle.high),
                            'low': float(candle.low),
                            'mid': (float(candle.high) + float(candle.low)) / 2,
                            'strength': min(ob_size / self.order_block_min_size, 2.0),
                            'tested': self._is_level_tested(candles[i+1:], float(candle.high)),
                            'index': len(candles) - 20 + i
                        })
        
        # En güçlü 3 order block'u tut
        order_blocks.sort(key=lambda x: x['strength'], reverse=True)
        return order_blocks[:3]
    
    def _find_fair_value_gaps(self, candles: List) -> List[Dict]:
        """Fair Value Gap (FVG) tespiti"""
        fair_value_gaps = []
        
        if len(candles) < 3:
            return fair_value_gaps
        
        # Son 15 mumu kontrol et
        for i in range(2, min(15, len(candles))):
            candle1 = candles[-i-1]
            candle2 = candles[-i]
            candle3 = candles[-i+1]
            
            # Bullish FVG: candle1.high < candle3.low
            if float(candle1.high) < float(candle3.low):
                gap_size = float(candle3.low) - float(candle1.high)
                # Division by zero kontrolü
                candle2_close = float(candle2.close)
                if candle2_close != 0:
                    gap_pct = (gap_size / candle2_close) * 100
                else:
                    gap_pct = 0
                
                if gap_pct >= self.fvg_min_gap:
                    fair_value_gaps.append({
                        'type': 'BULLISH_FVG',
                        'top': float(candle3.low),
                        'bottom': float(candle1.high),
                        'mid': (float(candle3.low) + float(candle1.high)) / 2,
                        'size': gap_pct,
                        'filled': self._is_fvg_filled(candles[-i+1:], float(candle1.high), float(candle3.low)),
                        'index': len(candles) - i
                    })
            
            # Bearish FVG: candle1.low > candle3.high
            elif float(candle1.low) > float(candle3.high):
                gap_size = float(candle1.low) - float(candle3.high)
                # Division by zero kontrolü
                candle2_close = float(candle2.close)
                if candle2_close != 0:
                    gap_pct = (gap_size / candle2_close) * 100
                else:
                    gap_pct = 0
                
                if gap_pct >= self.fvg_min_gap:
                    fair_value_gaps.append({
                        'type': 'BEARISH_FVG',
                        'top': float(candle1.low),
                        'bottom': float(candle3.high),
                        'mid': (float(candle1.low) + float(candle3.high)) / 2,
                        'size': gap_pct,
                        'filled': self._is_fvg_filled(candles[-i+1:], float(candle3.high), float(candle1.low)),
                        'index': len(candles) - i
                    })
        
        # En büyük 3 FVG'yi tut
        fair_value_gaps.sort(key=lambda x: x['size'], reverse=True)
        return fair_value_gaps[:3]
    
    def _analyze_liquidity_sweeps(self, candles: List, key_levels: Dict) -> List[Dict]:
        """Liquidity sweep (likidite süpürme) analizi"""
        liquidity_sweeps = []
        
        if len(candles) < 10:
            return liquidity_sweeps
        
        # Son 10 mumda sweep kontrolü
        recent_candles = candles[-10:]
        
        # Equal highs/lows bul
        equal_highs = self._find_equal_levels(recent_candles, 'high')
        equal_lows = self._find_equal_levels(recent_candles, 'low')
        
        current_price = float(candles[-1].close)
        
        # Equal high sweep
        for level in equal_highs:
            for i, candle in enumerate(recent_candles[-5:]):
                if float(candle.high) > level['price'] * (1 + self.liquidity_sweep_pct / 100):
                    # Sweep sonrası düşüş
                    if current_price < level['price']:
                        liquidity_sweeps.append({
                            'type': 'BEARISH_SWEEP',
                            'level': level['price'],
                            'sweep_high': float(candle.high),
                            'count': level['count'],
                            'confirmed': True
                        })
                        break
        
        # Equal low sweep
        for level in equal_lows:
            for i, candle in enumerate(recent_candles[-5:]):
                if float(candle.low) < level['price'] * (1 - self.liquidity_sweep_pct / 100):
                    # Sweep sonrası yükseliş
                    if current_price > level['price']:
                        liquidity_sweeps.append({
                            'type': 'BULLISH_SWEEP',
                            'level': level['price'],
                            'sweep_low': float(candle.low),
                            'count': level['count'],
                            'confirmed': True
                        })
                        break
        
        return liquidity_sweeps
    
    def _calculate_manipulation_score(self, stop_hunt: Dict, order_blocks: List,
                                     fvgs: List, sweeps: List) -> float:
        """Manipulation/kurumsal aktivite skoru"""
        score = 0.0
        
        # Stop hunt (en güçlü sinyal)
        if stop_hunt['detected'] and stop_hunt['recovery']:
            score += 0.4
        
        # Order blocks
        untested_obs = [ob for ob in order_blocks if not ob['tested']]
        score += min(len(untested_obs) * 0.15, 0.3)
        
        # Unfilled FVGs
        unfilled_fvgs = [fvg for fvg in fvgs if not fvg['filled']]
        score += min(len(unfilled_fvgs) * 0.1, 0.2)
        
        # Liquidity sweeps
        score += min(len(sweeps) * 0.1, 0.2)
        
        # History bonus
        if len(self.smart_money_history) >= 3:
            recent_scores = [h['manipulation_score'] for h in list(self.smart_money_history)[-3:]]
            if all(s > 0.5 for s in recent_scores):
                score += 0.1
        
        return min(score, 1.0)
    
    def _determine_smart_money_direction(self, stop_hunt: Dict, 
                                        order_blocks: List, sweeps: List) -> str:
        """Smart money yönünü belirle"""
        bullish_signals = 0
        bearish_signals = 0
        
        # Stop hunt yönü
        if stop_hunt['type'] == 'BULLISH_STOP_HUNT':
            bullish_signals += 2
        elif stop_hunt['type'] == 'BEARISH_STOP_HUNT':
            bearish_signals += 2
        
        # Order block yönleri
        for ob in order_blocks:
            if ob['type'] == 'BULLISH_OB' and not ob['tested']:
                bullish_signals += 1
            elif ob['type'] == 'BEARISH_OB' and not ob['tested']:
                bearish_signals += 1
        
        # Sweep yönleri
        for sweep in sweeps:
            if sweep['type'] == 'BULLISH_SWEEP':
                bullish_signals += 1
            elif sweep['type'] == 'BEARISH_SWEEP':
                bearish_signals += 1
        
        if bullish_signals > bearish_signals:
            return 'BULLISH'
        elif bearish_signals > bullish_signals:
            return 'BEARISH'
        else:
            return 'NEUTRAL'
    
    def _identify_entry_zones(self, order_blocks: List, fvgs: List, 
                             stop_hunt: Dict) -> List[Dict]:
        """Entry zone'ları belirle"""
        entry_zones = []
        
        # Stop hunt entry
        if stop_hunt['detected'] and stop_hunt['recovery']:
            entry_zones.append({
                'type': 'STOP_HUNT_ENTRY',
                'direction': 'BUY' if 'BULLISH' in stop_hunt['type'] else 'SELL',
                'entry_price': stop_hunt.get('entry_price'),
                'stop_loss': stop_hunt['level'],
                'confidence': 0.8
            })
        
        # Order block entries
        for ob in order_blocks[:2]:  # En güçlü 2 OB
            if not ob['tested']:
                entry_zones.append({
                    'type': 'ORDER_BLOCK_ENTRY',
                    'direction': 'BUY' if ob['type'] == 'BULLISH_OB' else 'SELL',
                    'entry_price': ob['mid'],
                    'stop_loss': ob['low'] if ob['type'] == 'BULLISH_OB' else ob['high'],
                    'confidence': 0.6 * ob['strength']
                })
        
        # FVG entries
        for fvg in fvgs[:1]:  # En büyük FVG
            if not fvg['filled']:
                entry_zones.append({
                    'type': 'FVG_ENTRY',
                    'direction': 'BUY' if fvg['type'] == 'BULLISH_FVG' else 'SELL',
                    'entry_price': fvg['mid'],
                    'stop_loss': fvg['bottom'] if fvg['type'] == 'BULLISH_FVG' else fvg['top'],
                    'confidence': 0.5
                })
        
        # Güven skoruna göre sırala
        entry_zones.sort(key=lambda x: x['confidence'], reverse=True)
        return entry_zones[:3]
    
    def _generate_recommendation(self, manipulation_score: float, 
                                direction: str, entry_zones: List) -> str:
        """Smart money analizi önerisi"""
        if manipulation_score < 0.3:
            return "Kurumsal aktivite düşük - Retail dominated"
        elif manipulation_score < 0.6:
            if direction == 'BULLISH':
                return "Orta düzey kurumsal alım - Dikkatli takip"
            elif direction == 'BEARISH':
                return "Orta düzey kurumsal satış - Dikkatli takip"
            else:
                return "Karışık kurumsal aktivite - Bekle"
        else:
            if direction == 'BULLISH' and entry_zones:
                return "GÜÇLÜ KURUMSAL ALIM - Entry zone'ları değerlendir"
            elif direction == 'BEARISH' and entry_zones:
                return "GÜÇLÜ KURUMSAL SATIŞ - Entry zone'ları değerlendir"
            else:
                return "Yüksek manipulation - Stop hunt sonrası bekle"
    
    def _is_level_tested(self, candles: List, level: float) -> bool:
        """Seviyenin test edilip edilmediğini kontrol et"""
        for candle in candles:
            if float(candle.low) <= level <= float(candle.high):
                return True
        return False
    
    def _is_fvg_filled(self, candles: List, bottom: float, top: float) -> bool:
        """FVG'nin doldurulup doldurulmadığını kontrol et"""
        for candle in candles:
            if float(candle.low) <= bottom and float(candle.high) >= top:
                return True
        return False
    
    def _find_equal_levels(self, candles: List, price_type: str) -> List[Dict]:
        """Equal highs/lows bul"""
        levels = []
        threshold = 0.05  # %0.05 tolerans
        
        prices = [float(getattr(c, price_type)) for c in candles]
        
        # Her fiyatı diğerleriyle karşılaştır
        for i, price in enumerate(prices):
            count = 1
            for j, other_price in enumerate(prices):
                if i != j and price != 0:
                    diff_pct = abs(price - other_price) / price * 100
                    if diff_pct <= threshold:
                        count += 1
            
            if count >= 2:  # En az 2 eşit seviye
                # Duplicate kontrolü
                is_duplicate = False
                for level in levels:
                    if price != 0 and abs(level['price'] - price) / price * 100 <= threshold:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    levels.append({
                        'price': price,
                        'count': count,
                        'type': price_type
                    })
        
        return levels
    
    def _calculate_institutional_bias(self, candles: List) -> float:
        """Kurumsal yönelim hesapla (-100 to +100)"""
        if len(candles) < 20:
            return 0.0
        
        # Son 20 mumda büyük mumları say
        large_bullish = 0
        large_bearish = 0
        
        avg_size = np.mean([abs(float(c.close) - float(c.open)) for c in candles[-20:]])
        
        for candle in candles[-20:]:
            size = abs(float(candle.close) - float(candle.open))
            if size > avg_size * 1.5:
                if float(candle.close) > float(candle.open):
                    large_bullish += 1
                else:
                    large_bearish += 1
        
        total_large = large_bullish + large_bearish
        if total_large > 0:
            bias = ((large_bullish - large_bearish) / total_large) * 100
            return bias
        
        return 0.0
    
    def _empty_smart_money_result(self) -> Dict:
        """Boş smart money sonucu"""
        return {
            'stop_hunt_detected': False,
            'stop_hunt_details': {'detected': False, 'type': 'NONE'},
            'order_blocks': [],
            'fair_value_gaps': [],
            'liquidity_sweeps': [],
            'manipulation_score': 0.0,
            'smart_money_direction': 'NEUTRAL',
            'entry_zones': [],
            'recommendation': 'Yetersiz veri',
            'details': {
                'total_patterns': 0,
                'history': [],
                'institutional_bias': 0.0
            }
        }