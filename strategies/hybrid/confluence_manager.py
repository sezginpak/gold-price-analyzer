"""
Confluence Manager - Timeframe uyumu ve confluence analizi
"""
from typing import Dict, List, Optional, Tuple, Any
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConfluenceManager:
    """Multiple timeframe confluence yönetimi"""
    
    # Timeframe hiyerarşisi ve ağırlıkları
    TIMEFRAME_HIERARCHY = {
        "15m": {"parent": "1h", "weight": 0.2, "required_confirmation": ["1h"]},
        "1h": {"parent": "4h", "weight": 0.3, "required_confirmation": ["4h"]},
        "4h": {"parent": "1d", "weight": 0.35, "required_confirmation": ["1d"]},
        "1d": {"parent": None, "weight": 0.15, "required_confirmation": []}
    }
    
    def __init__(self, storage=None):
        self.storage = storage
        self.confluence_cache = {}
        
    def analyze_confluence(self, 
                          current_timeframe: str,
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
        # Storage yoksa basit sonuç dön
        if not self.storage:
            return self._simple_confluence_result(current_signal)
            
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
                'all_timeframe_signals': {
                    tf: a.get('signal', 'HOLD') 
                    for tf, a in all_analyses.items()
                },
                'all_timeframe_trends': {
                    tf: a.get('gram_analysis', {}).get('trend', 'NEUTRAL') 
                    for tf, a in all_analyses.items()
                },
                'confluence_breakdown': self._get_confluence_breakdown(all_analyses)
            }
        }
    
    def _get_all_timeframe_analyses(self) -> Dict[str, Dict]:
        """Tüm timeframe'lerdeki son analizleri getir"""
        analyses = {}
        
        if not self.storage:
            return analyses
            
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
            logger.warning(f"Parent conflict: {timeframe}={signal}, {parent_tf}={parent_signal}")
            return False
        
        return False
    
    def _calculate_confluence_score(self, current_tf: str, current_signal: str,
                                   all_analyses: Dict) -> float:
        """Confluence skoru hesapla (0-100)"""
        if not all_analyses:
            return 50.0  # Varsayılan orta skor
        
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
            confluence_score = 50.0
        
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
            return f"GÜÇLÜ {signal} - Tüm timeframe'ler uyumlu"
        
        # Orta confluence (60-80)
        elif confluence_score >= 60 and parent_confirmation:
            return f"ORTA {signal} - Çoğu timeframe uyumlu"
        
        # Zayıf confluence (40-60)
        elif confluence_score >= 40:
            if not parent_confirmation:
                return f"ZAYIF {signal} - Üst timeframe onayı yok"
            else:
                return f"ZAYIF {signal} - Timeframe uyumu düşük"
        
        # Çok zayıf confluence (<40)
        else:
            if conflict_count > 0:
                return "İŞLEM YAPMA - Timeframe çelişkisi var"
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
    
    def _simple_confluence_result(self, signal: str) -> Dict:
        """Storage yoksa basit sonuç"""
        return {
            'confluence_score': 60.0,  # Orta skor
            'parent_confirmation': True,
            'conflicting_timeframes': [],
            'supporting_timeframes': [],
            'major_levels': {'support': [], 'resistance': []},
            'recommendation': f"ORTA {signal} - Confluence analizi sınırlı",
            'details': {}
        }
    
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