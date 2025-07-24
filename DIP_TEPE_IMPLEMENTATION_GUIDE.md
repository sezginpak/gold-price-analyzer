# Dip/Tepe Yakalama - Detaylı Implementation Kılavuzu

## 🏗️ Proje Yapısı ve Entegrasyon Noktaları

### Mevcut Mimari ile Entegrasyon
```
analyzers/
├── gram_altin_analyzer.py      # Divergence eklenecek
├── timeframe_confluence.py     # YENİ - Multiple TF analizi
├── market_structure.py         # YENİ - Structure break tespiti
└── smart_money_analyzer.py     # YENİ - Likidite havuzları

indicators/
├── divergence.py              # YENİ - RSI/MACD divergence
├── momentum_exhaustion.py     # YENİ - Momentum tükenmesi
└── swing_points.py           # YENİ - HH/HL/LL/LH tespiti

strategies/
└── hybrid_strategy.py        # Tüm yeni analizler buraya entegre edilecek
```

## 📦 1. Divergence Analizi Implementation

### 1.1 Yeni Dosya: `indicators/divergence.py`

```python
"""
Divergence (Uyumsuzluk) Tespit Modülü
RSI ve MACD divergence tespiti için gelişmiş algoritmalar
"""
from typing import List, Dict, Tuple, Optional
import numpy as np
from decimal import Decimal
import logging
from utils import timezone

logger = logging.getLogger(__name__)

class DivergenceDetector:
    """RSI ve MACD divergence tespiti"""
    
    def __init__(self, lookback_period: int = 5, min_swing_strength: float = 0.02):
        """
        Args:
            lookback_period: Swing noktaları için geriye bakma periyodu
            min_swing_strength: Minimum swing gücü (fiyatın %'si olarak)
        """
        self.lookback_period = lookback_period
        self.min_swing_strength = min_swing_strength
    
    def detect_rsi_divergence(self, prices: List[float], rsi_values: List[float]) -> Dict[str, Any]:
        """
        RSI divergence tespiti
        
        Returns:
            {
                'bullish_divergence': bool,
                'bearish_divergence': bool,
                'divergence_strength': float (0-5),
                'divergence_points': List[Dict],
                'confidence': float (0-1)
            }
        """
        if len(prices) < self.lookback_period * 2 or len(rsi_values) < self.lookback_period * 2:
            return self._empty_divergence_result()
        
        # Swing noktalarını tespit et
        price_swings = self._find_swing_points(prices)
        rsi_swings = self._find_swing_points(rsi_values)
        
        # Divergence analizi
        bullish_div = self._check_bullish_divergence(price_swings, rsi_swings)
        bearish_div = self._check_bearish_divergence(price_swings, rsi_swings)
        
        # Güç hesaplama
        strength = self._calculate_divergence_strength(
            price_swings, rsi_swings, bullish_div, bearish_div
        )
        
        return {
            'bullish_divergence': bullish_div['found'],
            'bearish_divergence': bearish_div['found'],
            'divergence_strength': strength,
            'divergence_points': bullish_div['points'] + bearish_div['points'],
            'confidence': self._calculate_confidence(bullish_div, bearish_div, strength)
        }
    
    def _find_swing_points(self, data: List[float]) -> Dict[str, List[Dict]]:
        """Swing high ve low noktalarını tespit et"""
        highs = []
        lows = []
        
        for i in range(self.lookback_period, len(data) - self.lookback_period):
            # Swing High kontrolü
            is_high = True
            for j in range(1, self.lookback_period + 1):
                if data[i] <= data[i-j] or data[i] <= data[i+j]:
                    is_high = False
                    break
            
            if is_high:
                highs.append({
                    'index': i,
                    'value': data[i],
                    'strength': self._calculate_swing_strength(data, i, 'high')
                })
            
            # Swing Low kontrolü
            is_low = True
            for j in range(1, self.lookback_period + 1):
                if data[i] >= data[i-j] or data[i] >= data[i+j]:
                    is_low = False
                    break
            
            if is_low:
                lows.append({
                    'index': i,
                    'value': data[i],
                    'strength': self._calculate_swing_strength(data, i, 'low')
                })
        
        return {'highs': highs, 'lows': lows}
    
    def _check_bullish_divergence(self, price_swings: Dict, rsi_swings: Dict) -> Dict:
        """
        Bullish Divergence: Fiyat LL (Lower Low), RSI HL (Higher Low)
        """
        price_lows = price_swings['lows']
        rsi_lows = rsi_swings['lows']
        
        if len(price_lows) < 2 or len(rsi_lows) < 2:
            return {'found': False, 'points': []}
        
        # Son iki low'u karşılaştır
        latest_price_low = price_lows[-1]
        prev_price_low = price_lows[-2]
        
        # RSI low'larını eşleştir (index yakınlığına göre)
        latest_rsi_low = self._find_closest_swing(rsi_lows, latest_price_low['index'])
        prev_rsi_low = self._find_closest_swing(rsi_lows, prev_price_low['index'])
        
        if not latest_rsi_low or not prev_rsi_low:
            return {'found': False, 'points': []}
        
        # Bullish divergence kontrolü
        price_makes_ll = latest_price_low['value'] < prev_price_low['value']
        rsi_makes_hl = latest_rsi_low['value'] > prev_rsi_low['value']
        
        if price_makes_ll and rsi_makes_hl:
            return {
                'found': True,
                'points': [{
                    'type': 'bullish',
                    'price_point1': prev_price_low,
                    'price_point2': latest_price_low,
                    'rsi_point1': prev_rsi_low,
                    'rsi_point2': latest_rsi_low,
                    'timestamp': timezone.now()
                }]
            }
        
        return {'found': False, 'points': []}
    
    def _check_bearish_divergence(self, price_swings: Dict, rsi_swings: Dict) -> Dict:
        """
        Bearish Divergence: Fiyat HH (Higher High), RSI LH (Lower High)
        """
        price_highs = price_swings['highs']
        rsi_highs = rsi_swings['highs']
        
        if len(price_highs) < 2 or len(rsi_highs) < 2:
            return {'found': False, 'points': []}
        
        # Son iki high'ı karşılaştır
        latest_price_high = price_highs[-1]
        prev_price_high = price_highs[-2]
        
        # RSI high'larını eşleştir
        latest_rsi_high = self._find_closest_swing(rsi_highs, latest_price_high['index'])
        prev_rsi_high = self._find_closest_swing(rsi_highs, prev_price_high['index'])
        
        if not latest_rsi_high or not prev_rsi_high:
            return {'found': False, 'points': []}
        
        # Bearish divergence kontrolü
        price_makes_hh = latest_price_high['value'] > prev_price_high['value']
        rsi_makes_lh = latest_rsi_high['value'] < prev_rsi_high['value']
        
        if price_makes_hh and rsi_makes_lh:
            return {
                'found': True,
                'points': [{
                    'type': 'bearish',
                    'price_point1': prev_price_high,
                    'price_point2': latest_price_high,
                    'rsi_point1': prev_rsi_high,
                    'rsi_point2': latest_rsi_high,
                    'timestamp': timezone.now()
                }]
            }
        
        return {'found': False, 'points': []}
    
    def _calculate_divergence_strength(self, price_swings: Dict, rsi_swings: Dict,
                                     bullish: Dict, bearish: Dict) -> float:
        """Divergence gücünü 1-5 arası skorla"""
        if not bullish['found'] and not bearish['found']:
            return 0
        
        strength = 2.5  # Başlangıç skoru
        
        # Divergence açısı (fiyat ve RSI arasındaki fark)
        if bullish['found']:
            div_point = bullish['points'][0]
            price_diff = abs(div_point['price_point2']['value'] - div_point['price_point1']['value'])
            rsi_diff = abs(div_point['rsi_point2']['value'] - div_point['rsi_point1']['value'])
            
            # Fark ne kadar büyükse divergence o kadar güçlü
            if rsi_diff > 10:  # RSI farkı 10'dan büyük
                strength += 1
            if price_diff / div_point['price_point1']['value'] > 0.02:  # %2'den büyük fiyat farkı
                strength += 0.5
                
        elif bearish['found']:
            div_point = bearish['points'][0]
            price_diff = abs(div_point['price_point2']['value'] - div_point['price_point1']['value'])
            rsi_diff = abs(div_point['rsi_point2']['value'] - div_point['rsi_point1']['value'])
            
            if rsi_diff > 10:
                strength += 1
            if price_diff / div_point['price_point1']['value'] > 0.02:
                strength += 0.5
        
        # Swing gücü
        avg_swing_strength = np.mean([s['strength'] for s in price_swings['highs'] + price_swings['lows']])
        if avg_swing_strength > 0.03:  # %3'ten güçlü swing'ler
            strength += 0.5
        
        return min(5.0, max(1.0, strength))
    
    def _find_closest_swing(self, swings: List[Dict], target_index: int, max_distance: int = 5) -> Optional[Dict]:
        """En yakın swing noktasını bul"""
        closest = None
        min_distance = float('inf')
        
        for swing in swings:
            distance = abs(swing['index'] - target_index)
            if distance < min_distance and distance <= max_distance:
                min_distance = distance
                closest = swing
        
        return closest
    
    def _calculate_swing_strength(self, data: List[float], index: int, swing_type: str) -> float:
        """Swing noktasının gücünü hesapla"""
        if swing_type == 'high':
            # Yüksekten önceki ve sonraki en düşük değerleri bul
            left_low = min(data[max(0, index-self.lookback_period):index])
            right_low = min(data[index+1:min(len(data), index+self.lookback_period+1)])
            avg_low = (left_low + right_low) / 2
            strength = (data[index] - avg_low) / data[index]
        else:  # low
            # Düşükten önceki ve sonraki en yüksek değerleri bul
            left_high = max(data[max(0, index-self.lookback_period):index])
            right_high = max(data[index+1:min(len(data), index+self.lookback_period+1)])
            avg_high = (left_high + right_high) / 2
            strength = (avg_high - data[index]) / data[index]
        
        return strength
    
    def _calculate_confidence(self, bullish: Dict, bearish: Dict, strength: float) -> float:
        """Divergence güven skoru"""
        if not bullish['found'] and not bearish['found']:
            return 0
        
        # Temel güven = güç / 5
        confidence = strength / 5
        
        # Yakınlık bonusu (son mumlardan divergence daha güvenilir)
        if bullish['found']:
            recency = bullish['points'][0]['price_point2']['index']
        else:
            recency = bearish['points'][0]['price_point2']['index']
        
        # Son 10 mumda ise bonus
        if recency >= len(prices) - 10:
            confidence *= 1.2
        
        return min(1.0, confidence)
    
    def _empty_divergence_result(self) -> Dict:
        """Boş divergence sonucu"""
        return {
            'bullish_divergence': False,
            'bearish_divergence': False,
            'divergence_strength': 0,
            'divergence_points': [],
            'confidence': 0
        }

    def detect_hidden_divergence(self, prices: List[float], rsi_values: List[float]) -> Dict[str, Any]:
        """
        Hidden Divergence: Trend devam sinyali
        Hidden Bullish: Fiyat HL, RSI LL (uptrend devamı)
        Hidden Bearish: Fiyat LH, RSI HH (downtrend devamı)
        """
        # Implementation için regular divergence'a benzer mantık
        # Ancak ters koşullar aranır
        pass  # TODO: Implement
```

### 1.2 gram_altin_analyzer.py'ye Entegrasyon

```python
# gram_altin_analyzer.py içine eklenecek

from indicators.divergence import DivergenceDetector

class GramAltinAnalyzer:
    def __init__(self):
        # Mevcut init kodları...
        self.divergence_detector = DivergenceDetector(lookback_period=5)
    
    def analyze(self, candles: List[GramAltinCandle]) -> Dict[str, Any]:
        # Mevcut analiz kodları...
        
        # Divergence analizi ekle
        if len(prices) >= 20 and rsi_value is not None:
            divergence_result = self.divergence_detector.detect_rsi_divergence(
                prices.tolist()[-50:],  # Son 50 mum
                self.rsi.get_values()[-50:]  # Son 50 RSI değeri
            )
        else:
            divergence_result = self.divergence_detector._empty_divergence_result()
        
        # Sonuçlara ekle
        result['divergence'] = divergence_result
        
        # Sinyal üretiminde kullan
        if divergence_result['bullish_divergence'] and divergence_result['divergence_strength'] >= 3:
            buy_signals += 3  # Güçlü bullish divergence
        elif divergence_result['bearish_divergence'] and divergence_result['divergence_strength'] >= 3:
            sell_signals += 3  # Güçlü bearish divergence
```

## 📦 2. Multiple Timeframe Confluence Implementation

### 2.1 Yeni Dosya: `analyzers/timeframe_confluence.py`

```python
"""
Multiple Timeframe Confluence Analyzer
Farklı timeframe'lerdeki sinyallerin uyumunu kontrol eder
"""
from typing import Dict, List, Optional, Tuple
import logging
from decimal import Decimal
from collections import defaultdict
from utils import timezone
from storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger(__name__)

class TimeframeConfluenceAnalyzer:
    """Çoklu zaman dilimi uyum analizi"""
    
    # Timeframe hiyerarşisi ve ağırlıkları
    TIMEFRAME_HIERARCHY = {
        "15m": {"parent": "1h", "weight": 0.2, "required_confirmation": ["1h"]},
        "1h": {"parent": "4h", "weight": 0.3, "required_confirmation": ["4h"]},
        "4h": {"parent": "1d", "weight": 0.35, "required_confirmation": ["1d"]},
        "1d": {"parent": None, "weight": 0.15, "required_confirmation": []}
    }
    
    def __init__(self, storage: SQLiteStorage):
        self.storage = storage
        self.confluence_cache = {}
    
    def analyze_confluence(self, current_timeframe: str, 
                          current_signal: str,
                          current_analysis: Dict) -> Dict[str, Any]:
        """
        Timeframe uyumunu analiz et
        
        Returns:
            {
                'confluence_score': float (0-100),
                'parent_confirmation': bool,
                'conflicting_timeframes': List[str],
                'supporting_timeframes': List[str],
                'major_levels': Dict[str, List[float]],
                'recommendation': str,
                'details': Dict
            }
        """
        # Tüm timeframe'lerdeki son analizleri al
        all_analyses = self._get_all_timeframe_analyses()
        
        # Hiyerarşik onay kontrolü
        parent_confirmation = self._check_parent_confirmation(
            current_timeframe, current_signal, all_analyses
        )
        
        # Confluence skoru hesapla
        confluence_score = self._calculate_confluence_score(
            current_timeframe, current_signal, all_analyses
        )
        
        # Çelişen ve destekleyen timeframe'leri bul
        conflicts, supports = self._find_conflicts_and_supports(
            current_signal, all_analyses
        )
        
        # Major seviyeleri topla
        major_levels = self._collect_major_levels(all_analyses)
        
        # Öneri oluştur
        recommendation = self._generate_recommendation(
            current_timeframe, current_signal, confluence_score, 
            parent_confirmation, len(conflicts)
        )
        
        return {
            'confluence_score': confluence_score,
            'parent_confirmation': parent_confirmation,
            'conflicting_timeframes': conflicts,
            'supporting_timeframes': supports,
            'major_levels': major_levels,
            'recommendation': recommendation,
            'details': {
                'all_timeframe_signals': {tf: a.get('signal', 'HOLD') 
                                         for tf, a in all_analyses.items()},
                'all_timeframe_trends': {tf: a.get('gram_analysis', {}).get('trend', 'NEUTRAL') 
                                        for tf, a in all_analyses.items()},
                'confluence_breakdown': self._get_confluence_breakdown(all_analyses)
            }
        }
    
    def _get_all_timeframe_analyses(self) -> Dict[str, Dict]:
        """Tüm timeframe'lerdeki son analizleri getir"""
        analyses = {}
        
        for timeframe in self.TIMEFRAME_HIERARCHY.keys():
            latest = self.storage.get_latest_hybrid_analysis(timeframe)
            if latest:
                analyses[timeframe] = latest
        
        return analyses
    
    def _check_parent_confirmation(self, timeframe: str, signal: str, 
                                   all_analyses: Dict) -> bool:
        """Üst timeframe onayını kontrol et"""
        tf_config = self.TIMEFRAME_HIERARCHY.get(timeframe, {})
        parent_tf = tf_config.get('parent')
        
        if not parent_tf or parent_tf not in all_analyses:
            return True  # Parent yoksa onaylı say
        
        parent_analysis = all_analyses[parent_tf]
        parent_signal = parent_analysis.get('signal', 'HOLD')
        parent_trend = parent_analysis.get('gram_analysis', {}).get('trend', 'NEUTRAL')
        
        # Sinyal uyumu
        if signal == parent_signal:
            return True
        
        # Trend uyumu (HOLD durumunda)
        if parent_signal == 'HOLD':
            if signal == 'BUY' and parent_trend in ['BULLISH', 'NEUTRAL']:
                return True
            elif signal == 'SELL' and parent_trend in ['BEARISH', 'NEUTRAL']:
                return True
        
        # Çelişki durumu
        if (signal == 'BUY' and parent_signal == 'SELL') or \
           (signal == 'SELL' and parent_signal == 'BUY'):
            logger.warning(f"Parent timeframe conflict: {timeframe}={signal}, {parent_tf}={parent_signal}")
            return False
        
        return False  # Diğer durumlar için onaysız
    
    def _calculate_confluence_score(self, current_tf: str, current_signal: str,
                                   all_analyses: Dict) -> float:
        """
        Confluence skoru hesapla (0-100)
        """
        if not all_analyses:
            return 0
        
        total_score = 0
        total_weight = 0
        
        for tf, analysis in all_analyses.items():
            tf_weight = self.TIMEFRAME_HIERARCHY.get(tf, {}).get('weight', 0.25)
            tf_signal = analysis.get('signal', 'HOLD')
            tf_confidence = analysis.get('confidence', 0.5)
            tf_trend = analysis.get('gram_analysis', {}).get('trend', 'NEUTRAL')
            
            # Sinyal uyumu skoru
            signal_score = 0
            if tf_signal == current_signal:
                signal_score = 1.0
            elif tf_signal == 'HOLD':
                # HOLD durumunda trend uyumuna bak
                if (current_signal == 'BUY' and tf_trend == 'BULLISH') or \
                   (current_signal == 'SELL' and tf_trend == 'BEARISH'):
                    signal_score = 0.7
                else:
                    signal_score = 0.3
            else:
                # Çelişki durumu
                signal_score = 0
            
            # Güven ile ağırlıklandır
            weighted_score = signal_score * tf_confidence * tf_weight
            total_score += weighted_score
            total_weight += tf_weight
        
        # Normalize et (0-100)
        if total_weight > 0:
            confluence_score = (total_score / total_weight) * 100
        else:
            confluence_score = 0
        
        # Bonus: Tüm timeframe'ler aynı yönde ise
        all_signals = [a.get('signal', 'HOLD') for a in all_analyses.values()]
        if all(s == current_signal for s in all_signals if s != 'HOLD'):
            confluence_score = min(100, confluence_score * 1.2)
        
        return round(confluence_score, 1)
    
    def _find_conflicts_and_supports(self, current_signal: str, 
                                     all_analyses: Dict) -> Tuple[List[str], List[str]]:
        """Çelişen ve destekleyen timeframe'leri bul"""
        conflicts = []
        supports = []
        
        for tf, analysis in all_analyses.items():
            tf_signal = analysis.get('signal', 'HOLD')
            
            if tf_signal == current_signal:
                supports.append(tf)
            elif tf_signal != 'HOLD' and tf_signal != current_signal:
                conflicts.append(tf)
            # HOLD durumunda trend'e bak
            elif tf_signal == 'HOLD':
                tf_trend = analysis.get('gram_analysis', {}).get('trend', 'NEUTRAL')
                if (current_signal == 'BUY' and tf_trend == 'BULLISH') or \
                   (current_signal == 'SELL' and tf_trend == 'BEARISH'):
                    supports.append(f"{tf}(trend)")
        
        return conflicts, supports
    
    def _collect_major_levels(self, all_analyses: Dict) -> Dict[str, List[float]]:
        """Büyük timeframe'lerden önemli seviyeleri topla"""
        major_levels = {
            'support': [],
            'resistance': []
        }
        
        # Sadece 4h ve 1d timeframe'lerden seviyeler al
        major_timeframes = ['4h', '1d']
        
        for tf in major_timeframes:
            if tf not in all_analyses:
                continue
            
            analysis = all_analyses[tf]
            gram_analysis = analysis.get('gram_analysis', {})
            
            # Destek seviyeleri
            supports = gram_analysis.get('support_levels', [])
            for sup in supports[:2]:  # En güçlü 2 destek
                if hasattr(sup, 'level'):
                    major_levels['support'].append({
                        'level': float(sup.level),
                        'timeframe': tf,
                        'strength': sup.strength
                    })
            
            # Direnç seviyeleri
            resistances = gram_analysis.get('resistance_levels', [])
            for res in resistances[:2]:  # En güçlü 2 direnç
                if hasattr(res, 'level'):
                    major_levels['resistance'].append({
                        'level': float(res.level),
                        'timeframe': tf,
                        'strength': res.strength
                    })
        
        # Sırala ve unique yap
        major_levels['support'].sort(key=lambda x: x['level'], reverse=True)
        major_levels['resistance'].sort(key=lambda x: x['level'])
        
        return major_levels
    
    def _generate_recommendation(self, timeframe: str, signal: str, 
                               confluence_score: float, parent_confirmation: bool,
                               conflict_count: int) -> str:
        """Confluence analizine göre öneri oluştur"""
        
        # Güçlü confluence (80+)
        if confluence_score >= 80 and parent_confirmation:
            return f"GÜÇLÜ {signal} - Tüm timeframe'ler uyumlu, yüksek güvenle işlem yapılabilir"
        
        # Orta confluence (60-80)
        elif confluence_score >= 60 and parent_confirmation:
            return f"ORTA {signal} - Çoğu timeframe uyumlu, dikkatli pozisyon alınabilir"
        
        # Zayıf confluence (40-60)
        elif confluence_score >= 40:
            if not parent_confirmation:
                return f"ZAYIF {signal} - Üst timeframe onayı yok, beklenmesi önerilir"
            else:
                return f"ZAYIF {signal} - Timeframe uyumu düşük, küçük pozisyon düşünülebilir"
        
        # Çok zayıf confluence (<40)
        else:
            if conflict_count > 0:
                return "İŞLEM YAPMA - Timeframe'ler arasında ciddi çelişki var"
            else:
                return "BEKLE - Yeterli timeframe uyumu yok"
    
    def _get_confluence_breakdown(self, all_analyses: Dict) -> Dict:
        """Confluence detaylı dökümü"""
        breakdown = {}
        
        for tf, analysis in all_analyses.items():
            breakdown[tf] = {
                'signal': analysis.get('signal', 'HOLD'),
                'confidence': analysis.get('confidence', 0),
                'trend': analysis.get('gram_analysis', {}).get('trend', 'NEUTRAL'),
                'price': analysis.get('gram_price', 0),
                'timestamp': analysis.get('timestamp')
            }
        
        return breakdown
    
    def get_unified_signal(self, all_analyses: Dict) -> Dict[str, Any]:
        """
        Tüm timeframe'leri birleştirerek tek bir sinyal üret
        ⚠️ IMPORTANT: Bu metod sadece özel durumlar için kullanılmalı
        """
        # Ağırlıklı oylama sistemi
        signal_votes = defaultdict(float)
        total_weight = 0
        
        for tf, analysis in all_analyses.items():
            tf_weight = self.TIMEFRAME_HIERARCHY.get(tf, {}).get('weight', 0.25)
            tf_signal = analysis.get('signal', 'HOLD')
            tf_confidence = analysis.get('confidence', 0.5)
            
            signal_votes[tf_signal] += tf_weight * tf_confidence
            total_weight += tf_weight
        
        # En yüksek oyu alan sinyal
        if signal_votes:
            unified_signal = max(signal_votes.items(), key=lambda x: x[1])[0]
            unified_confidence = signal_votes[unified_signal] / total_weight
        else:
            unified_signal = 'HOLD'
            unified_confidence = 0
        
        return {
            'signal': unified_signal,
            'confidence': unified_confidence,
            'vote_distribution': dict(signal_votes)
        }
```

### 2.2 hybrid_strategy.py'ye Entegrasyon

```python
# hybrid_strategy.py içine eklenecek

from analyzers.timeframe_confluence import TimeframeConfluenceAnalyzer

class HybridStrategy:
    def __init__(self):
        # Mevcut init kodları...
        self.confluence_analyzer = TimeframeConfluenceAnalyzer(storage)  # storage inject edilmeli
    
    def analyze(self, gram_candles: List[GramAltinCandle], 
                market_data: List[MarketData], timeframe: str = "15m") -> Dict[str, Any]:
        # Mevcut analiz kodları...
        
        # Confluence analizi (sinyal üretiminden sonra)
        if combined_signal["signal"] != "HOLD":
            confluence_result = self.confluence_analyzer.analyze_confluence(
                timeframe, 
                combined_signal["signal"],
                {
                    'signal': combined_signal["signal"],
                    'confidence': combined_signal["confidence"],
                    'gram_analysis': gram_analysis,
                    'timestamp': timezone.now()
                }
            )
            
            # Confluence skoru düşükse sinyali HOLD'a çevir
            if confluence_result['confluence_score'] < 40:
                logger.info(f"Low confluence score ({confluence_result['confluence_score']}), converting to HOLD")
                combined_signal["signal"] = "HOLD"
                combined_signal["confidence"] *= 0.5
            
            # Parent onayı yoksa güveni düşür
            elif not confluence_result['parent_confirmation']:
                combined_signal["confidence"] *= 0.7
                logger.info(f"No parent confirmation, reducing confidence to {combined_signal['confidence']:.2f}")
            
            # Sonuca confluence bilgilerini ekle
            result['confluence'] = confluence_result
```

## 📦 3. Market Structure Break Implementation

### 3.1 Yeni Dosya: `analyzers/market_structure.py`

```python
"""
Market Structure Analyzer
HH/HL/LL/LH pattern tespiti ve structure break analizi
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import logging
from utils import timezone

logger = logging.getLogger(__name__)

class MarketStructureAnalyzer:
    """Piyasa yapısı ve trend değişim analizi"""
    
    def __init__(self, swing_lookback: int = 10, break_threshold: float = 0.001):
        """
        Args:
            swing_lookback: Swing noktaları için geriye bakma
            break_threshold: Structure break için minimum kırılım (%0.1)
        """
        self.swing_lookback = swing_lookback
        self.break_threshold = break_threshold
    
    def analyze_structure(self, candles: List) -> Dict[str, Any]:
        """
        Market structure analizi
        
        Returns:
            {
                'current_structure': str (UPTREND/DOWNTREND/RANGING),
                'structure_points': List[Dict],
                'structure_break': bool,
                'break_type': str (BULLISH_BREAK/BEARISH_BREAK),
                'pullback_zone': Dict,
                'key_levels': Dict,
                'structure_strength': float (0-1)
            }
        """
        if len(candles) < self.swing_lookback * 2:
            return self._empty_structure_result()
        
        # Swing noktalarını tespit et
        swings = self._identify_swings(candles)
        
        # Market structure belirle
        structure = self._determine_structure(swings)
        
        # Structure break kontrolü
        break_analysis = self._check_structure_break(swings, structure)
        
        # Pullback bölgesi hesapla
        pullback_zone = self._calculate_pullback_zone(swings, break_analysis)
        
        # Key level'ları belirle
        key_levels = self._identify_key_levels(swings, candles)
        
        return {
            'current_structure': structure['type'],
            'structure_points': structure['points'],
            'structure_break': break_analysis['break_detected'],
            'break_type': break_analysis['break_type'],
            'pullback_zone': pullback_zone,
            'key_levels': key_levels,
            'structure_strength': structure['strength'],
            'last_swing': swings['all'][-1] if swings['all'] else None
        }
    
    def _identify_swings(self, candles: List) -> Dict[str, List]:
        """Swing high ve low noktalarını tespit et"""
        highs = []
        lows = []
        all_swings = []
        
        for i in range(self.swing_lookback, len(candles) - self.swing_lookback):
            candle = candles[i]
            
            # Swing High kontrolü
            is_swing_high = True
            for j in range(1, self.swing_lookback + 1):
                if candles[i].high <= candles[i-j].high or candles[i].high <= candles[i+j].high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing = {
                    'type': 'HIGH',
                    'index': i,
                    'price': float(candle.high),
                    'time': candle.timestamp,
                    'candle': candle
                }
                highs.append(swing)
                all_swings.append(swing)
            
            # Swing Low kontrolü
            is_swing_low = True
            for j in range(1, self.swing_lookback + 1):
                if candles[i].low >= candles[i-j].low or candles[i].low >= candles[i+j].low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing = {
                    'type': 'LOW',
                    'index': i,
                    'price': float(candle.low),
                    'time': candle.timestamp,
                    'candle': candle
                }
                lows.append(swing)
                all_swings.append(swing)
        
        # Zamana göre sırala
        all_swings.sort(key=lambda x: x['index'])
        
        return {
            'highs': highs,
            'lows': lows,
            'all': all_swings
        }
    
    def _determine_structure(self, swings: Dict) -> Dict[str, Any]:
        """
        Market structure belirle
        UPTREND: HH + HL
        DOWNTREND: LL + LH
        RANGING: Belirsiz
        """
        if len(swings['all']) < 4:
            return {'type': 'RANGING', 'points': [], 'strength': 0}
        
        # Son 4 swing noktasını al
        recent_swings = swings['all'][-4:]
        
        # Pattern analizi
        patterns = []
        for i in range(1, len(recent_swings)):
            curr = recent_swings[i]
            prev = recent_swings[i-1]
            
            # Aynı tipte iki swing'i karşılaştır
            if i >= 2:
                if curr['type'] == recent_swings[i-2]['type']:
                    prev_same_type = recent_swings[i-2]
                    
                    if curr['type'] == 'HIGH':
                        if curr['price'] > prev_same_type['price']:
                            patterns.append('HH')  # Higher High
                        else:
                            patterns.append('LH')  # Lower High
                    else:  # LOW
                        if curr['price'] < prev_same_type['price']:
                            patterns.append('LL')  # Lower Low
                        else:
                            patterns.append('HL')  # Higher Low
        
        # Structure belirleme
        structure_type = 'RANGING'
        strength = 0.5
        
        # UPTREND kontrolü (HH + HL)
        if 'HH' in patterns and 'HL' in patterns:
            structure_type = 'UPTREND'
            hh_count = patterns.count('HH')
            hl_count = patterns.count('HL')
            strength = min(1.0, (hh_count + hl_count) / 4)
        
        # DOWNTREND kontrolü (LL + LH)
        elif 'LL' in patterns and 'LH' in patterns:
            structure_type = 'DOWNTREND'
            ll_count = patterns.count('LL')
            lh_count = patterns.count('LH')
            strength = min(1.0, (ll_count + lh_count) / 4)
        
        return {
            'type': structure_type,
            'points': recent_swings,
            'patterns': patterns,
            'strength': strength
        }
    
    def _check_structure_break(self, swings: Dict, structure: Dict) -> Dict[str, Any]:
        """Structure break kontrolü"""
        if structure['type'] == 'RANGING' or len(swings['all']) < 2:
            return {'break_detected': False, 'break_type': None}
        
        last_swing = swings['all'][-1]
        
        # UPTREND'de structure break
        if structure['type'] == 'UPTREND':
            # Son swing LOW ise ve önceki LOW'dan düşükse
            if last_swing['type'] == 'LOW':
                prev_lows = [s for s in swings['lows'] if s['index'] < last_swing['index']]
                if prev_lows and last_swing['price'] < prev_lows[-1]['price']:
                    # Break confirmed
                    return {
                        'break_detected': True,
                        'break_type': 'BEARISH_BREAK',
                        'break_level': prev_lows[-1]['price'],
                        'break_swing': last_swing
                    }
        
        # DOWNTREND'de structure break
        elif structure['type'] == 'DOWNTREND':
            # Son swing HIGH ise ve önceki HIGH'dan yüksekse
            if last_swing['type'] == 'HIGH':
                prev_highs = [s for s in swings['highs'] if s['index'] < last_swing['index']]
                if prev_highs and last_swing['price'] > prev_highs[-1]['price']:
                    # Break confirmed
                    return {
                        'break_detected': True,
                        'break_type': 'BULLISH_BREAK',
                        'break_level': prev_highs[-1]['price'],
                        'break_swing': last_swing
                    }
        
        return {'break_detected': False, 'break_type': None}
    
    def _calculate_pullback_zone(self, swings: Dict, break_analysis: Dict) -> Optional[Dict]:
        """
        Structure break sonrası pullback bölgesi hesapla
        ⚠️ IMPORTANT: Pullback beklemeden giriş yapılmamalı
        """
        if not break_analysis['break_detected']:
            return None
        
        break_level = break_analysis['break_level']
        break_type = break_analysis['break_type']
        
        if break_type == 'BULLISH_BREAK':
            # Bullish break sonrası pullback = eski direnç yeni destek
            return {
                'type': 'BULLISH_PULLBACK',
                'entry_zone': {
                    'upper': break_level * 1.003,  # %0.3 tolerans
                    'lower': break_level * 0.997
                },
                'invalidation': break_level * 0.99,  # %1 altı = invalid
                'target': break_level * 1.02  # İlk hedef %2 yukarı
            }
        
        elif break_type == 'BEARISH_BREAK':
            # Bearish break sonrası pullback = eski destek yeni direnç
            return {
                'type': 'BEARISH_PULLBACK',
                'entry_zone': {
                    'upper': break_level * 1.003,
                    'lower': break_level * 0.997
                },
                'invalidation': break_level * 1.01,  # %1 üstü = invalid
                'target': break_level * 0.98  # İlk hedef %2 aşağı
            }
        
        return None
    
    def _identify_key_levels(self, swings: Dict, candles: List) -> Dict[str, List]:
        """Önemli seviyeleri belirle"""
        key_levels = {
            'major_resistance': [],
            'major_support': [],
            'recent_high': None,
            'recent_low': None
        }
        
        if not swings['highs'] or not swings['lows']:
            return key_levels
        
        # Recent high/low
        key_levels['recent_high'] = max(swings['highs'], key=lambda x: x['price'])['price']
        key_levels['recent_low'] = min(swings['lows'], key=lambda x: x['price'])['price']
        
        # Major levels (3+ kez test edilmiş)
        price_touches = defaultdict(int)
        
        for candle in candles:
            # Round to nearest 5 TRY for grouping
            high_rounded = round(float(candle.high) / 5) * 5
            low_rounded = round(float(candle.low) / 5) * 5
            
            price_touches[high_rounded] += 1
            price_touches[low_rounded] += 1
        
        # En çok test edilen seviyeleri bul
        sorted_levels = sorted(price_touches.items(), key=lambda x: x[1], reverse=True)
        
        current_price = float(candles[-1].close)
        
        for level, touches in sorted_levels[:10]:  # Top 10
            if touches >= 3:  # En az 3 kez test edilmiş
                if level > current_price:
                    key_levels['major_resistance'].append({
                        'level': level,
                        'touches': touches,
                        'strength': min(1.0, touches / 10)
                    })
                else:
                    key_levels['major_support'].append({
                        'level': level,
                        'touches': touches,
                        'strength': min(1.0, touches / 10)
                    })
        
        # Sırala
        key_levels['major_resistance'].sort(key=lambda x: x['level'])
        key_levels['major_support'].sort(key=lambda x: x['level'], reverse=True)
        
        # En yakın 3'ü al
        key_levels['major_resistance'] = key_levels['major_resistance'][:3]
        key_levels['major_support'] = key_levels['major_support'][:3]
        
        return key_levels
    
    def _empty_structure_result(self) -> Dict:
        """Boş structure sonucu"""
        return {
            'current_structure': 'UNKNOWN',
            'structure_points': [],
            'structure_break': False,
            'break_type': None,
            'pullback_zone': None,
            'key_levels': {
                'major_resistance': [],
                'major_support': [],
                'recent_high': None,
                'recent_low': None
            },
            'structure_strength': 0,
            'last_swing': None
        }
```

## 📦 4. Momentum Exhaustion Implementation

### 4.1 Yeni Dosya: `indicators/momentum_exhaustion.py`

```python
"""
Momentum Exhaustion Indicator
Ardışık mum analizi ve momentum tükenmesi tespiti
"""
from typing import List, Dict, Tuple, Optional
import numpy as np
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class MomentumExhaustionIndicator:
    """Momentum tükenmesi göstergesi"""
    
    def __init__(self, consecutive_threshold: int = 5, 
                 extreme_rsi: Tuple[float, float] = (30, 70),
                 volume_spike_threshold: float = 2.0):
        """
        Args:
            consecutive_threshold: Ardışık mum eşiği
            extreme_rsi: RSI ekstrem seviyeleri (low, high)
            volume_spike_threshold: Volume spike çarpanı
        """
        self.consecutive_threshold = consecutive_threshold
        self.extreme_rsi = extreme_rsi
        self.volume_spike_threshold = volume_spike_threshold
    
    def analyze_exhaustion(self, candles: List, indicators: Dict) -> Dict[str, Any]:
        """
        Momentum exhaustion analizi
        
        Args:
            candles: Mum verileri
            indicators: RSI, MACD, Stoch değerleri
            
        Returns:
            {
                'exhaustion_detected': bool,
                'exhaustion_type': str (BULLISH_EXHAUSTION/BEARISH_EXHAUSTION),
                'exhaustion_signals': List[str],
                'consecutive_candles': Dict,
                'candle_anomaly': Dict,
                'extreme_indicators': Dict,
                'exhaustion_score': float (0-1),
                'reversal_probability': float (0-1)
            }
        """
        if len(candles) < self.consecutive_threshold:
            return self._empty_exhaustion_result()
        
        # 1. Ardışık mum analizi
        consecutive = self._analyze_consecutive_candles(candles)
        
        # 2. Mum büyüklüğü anomali tespiti
        candle_anomaly = self._detect_candle_anomaly(candles)
        
        # 3. Gösterge ekstrem kontrolü
        extreme_indicators = self._check_extreme_indicators(indicators)
        
        # 4. Volume spike analizi
        volume_analysis = self._analyze_volume_spike(candles)
        
        # 5. Exhaustion skorlama
        exhaustion_score, exhaustion_type = self._calculate_exhaustion_score(
            consecutive, candle_anomaly, extreme_indicators, volume_analysis
        )
        
        # 6. Reversal olasılığı
        reversal_prob = self._calculate_reversal_probability(
            exhaustion_score, consecutive, extreme_indicators
        )
        
        # Exhaustion sinyalleri topla
        signals = self._collect_exhaustion_signals(
            consecutive, candle_anomaly, extreme_indicators, volume_analysis
        )
        
        return {
            'exhaustion_detected': exhaustion_score >= 0.6,
            'exhaustion_type': exhaustion_type,
            'exhaustion_signals': signals,
            'consecutive_candles': consecutive,
            'candle_anomaly': candle_anomaly,
            'extreme_indicators': extreme_indicators,
            'volume_analysis': volume_analysis,
            'exhaustion_score': exhaustion_score,
            'reversal_probability': reversal_prob
        }
    
    def _analyze_consecutive_candles(self, candles: List) -> Dict[str, Any]:
        """Ardışık aynı yönlü mumları say"""
        if not candles:
            return {'bullish': 0, 'bearish': 0, 'current_streak': 0}
        
        # Son mumdan geriye doğru say
        current_direction = None
        current_streak = 0
        max_bullish = 0
        max_bearish = 0
        
        for i in range(len(candles) - 1, -1, -1):
            candle = candles[i]
            is_bullish = candle.close > candle.open
            
            if current_direction is None:
                current_direction = 'bullish' if is_bullish else 'bearish'
                current_streak = 1
            elif (current_direction == 'bullish' and is_bullish) or \
                 (current_direction == 'bearish' and not is_bullish):
                current_streak += 1
            else:
                # Yön değişti, streak'i kaydet
                if current_direction == 'bullish':
                    max_bullish = max(max_bullish, current_streak)
                else:
                    max_bearish = max(max_bearish, current_streak)
                
                # Yeni streak başlat
                current_direction = 'bullish' if is_bullish else 'bearish'
                current_streak = 1
            
            # Son 20 muma bak
            if i < len(candles) - 20:
                break
        
        # Son streak'i de kaydet
        if current_direction == 'bullish':
            max_bullish = max(max_bullish, current_streak)
        else:
            max_bearish = max(max_bearish, current_streak)
        
        # Streak gücü hesapla
        streak_strength = 0
        if current_streak >= self.consecutive_threshold:
            streak_strength = min(1.0, current_streak / (self.consecutive_threshold * 2))
        
        return {
            'current_direction': current_direction,
            'current_streak': current_streak,
            'max_bullish_streak': max_bullish,
            'max_bearish_streak': max_bearish,
            'streak_strength': streak_strength,
            'exhaustion_likely': current_streak >= self.consecutive_threshold
        }
    
    def _detect_candle_anomaly(self, candles: List) -> Dict[str, Any]:
        """Dev mum veya anomali tespiti"""
        if len(candles) < 20:
            return {'anomaly_detected': False}
        
        # Son 20 mumun ortalama büyüklüğü
        candle_sizes = []
        for candle in candles[-20:]:
            size = abs(float(candle.high - candle.low))
            candle_sizes.append(size)
        
        avg_size = np.mean(candle_sizes)
        std_size = np.std(candle_sizes)
        
        # Son mumun büyüklüğü
        last_candle = candles[-1]
        last_size = abs(float(last_candle.high - last_candle.low))
        last_body = abs(float(last_candle.close - last_candle.open))
        
        # Anomali kontrolü
        is_anomaly = last_size > avg_size + (2 * std_size)  # 2 standart sapma
        is_large_body = last_body > avg_size * 0.7  # Body, ortalama mum boyutunun %70'inden büyük
        
        # Spike direction
        spike_direction = 'bullish' if last_candle.close > last_candle.open else 'bearish'
        
        # Anomali skoru
        if is_anomaly:
            anomaly_score = min(1.0, (last_size - avg_size) / avg_size)
        else:
            anomaly_score = 0
        
        return {
            'anomaly_detected': is_anomaly,
            'large_body': is_large_body,
            'spike_direction': spike_direction,
            'last_candle_size': last_size,
            'average_size': avg_size,
            'size_ratio': last_size / avg_size if avg_size > 0 else 1,
            'anomaly_score': anomaly_score
        }
    
    def _check_extreme_indicators(self, indicators: Dict) -> Dict[str, Any]:
        """RSI, MACD, Stochastic ekstrem kontrolü"""
        extreme_count = 0
        extreme_indicators = []
        
        # RSI kontrolü
        rsi = indicators.get('rsi')
        if rsi is not None:
            if rsi <= self.extreme_rsi[0]:  # Oversold
                extreme_count += 1
                extreme_indicators.append(f"RSI_OVERSOLD({rsi:.1f})")
            elif rsi >= self.extreme_rsi[1]:  # Overbought
                extreme_count += 1
                extreme_indicators.append(f"RSI_OVERBOUGHT({rsi:.1f})")
        
        # Stochastic kontrolü
        stoch = indicators.get('stochastic', {})
        stoch_k = stoch.get('k')
        if stoch_k is not None:
            if stoch_k <= 20:
                extreme_count += 1
                extreme_indicators.append(f"STOCH_OVERSOLD({stoch_k:.1f})")
            elif stoch_k >= 80:
                extreme_count += 1
                extreme_indicators.append(f"STOCH_OVERBOUGHT({stoch_k:.1f})")
        
        # MACD divergence from signal
        macd_data = indicators.get('macd', {})
        macd = macd_data.get('macd')
        signal = macd_data.get('signal')
        if macd is not None and signal is not None:
            divergence = abs(macd - signal)
            avg_value = (abs(macd) + abs(signal)) / 2
            if avg_value > 0:
                divergence_ratio = divergence / avg_value
                if divergence_ratio > 0.3:  # %30'dan fazla sapma
                    extreme_count += 1
                    extreme_indicators.append(f"MACD_DIVERGENCE({divergence_ratio:.1%})")
        
        # Triple extreme kontrolü
        triple_extreme = extreme_count >= 3
        
        return {
            'extreme_count': extreme_count,
            'extreme_indicators': extreme_indicators,
            'triple_extreme': triple_extreme,
            'exhaustion_direction': self._determine_exhaustion_direction(indicators)
        }
    
    def _analyze_volume_spike(self, candles: List) -> Dict[str, Any]:
        """Volume spike analizi"""
        if len(candles) < 20:
            return {'volume_spike': False, 'spike_ratio': 1.0}
        
        # Volume verisi kontrolü
        volumes = []
        for candle in candles[-20:]:
            if hasattr(candle, 'volume') and candle.volume is not None:
                volumes.append(float(candle.volume))
        
        if not volumes or len(volumes) < 10:
            return {'volume_spike': False, 'spike_ratio': 1.0}
        
        # Ortalama volume
        avg_volume = np.mean(volumes[:-1])  # Son hariç
        last_volume = volumes[-1]
        
        # Spike kontrolü
        if avg_volume > 0:
            spike_ratio = last_volume / avg_volume
            is_spike = spike_ratio >= self.volume_spike_threshold
        else:
            spike_ratio = 1.0
            is_spike = False
        
        return {
            'volume_spike': is_spike,
            'spike_ratio': spike_ratio,
            'last_volume': last_volume,
            'average_volume': avg_volume,
            'spike_strength': min(1.0, (spike_ratio - 1) / 2) if is_spike else 0
        }
    
    def _calculate_exhaustion_score(self, consecutive: Dict, anomaly: Dict,
                                   indicators: Dict, volume: Dict) -> Tuple[float, str]:
        """Exhaustion skorunu hesapla"""
        score = 0
        weights = {
            'consecutive': 0.3,
            'anomaly': 0.2,
            'indicators': 0.3,
            'volume': 0.2
        }
        
        # 1. Ardışık mum skoru
        if consecutive['exhaustion_likely']:
            score += weights['consecutive'] * consecutive['streak_strength']
        
        # 2. Anomali skoru
        if anomaly['anomaly_detected']:
            score += weights['anomaly'] * anomaly['anomaly_score']
        
        # 3. Ekstrem gösterge skoru
        if indicators['extreme_count'] > 0:
            indicator_score = min(1.0, indicators['extreme_count'] / 3)
            score += weights['indicators'] * indicator_score
        
        # 4. Volume spike skoru
        if volume['volume_spike']:
            score += weights['volume'] * volume['spike_strength']
        
        # Exhaustion tipi belirle
        if score >= 0.5:
            direction = consecutive['current_direction']
            if direction == 'bullish' and indicators.get('exhaustion_direction') == 'overbought':
                exhaustion_type = 'BEARISH_EXHAUSTION'  # Yükseliş tükendi, düşüş bekle
            elif direction == 'bearish' and indicators.get('exhaustion_direction') == 'oversold':
                exhaustion_type = 'BULLISH_EXHAUSTION'  # Düşüş tükendi, yükseliş bekle
            else:
                exhaustion_type = 'NEUTRAL_EXHAUSTION'
        else:
            exhaustion_type = 'NO_EXHAUSTION'
        
        return score, exhaustion_type
    
    def _calculate_reversal_probability(self, exhaustion_score: float,
                                      consecutive: Dict, indicators: Dict) -> float:
        """Reversal olasılığını hesapla"""
        if exhaustion_score < 0.5:
            return 0
        
        base_prob = exhaustion_score * 0.6  # Base probability
        
        # Modifiers
        # 1. Streak uzunluğu
        if consecutive['current_streak'] >= self.consecutive_threshold + 2:
            base_prob *= 1.2
        
        # 2. Triple extreme
        if indicators['triple_extreme']:
            base_prob *= 1.3
        
        # 3. Tutarlılık kontrolü
        if consecutive['current_direction'] == 'bullish' and \
           indicators.get('exhaustion_direction') == 'overbought':
            base_prob *= 1.1
        elif consecutive['current_direction'] == 'bearish' and \
             indicators.get('exhaustion_direction') == 'oversold':
            base_prob *= 1.1
        
        return min(0.9, base_prob)  # Max %90
    
    def _determine_exhaustion_direction(self, indicators: Dict) -> str:
        """Göstergelere göre exhaustion yönü"""
        overbought_score = 0
        oversold_score = 0
        
        # RSI
        rsi = indicators.get('rsi')
        if rsi is not None:
            if rsi >= self.extreme_rsi[1]:
                overbought_score += 1
            elif rsi <= self.extreme_rsi[0]:
                oversold_score += 1
        
        # Stochastic
        stoch_k = indicators.get('stochastic', {}).get('k')
        if stoch_k is not None:
            if stoch_k >= 80:
                overbought_score += 1
            elif stoch_k <= 20:
                oversold_score += 1
        
        if overbought_score > oversold_score:
            return 'overbought'
        elif oversold_score > overbought_score:
            return 'oversold'
        else:
            return 'neutral'
    
    def _collect_exhaustion_signals(self, consecutive: Dict, anomaly: Dict,
                                   indicators: Dict, volume: Dict) -> List[str]:
        """Exhaustion sinyallerini topla"""
        signals = []
        
        if consecutive['exhaustion_likely']:
            signals.append(f"{consecutive['current_streak']} ardışık {consecutive['current_direction']} mum")
        
        if anomaly['anomaly_detected']:
            signals.append(f"Dev mum tespiti (x{anomaly['size_ratio']:.1f} normal boyut)")
        
        if indicators['extreme_indicators']:
            signals.extend(indicators['extreme_indicators'])
        
        if volume['volume_spike']:
            signals.append(f"Volume spike (x{volume['spike_ratio']:.1f})")
        
        return signals
    
    def _empty_exhaustion_result(self) -> Dict:
        """Boş exhaustion sonucu"""
        return {
            'exhaustion_detected': False,
            'exhaustion_type': 'NO_EXHAUSTION',
            'exhaustion_signals': [],
            'consecutive_candles': {'bullish': 0, 'bearish': 0, 'current_streak': 0},
            'candle_anomaly': {'anomaly_detected': False},
            'extreme_indicators': {'extreme_count': 0, 'extreme_indicators': []},
            'volume_analysis': {'volume_spike': False, 'spike_ratio': 1.0},
            'exhaustion_score': 0,
            'reversal_probability': 0
        }
```

## 📦 5. Smart Money Concepts Implementation

### 5.1 Yeni Dosya: `analyzers/smart_money_analyzer.py`

```python
"""
Smart Money Concepts Analyzer
Likidite havuzları, stop hunt, order block ve FVG analizi
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import numpy as np
import logging
from collections import defaultdict
from utils import timezone

logger = logging.getLogger(__name__)

class SmartMoneyAnalyzer:
    """Akıllı para konseptleri analizi"""
    
    def __init__(self, lookback_period: int = 50,
                 liquidity_threshold: float = 0.002,
                 stop_hunt_threshold: float = 0.003):
        """
        Args:
            lookback_period: Analiz için geriye bakma periyodu
            liquidity_threshold: Likidite seviyesi eşiği (%0.2)
            stop_hunt_threshold: Stop hunt için spike eşiği (%0.3)
        """
        self.lookback_period = lookback_period
        self.liquidity_threshold = liquidity_threshold
        self.stop_hunt_threshold = stop_hunt_threshold
    
    def analyze_smart_money(self, candles: List) -> Dict[str, Any]:
        """
        Smart money konseptleri analizi
        
        Returns:
            {
                'liquidity_pools': List[Dict],
                'stop_hunt_detected': bool,
                'stop_hunt_pattern': Dict,
                'order_blocks': List[Dict],
                'fair_value_gaps': List[Dict],
                'smart_money_signal': str,
                'entry_zones': List[Dict],
                'confidence': float
            }
        """
        if len(candles) < self.lookback_period:
            return self._empty_smart_money_result()
        
        # 1. Likidite havuzlarını tespit et
        liquidity_pools = self._identify_liquidity_pools(candles)
        
        # 2. Stop hunt pattern kontrolü
        stop_hunt = self._detect_stop_hunt(candles, liquidity_pools)
        
        # 3. Order block tespiti
        order_blocks = self._identify_order_blocks(candles)
        
        # 4. Fair Value Gap analizi
        fvgs = self._find_fair_value_gaps(candles)
        
        # 5. Smart money sinyali üret
        signal, entry_zones = self._generate_smart_money_signal(
            liquidity_pools, stop_hunt, order_blocks, fvgs, candles
        )
        
        # 6. Güven skoru
        confidence = self._calculate_confidence(
            liquidity_pools, stop_hunt, order_blocks, fvgs
        )
        
        return {
            'liquidity_pools': liquidity_pools,
            'stop_hunt_detected': stop_hunt['detected'],
            'stop_hunt_pattern': stop_hunt,
            'order_blocks': order_blocks,
            'fair_value_gaps': fvgs,
            'smart_money_signal': signal,
            'entry_zones': entry_zones,
            'confidence': confidence
        }
    
    def _identify_liquidity_pools(self, candles: List) -> List[Dict]:
        """
        Likidite havuzlarını tespit et
        Stop loss'ların toplandığı yerler
        """
        liquidity_pools = []
        
        # Son N mumun high/low'larını topla
        price_levels = defaultdict(int)
        
        for i, candle in enumerate(candles[-self.lookback_period:]):
            # High ve low'ları yuvarla (5 TRY'lik gruplar)
            high_rounded = round(float(candle.high) / 5) * 5
            low_rounded = round(float(candle.low) / 5) * 5
            
            price_levels[high_rounded] += 1
            price_levels[low_rounded] += 1
        
        # En çok test edilen seviyeleri bul
        current_price = float(candles[-1].close)
        
        for level, touches in price_levels.items():
            if touches >= 3:  # En az 3 kez test edilmiş
                distance_ratio = abs(level - current_price) / current_price
                
                # Yakın seviyeleri likidite havuzu olarak işaretle
                if distance_ratio <= 0.02:  # %2 içinde
                    pool_type = 'buy_stops' if level > current_price else 'sell_stops'
                    
                    liquidity_pools.append({
                        'level': level,
                        'type': pool_type,
                        'touches': touches,
                        'distance_ratio': distance_ratio,
                        'strength': min(1.0, touches / 5),
                        'likely_stops': self._estimate_stop_count(level, candles)
                    })
        
        # Güce göre sırala
        liquidity_pools.sort(key=lambda x: x['strength'], reverse=True)
        
        return liquidity_pools[:5]  # En güçlü 5 havuz
    
    def _detect_stop_hunt(self, candles: List, liquidity_pools: List) -> Dict[str, Any]:
        """
        Stop hunt pattern tespiti
        Pattern: Spike → Quick reversal → Strong move
        """
        if len(candles) < 10 or not liquidity_pools:
            return {'detected': False}
        
        # Son 10 mumu kontrol et
        recent_candles = candles[-10:]
        
        for i in range(2, len(recent_candles) - 2):
            candle = recent_candles[i]
            prev_candle = recent_candles[i-1]
            next_candle = recent_candles[i+1]
            
            # Spike tespiti (wick'li mum)
            upper_wick = float(candle.high - max(candle.open, candle.close))
            lower_wick = float(min(candle.open, candle.close) - candle.low)
            body_size = abs(float(candle.close - candle.open))
            total_size = float(candle.high - candle.low)
            
            if total_size == 0:
                continue
            
            # Üst stop hunt kontrolü
            if upper_wick > body_size * 2:  # Wick, body'den 2 kat büyük
                # Likidite havuzu kontrolü
                for pool in liquidity_pools:
                    if pool['type'] == 'buy_stops' and \
                       abs(float(candle.high) - pool['level']) / pool['level'] < self.stop_hunt_threshold:
                        
                        # Reversal kontrolü
                        if next_candle.close < candle.close and \
                           recent_candles[i+2].close < next_candle.close:
                            
                            return {
                                'detected': True,
                                'type': 'BEARISH_STOP_HUNT',
                                'hunt_candle': candle,
                                'hunt_level': pool['level'],
                                'entry_zone': {
                                    'upper': float(candle.close),
                                    'lower': float(candle.close) * 0.998
                                },
                                'timestamp': candle.timestamp
                            }
            
            # Alt stop hunt kontrolü
            elif lower_wick > body_size * 2:
                for pool in liquidity_pools:
                    if pool['type'] == 'sell_stops' and \
                       abs(pool['level'] - float(candle.low)) / pool['level'] < self.stop_hunt_threshold:
                        
                        # Reversal kontrolü
                        if next_candle.close > candle.close and \
                           recent_candles[i+2].close > next_candle.close:
                            
                            return {
                                'detected': True,
                                'type': 'BULLISH_STOP_HUNT',
                                'hunt_candle': candle,
                                'hunt_level': pool['level'],
                                'entry_zone': {
                                    'upper': float(candle.close) * 1.002,
                                    'lower': float(candle.close)
                                },
                                'timestamp': candle.timestamp
                            }
        
        return {'detected': False}
    
    def _identify_order_blocks(self, candles: List) -> List[Dict]:
        """
        Order block tespiti
        Güçlü hareket öncesi konsolidasyon bölgeleri
        """
        order_blocks = []
        
        if len(candles) < 20:
            return order_blocks
        
        for i in range(10, len(candles) - 5):
            # Konsolidasyon kontrolü (3-5 mum)
            consolidation_candles = candles[i-3:i+1]
            
            # Range hesapla
            high_range = max(float(c.high) for c in consolidation_candles)
            low_range = min(float(c.low) for c in consolidation_candles)
            range_size = (high_range - low_range) / low_range
            
            # Dar range kontrolü
            if range_size < 0.005:  # %0.5'ten küçük range
                # Sonraki hareketi kontrol et
                next_candles = candles[i+1:i+4]
                
                # Bullish order block
                if all(c.close > c.open for c in next_candles) and \
                   next_candles[-1].close > high_range * 1.002:
                    
                    order_blocks.append({
                        'type': 'BULLISH_OB',
                        'zone': {
                            'upper': high_range,
                            'lower': low_range
                        },
                        'strength': self._calculate_ob_strength(consolidation_candles, next_candles),
                        'timestamp': consolidation_candles[-1].timestamp,
                        'tested': self._check_ob_tested(i, candles, low_range, high_range)
                    })
                
                # Bearish order block
                elif all(c.close < c.open for c in next_candles) and \
                     next_candles[-1].close < low_range * 0.998:
                    
                    order_blocks.append({
                        'type': 'BEARISH_OB',
                        'zone': {
                            'upper': high_range,
                            'lower': low_range
                        },
                        'strength': self._calculate_ob_strength(consolidation_candles, next_candles),
                        'timestamp': consolidation_candles[-1].timestamp,
                        'tested': self._check_ob_tested(i, candles, low_range, high_range)
                    })
        
        # Son 10 tane ve test edilmemiş olanları önceliklendir
        order_blocks.sort(key=lambda x: (not x['tested'], x['strength']), reverse=True)
        
        return order_blocks[:5]
    
    def _find_fair_value_gaps(self, candles: List) -> List[Dict]:
        """
        Fair Value Gap (FVG) tespiti
        3 mum pattern'i - ortadaki mumun gap'i
        """
        fvgs = []
        
        if len(candles) < 3:
            return fvgs
        
        for i in range(1, len(candles) - 1):
            prev_candle = candles[i-1]
            curr_candle = candles[i]
            next_candle = candles[i+1]
            
            # Bullish FVG: curr_candle.low > prev_candle.high
            if float(curr_candle.low) > float(prev_candle.high):
                gap_size = float(curr_candle.low - prev_candle.high)
                
                fvgs.append({
                    'type': 'BULLISH_FVG',
                    'gap_zone': {
                        'upper': float(curr_candle.low),
                        'lower': float(prev_candle.high)
                    },
                    'gap_size': gap_size,
                    'timestamp': curr_candle.timestamp,
                    'filled': self._check_fvg_filled(i, candles, 
                                                    float(prev_candle.high), 
                                                    float(curr_candle.low))
                })
            
            # Bearish FVG: curr_candle.high < prev_candle.low
            elif float(curr_candle.high) < float(prev_candle.low):
                gap_size = float(prev_candle.low - curr_candle.high)
                
                fvgs.append({
                    'type': 'BEARISH_FVG',
                    'gap_zone': {
                        'upper': float(prev_candle.low),
                        'lower': float(curr_candle.high)
                    },
                    'gap_size': gap_size,
                    'timestamp': curr_candle.timestamp,
                    'filled': self._check_fvg_filled(i, candles,
                                                    float(curr_candle.high),
                                                    float(prev_candle.low))
                })
        
        # Doldurulmamış ve büyük gap'leri önceliklendir
        fvgs.sort(key=lambda x: (not x['filled'], x['gap_size']), reverse=True)
        
        return fvgs[:3]
    
    def _generate_smart_money_signal(self, liquidity_pools: List[Dict],
                                    stop_hunt: Dict, order_blocks: List[Dict],
                                    fvgs: List[Dict], candles: List) -> Tuple[str, List[Dict]]:
        """Smart money konseptlerine göre sinyal üret"""
        signal = "HOLD"
        entry_zones = []
        current_price = float(candles[-1].close)
        
        # 1. Stop hunt sonrası giriş (en güçlü sinyal)
        if stop_hunt['detected']:
            if stop_hunt['type'] == 'BULLISH_STOP_HUNT':
                signal = "BUY"
                entry_zones.append({
                    'type': 'stop_hunt_entry',
                    'zone': stop_hunt['entry_zone'],
                    'strength': 0.9
                })
            elif stop_hunt['type'] == 'BEARISH_STOP_HUNT':
                signal = "SELL"
                entry_zones.append({
                    'type': 'stop_hunt_entry',
                    'zone': stop_hunt['entry_zone'],
                    'strength': 0.9
                })
        
        # 2. Order block'tan dönüş
        for ob in order_blocks[:2]:  # En güçlü 2 OB
            if not ob['tested'] and ob['strength'] > 0.7:
                ob_mid = (ob['zone']['upper'] + ob['zone']['lower']) / 2
                price_to_ob = abs(current_price - ob_mid) / current_price
                
                if price_to_ob < 0.005:  # %0.5 içinde
                    if ob['type'] == 'BULLISH_OB' and current_price <= ob['zone']['upper']:
                        if signal == "HOLD":
                            signal = "BUY"
                        entry_zones.append({
                            'type': 'order_block_entry',
                            'zone': ob['zone'],
                            'strength': ob['strength']
                        })
                    elif ob['type'] == 'BEARISH_OB' and current_price >= ob['zone']['lower']:
                        if signal == "HOLD":
                            signal = "SELL"
                        entry_zones.append({
                            'type': 'order_block_entry',
                            'zone': ob['zone'],
                            'strength': ob['strength']
                        })
        
        # 3. FVG doldurma
        for fvg in fvgs[:1]:  # En büyük FVG
            if not fvg['filled']:
                fvg_mid = (fvg['gap_zone']['upper'] + fvg['gap_zone']['lower']) / 2
                
                if fvg['type'] == 'BULLISH_FVG' and \
                   current_price >= fvg['gap_zone']['lower'] and \
                   current_price <= fvg['gap_zone']['upper']:
                    if signal == "HOLD":
                        signal = "BUY"
                    entry_zones.append({
                        'type': 'fvg_fill_entry',
                        'zone': fvg['gap_zone'],
                        'strength': 0.7
                    })
                elif fvg['type'] == 'BEARISH_FVG' and \
                     current_price >= fvg['gap_zone']['lower'] and \
                     current_price <= fvg['gap_zone']['upper']:
                    if signal == "HOLD":
                        signal = "SELL"
                    entry_zones.append({
                        'type': 'fvg_fill_entry',
                        'zone': fvg['gap_zone'],
                        'strength': 0.7
                    })
        
        return signal, entry_zones
    
    def _calculate_confidence(self, liquidity_pools: List[Dict],
                            stop_hunt: Dict, order_blocks: List[Dict],
                            fvgs: List[Dict]) -> float:
        """Smart money güven skoru"""
        confidence = 0.5  # Base confidence
        
        # Stop hunt detected = yüksek güven
        if stop_hunt['detected']:
            confidence += 0.3
        
        # Güçlü likidite havuzları
        if liquidity_pools and liquidity_pools[0]['strength'] > 0.7:
            confidence += 0.1
        
        # Test edilmemiş order block
        untested_obs = [ob for ob in order_blocks if not ob['tested']]
        if untested_obs:
            confidence += 0.1
        
        # Büyük FVG
        if fvgs and fvgs[0]['gap_size'] > 10:  # 10 TRY'den büyük gap
            confidence += 0.05
        
        return min(0.95, confidence)
    
    def _estimate_stop_count(self, level: float, candles: List) -> int:
        """Bir seviyedeki tahmini stop sayısı"""
        # Basit tahmin: O seviyeye kaç kez dokunulmuş
        touches = 0
        for candle in candles:
            if abs(float(candle.high) - level) < 5 or abs(float(candle.low) - level) < 5:
                touches += 1
        return touches
    
    def _calculate_ob_strength(self, consolidation: List, breakout: List) -> float:
        """Order block gücünü hesapla"""
        # Konsolidasyon sıkılığı
        cons_range = max(float(c.high) for c in consolidation) - min(float(c.low) for c in consolidation)
        cons_avg = sum(float(c.close) for c in consolidation) / len(consolidation)
        tightness = 1 - (cons_range / cons_avg)
        
        # Breakout gücü
        breakout_move = abs(float(breakout[-1].close) - float(consolidation[-1].close))
        breakout_strength = min(1.0, breakout_move / cons_avg / 0.02)  # %2 hareket = tam güç
        
        return (tightness + breakout_strength) / 2
    
    def _check_ob_tested(self, ob_index: int, candles: List, 
                        lower: float, upper: float) -> bool:
        """Order block test edilmiş mi?"""
        for i in range(ob_index + 5, len(candles)):
            if float(candles[i].low) <= upper and float(candles[i].high) >= lower:
                return True
        return False
    
    def _check_fvg_filled(self, fvg_index: int, candles: List,
                         lower: float, upper: float) -> bool:
        """FVG doldurulmuş mu?"""
        for i in range(fvg_index + 1, len(candles)):
            if float(candles[i].low) <= upper and float(candles[i].high) >= lower:
                return True
        return False
    
    def _empty_smart_money_result(self) -> Dict:
        """Boş smart money sonucu"""
        return {
            'liquidity_pools': [],
            'stop_hunt_detected': False,
            'stop_hunt_pattern': {'detected': False},
            'order_blocks': [],
            'fair_value_gaps': [],
            'smart_money_signal': 'HOLD',
            'entry_zones': [],
            'confidence': 0
        }
```

## 🔗 Entegrasyon ve Test Planı

### main.py Değişiklikleri
```python
# Yeni analizörleri import et
from analyzers.timeframe_confluence import TimeframeConfluenceAnalyzer
from analyzers.market_structure import MarketStructureAnalyzer
from analyzers.smart_money_analyzer import SmartMoneyAnalyzer

# __init__ metoduna ekle
self.confluence_analyzer = TimeframeConfluenceAnalyzer(self.storage)
self.structure_analyzer = MarketStructureAnalyzer()
self.smart_money_analyzer = SmartMoneyAnalyzer()
```

### hybrid_strategy.py Ana Entegrasyon
```python
def analyze(self, gram_candles, market_data, timeframe="15m"):
    # Mevcut analizler...
    
    # Yeni analizleri ekle
    
    # 1. Market Structure
    structure_analysis = self.structure_analyzer.analyze_structure(gram_candles)
    
    # 2. Momentum Exhaustion
    exhaustion = self.momentum_indicator.analyze_exhaustion(
        gram_candles, 
        gram_analysis['indicators']
    )
    
    # 3. Smart Money
    smart_money = self.smart_money_analyzer.analyze_smart_money(gram_candles)
    
    # 4. Confluence (en son)
    if combined_signal["signal"] != "HOLD":
        confluence = self.confluence_analyzer.analyze_confluence(
            timeframe, combined_signal["signal"], current_analysis
        )
        
        # Düşük confluence = HOLD
        if confluence['confluence_score'] < 40:
            combined_signal["signal"] = "HOLD"
    
    # Tüm konfirmasyonları say
    confirmations = 0
    if gram_analysis.get('divergence', {}).get('bullish_divergence'):
        confirmations += 1
    if structure_analysis['structure_break']:
        confirmations += 1
    if exhaustion['exhaustion_detected']:
        confirmations += 1
    if smart_money['stop_hunt_detected']:
        confirmations += 2  # Çift ağırlık
    if confluence.get('confluence_score', 0) > 70:
        confirmations += 1
    
    # GÜÇLÜ SİNYAL kontrolü
    if confirmations < 4 and combined_signal["signal"] != "HOLD":
        combined_signal["confidence"] *= 0.7
        logger.info(f"Weak confirmation ({confirmations}), reducing confidence")
```

## 📝 Test Senaryoları

1. **Divergence Testi**
   - 5+ mumda fiyat/RSI uyumsuzluğu
   - Hidden divergence kontrolü

2. **Confluence Testi**
   - Alt TF sinyali + Üst TF onayı
   - Çelişkili TF durumu

3. **Structure Break Testi**
   - HH/HL → LL dönüşümü
   - Pullback zone entry

4. **Exhaustion Testi**
   - 7+ ardışık mum + RSI > 80
   - Volume spike kontrolü

5. **Smart Money Testi**
   - Stop hunt pattern
   - Order block bounce

## ⚠️ Kritik Uyarılar

1. **ASLA tek stratejiye güvenme** - Minimum 3 konfirmasyon
2. **Timeframe uyumu şart** - Alt TF, üst TF'e ters olamaz
3. **Stop hunt'ta acele etme** - Reversal konfirmasyonu bekle
4. **Test edilmemiş order block** öncelikli
5. **Volume onayı** her zaman kontrol et

Bu implementation guide'ı takip ederek tüm stratejileri entegre edebilirsiniz. Her modül bağımsız test edilebilir ve kademeli olarak sisteme eklenebilir.