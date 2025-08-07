"""
Smart Money Concepts (SMC) Module
Order blocks, Fair Value Gaps, Market Structure analizi
Volume verisi olmadan çalışacak şekilde optimize edilmiş
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from utils.logger import logger


@dataclass
class OrderBlock:
    """Order Block bilgisi"""
    type: str  # "bullish" veya "bearish"
    start_idx: int
    end_idx: int
    high: float
    low: float
    mid_point: float
    strength: float  # 0-100
    touched: bool
    broken: bool


@dataclass
class FairValueGap:
    """Fair Value Gap (Imbalance) bilgisi"""
    type: str  # "bullish" veya "bearish"
    idx: int
    high: float
    low: float
    size: float
    filled: bool
    fill_percentage: float


@dataclass
class MarketStructure:
    """Market Structure bilgisi"""
    trend: str  # "bullish", "bearish", "ranging"
    last_high: float
    last_low: float
    higher_highs: int
    higher_lows: int
    lower_highs: int
    lower_lows: int
    bos_level: Optional[float]  # Break of Structure
    choch_level: Optional[float]  # Change of Character


class SmartMoneyConcepts:
    """Smart Money Concepts analizi"""
    
    def __init__(self):
        """SMC analizci başlatıcı"""
        self.order_blocks = []
        self.fair_value_gaps = []
        self.market_structure = None
        self.liquidity_zones = []
        
    def identify_order_blocks(
        self, 
        df: pd.DataFrame,
        lookback: int = 50,
        min_strength: float = 30.0
    ) -> List[OrderBlock]:
        """
        Order block'ları tespit et
        
        Args:
            df: OHLC verisi
            lookback: Geriye bakma periyodu
            min_strength: Minimum order block gücü
            
        Returns:
            Order block listesi
        """
        try:
            order_blocks = []
            
            if len(df) < lookback:
                return order_blocks
            
            for i in range(lookback, len(df) - 1):
                # Bullish Order Block: Down move sonrası güçlü up move
                if i >= 2:
                    # Son 3 mum kontrolü
                    prev_candle = df.iloc[i-1]
                    current_candle = df.iloc[i]
                    next_candle = df.iloc[i+1] if i+1 < len(df) else None
                    
                    if next_candle is not None:
                        # Bullish OB: Düşüş sonrası güçlü yükseliş
                        down_move = prev_candle['close'] < prev_candle['open']
                        strong_up = next_candle['close'] > current_candle['high']
                        
                        if down_move and strong_up:
                            # Order block gücünü hesapla
                            move_strength = abs(next_candle['close'] - current_candle['low']) / current_candle['low'] * 100
                            
                            if move_strength >= min_strength / 100:
                                ob = OrderBlock(
                                    type="bullish",
                                    start_idx=i-1,
                                    end_idx=i,
                                    high=current_candle['high'],
                                    low=current_candle['low'],
                                    mid_point=(current_candle['high'] + current_candle['low']) / 2,
                                    strength=min(move_strength * 100, 100),
                                    touched=False,
                                    broken=False
                                )
                                order_blocks.append(ob)
                        
                        # Bearish OB: Yükseliş sonrası güçlü düşüş
                        up_move = prev_candle['close'] > prev_candle['open']
                        strong_down = next_candle['close'] < current_candle['low']
                        
                        if up_move and strong_down:
                            # Order block gücünü hesapla
                            move_strength = abs(current_candle['high'] - next_candle['close']) / current_candle['high'] * 100
                            
                            if move_strength >= min_strength / 100:
                                ob = OrderBlock(
                                    type="bearish",
                                    start_idx=i-1,
                                    end_idx=i,
                                    high=current_candle['high'],
                                    low=current_candle['low'],
                                    mid_point=(current_candle['high'] + current_candle['low']) / 2,
                                    strength=min(move_strength * 100, 100),
                                    touched=False,
                                    broken=False
                                )
                                order_blocks.append(ob)
            
            # En son ve en güçlü order block'ları tut (max 5)
            order_blocks = sorted(order_blocks, key=lambda x: x.strength, reverse=True)[:5]
            
            # Order block'ların durumunu güncelle
            current_price = df['close'].iloc[-1]
            for ob in order_blocks:
                # Touched kontrolü
                if ob.type == "bullish":
                    if current_price <= ob.high and current_price >= ob.low:
                        ob.touched = True
                    elif current_price < ob.low:
                        ob.broken = True
                else:  # bearish
                    if current_price >= ob.low and current_price <= ob.high:
                        ob.touched = True
                    elif current_price > ob.high:
                        ob.broken = True
            
            return order_blocks
            
        except Exception as e:
            logger.error(f"Order block tespit hatası: {e}")
            return []
    
    def identify_fair_value_gaps(
        self, 
        df: pd.DataFrame,
        min_gap_size: float = 0.001
    ) -> List[FairValueGap]:
        """
        Fair Value Gap (FVG) tespit et
        
        Args:
            df: OHLC verisi
            min_gap_size: Minimum gap büyüklüğü (%)
            
        Returns:
            FVG listesi
        """
        try:
            gaps = []
            
            if len(df) < 3:
                return gaps
            
            for i in range(1, len(df) - 1):
                prev_candle = df.iloc[i-1]
                current_candle = df.iloc[i]
                next_candle = df.iloc[i+1]
                
                # Bullish FVG: 3. mum low > 1. mum high
                if next_candle['low'] > prev_candle['high']:
                    gap_size = (next_candle['low'] - prev_candle['high']) / prev_candle['high']
                    
                    if gap_size >= min_gap_size:
                        fvg = FairValueGap(
                            type="bullish",
                            idx=i,
                            high=next_candle['low'],
                            low=prev_candle['high'],
                            size=gap_size * 100,
                            filled=False,
                            fill_percentage=0.0
                        )
                        gaps.append(fvg)
                
                # Bearish FVG: 3. mum high < 1. mum low
                if next_candle['high'] < prev_candle['low']:
                    gap_size = (prev_candle['low'] - next_candle['high']) / next_candle['high']
                    
                    if gap_size >= min_gap_size:
                        fvg = FairValueGap(
                            type="bearish",
                            idx=i,
                            high=prev_candle['low'],
                            low=next_candle['high'],
                            size=gap_size * 100,
                            filled=False,
                            fill_percentage=0.0
                        )
                        gaps.append(fvg)
            
            # FVG'lerin dolma durumunu kontrol et
            current_price = df['close'].iloc[-1]
            for gap in gaps:
                gap_range = gap.high - gap.low
                
                if gap.type == "bullish":
                    if current_price <= gap.low:
                        gap.filled = True
                        gap.fill_percentage = 100.0
                    elif current_price < gap.high:
                        gap.fill_percentage = ((gap.high - current_price) / gap_range) * 100
                else:  # bearish
                    if current_price >= gap.high:
                        gap.filled = True
                        gap.fill_percentage = 100.0
                    elif current_price > gap.low:
                        gap.fill_percentage = ((current_price - gap.low) / gap_range) * 100
            
            # En son 10 FVG'yi tut
            return gaps[-10:] if len(gaps) > 10 else gaps
            
        except Exception as e:
            logger.error(f"FVG tespit hatası: {e}")
            return []
    
    def analyze_market_structure(
        self, 
        df: pd.DataFrame,
        swing_lookback: int = 10
    ) -> MarketStructure:
        """
        Market structure analizi (BOS/CHoCH)
        
        Args:
            df: OHLC verisi
            swing_lookback: Swing point lookback
            
        Returns:
            Market structure
        """
        try:
            if len(df) < swing_lookback * 2:
                return MarketStructure(
                    trend="ranging",
                    last_high=df['high'].max(),
                    last_low=df['low'].min(),
                    higher_highs=0,
                    higher_lows=0,
                    lower_highs=0,
                    lower_lows=0,
                    bos_level=None,
                    choch_level=None
                )
            
            # Swing high/low bul
            highs = []
            lows = []
            
            for i in range(swing_lookback, len(df) - swing_lookback):
                # Swing high
                if df['high'].iloc[i] == df['high'].iloc[i-swing_lookback:i+swing_lookback+1].max():
                    highs.append((i, df['high'].iloc[i]))
                
                # Swing low
                if df['low'].iloc[i] == df['low'].iloc[i-swing_lookback:i+swing_lookback+1].min():
                    lows.append((i, df['low'].iloc[i]))
            
            if len(highs) < 2 or len(lows) < 2:
                return MarketStructure(
                    trend="ranging",
                    last_high=df['high'].iloc[-1],
                    last_low=df['low'].iloc[-1],
                    higher_highs=0,
                    higher_lows=0,
                    lower_highs=0,
                    lower_lows=0,
                    bos_level=None,
                    choch_level=None
                )
            
            # Structure analizi
            hh_count = 0  # Higher highs
            hl_count = 0  # Higher lows
            lh_count = 0  # Lower highs
            ll_count = 0  # Lower lows
            
            # High analizi
            for i in range(1, len(highs)):
                if highs[i][1] > highs[i-1][1]:
                    hh_count += 1
                else:
                    lh_count += 1
            
            # Low analizi
            for i in range(1, len(lows)):
                if lows[i][1] > lows[i-1][1]:
                    hl_count += 1
                else:
                    ll_count += 1
            
            # Trend belirleme
            if hh_count > lh_count and hl_count > ll_count:
                trend = "bullish"
            elif lh_count > hh_count and ll_count > hl_count:
                trend = "bearish"
            else:
                trend = "ranging"
            
            # BOS (Break of Structure) seviyesi
            bos_level = None
            if trend == "bullish" and len(lows) > 0:
                bos_level = lows[-1][1]  # Son low kırılırsa BOS
            elif trend == "bearish" and len(highs) > 0:
                bos_level = highs[-1][1]  # Son high kırılırsa BOS
            
            # CHoCH (Change of Character) seviyesi
            choch_level = None
            if trend == "bullish" and len(lows) >= 2:
                choch_level = min(lows[-2][1], lows[-1][1])  # Önceki low'ların minimumu
            elif trend == "bearish" and len(highs) >= 2:
                choch_level = max(highs[-2][1], highs[-1][1])  # Önceki high'ların maksimumu
            
            return MarketStructure(
                trend=trend,
                last_high=highs[-1][1] if highs else df['high'].iloc[-1],
                last_low=lows[-1][1] if lows else df['low'].iloc[-1],
                higher_highs=hh_count,
                higher_lows=hl_count,
                lower_highs=lh_count,
                lower_lows=ll_count,
                bos_level=bos_level,
                choch_level=choch_level
            )
            
        except Exception as e:
            logger.error(f"Market structure analiz hatası: {e}")
            return MarketStructure(
                trend="ranging",
                last_high=0,
                last_low=0,
                higher_highs=0,
                higher_lows=0,
                lower_highs=0,
                lower_lows=0,
                bos_level=None,
                choch_level=None
            )
    
    def identify_liquidity_zones(
        self, 
        df: pd.DataFrame,
        lookback: int = 50
    ) -> List[Dict]:
        """
        Likidite bölgelerini tespit et (Stop hunt zones)
        
        Args:
            df: OHLC verisi
            lookback: Geriye bakma periyodu
            
        Returns:
            Likidite bölgeleri
        """
        try:
            zones = []
            
            if len(df) < lookback:
                return zones
            
            recent_df = df.tail(lookback)
            
            # Equal highs (Buy side liquidity)
            high_counts = recent_df['high'].value_counts()
            for price, count in high_counts.items():
                if count >= 2:  # En az 2 kez test edilmiş
                    zones.append({
                        'type': 'buy_side_liquidity',
                        'level': price,
                        'touches': count,
                        'strength': min(count * 20, 100),
                        'description': f"{count} kez test edilmiş direnç (stop-loss yığılması)"
                    })
            
            # Equal lows (Sell side liquidity)
            low_counts = recent_df['low'].value_counts()
            for price, count in low_counts.items():
                if count >= 2:  # En az 2 kez test edilmiş
                    zones.append({
                        'type': 'sell_side_liquidity',
                        'level': price,
                        'touches': count,
                        'strength': min(count * 20, 100),
                        'description': f"{count} kez test edilmiş destek (stop-loss yığılması)"
                    })
            
            # Relative highs/lows (Swing points)
            window = 5
            for i in range(window, len(recent_df) - window):
                # Relative high
                if recent_df['high'].iloc[i] == recent_df['high'].iloc[i-window:i+window+1].max():
                    zones.append({
                        'type': 'swing_high_liquidity',
                        'level': recent_df['high'].iloc[i],
                        'touches': 1,
                        'strength': 50,
                        'description': "Swing high (potansiyel stop-loss bölgesi)"
                    })
                
                # Relative low
                if recent_df['low'].iloc[i] == recent_df['low'].iloc[i-window:i+window+1].min():
                    zones.append({
                        'type': 'swing_low_liquidity',
                        'level': recent_df['low'].iloc[i],
                        'touches': 1,
                        'strength': 50,
                        'description': "Swing low (potansiyel stop-loss bölgesi)"
                    })
            
            # En güçlü 10 zonu döndür
            zones = sorted(zones, key=lambda x: x['strength'], reverse=True)[:10]
            
            return zones
            
        except Exception as e:
            logger.error(f"Likidite bölgesi tespit hatası: {e}")
            return []
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Komple SMC analizi
        
        Args:
            df: OHLC verisi
            
        Returns:
            SMC analiz sonuçları
        """
        try:
            if len(df) < 50:
                return {
                    'status': 'insufficient_data',
                    'message': 'SMC analizi için yetersiz veri'
                }
            
            # Tüm SMC bileşenlerini analiz et
            self.order_blocks = self.identify_order_blocks(df)
            self.fair_value_gaps = self.identify_fair_value_gaps(df)
            self.market_structure = self.analyze_market_structure(df)
            self.liquidity_zones = self.identify_liquidity_zones(df)
            
            current_price = df['close'].iloc[-1]
            
            # Trading sinyalleri üret
            signals = self._generate_smc_signals(current_price)
            
            # Sonuçları hazırla - tüm numpy değerleri Python tiplerini çevir
            result = {
                'status': 'success',
                'current_price': float(current_price),
                'market_structure': {
                    'trend': str(self.market_structure.trend),
                    'last_high': float(self.market_structure.last_high) if self.market_structure.last_high is not None else None,
                    'last_low': float(self.market_structure.last_low) if self.market_structure.last_low is not None else None,
                    'higher_highs': int(self.market_structure.higher_highs),
                    'higher_lows': int(self.market_structure.higher_lows),
                    'lower_highs': int(self.market_structure.lower_highs),
                    'lower_lows': int(self.market_structure.lower_lows),
                    'bos_level': float(self.market_structure.bos_level) if self.market_structure.bos_level is not None else None,
                    'choch_level': float(self.market_structure.choch_level) if self.market_structure.choch_level is not None else None
                },
                'order_blocks': [
                    {
                        'type': str(ob.type),
                        'high': float(ob.high),
                        'low': float(ob.low),
                        'mid_point': float(ob.mid_point),
                        'strength': float(ob.strength),
                        'touched': bool(ob.touched),
                        'broken': bool(ob.broken)
                    }
                    for ob in self.order_blocks if not ob.broken
                ],
                'fair_value_gaps': [
                    {
                        'type': str(fvg.type),
                        'high': float(fvg.high),
                        'low': float(fvg.low),
                        'size_pct': float(fvg.size),
                        'filled': bool(fvg.filled),
                        'fill_percentage': float(fvg.fill_percentage)
                    }
                    for fvg in self.fair_value_gaps if not fvg.filled
                ],
                'liquidity_zones': [
                    {k: float(v) if isinstance(v, (int, float, np.number)) and not isinstance(v, bool) 
                     else bool(v) if isinstance(v, (bool, np.bool_))
                     else str(v) for k, v in zone.items()} if isinstance(zone, dict) else zone 
                    for zone in self.liquidity_zones[:5]
                ],  # Top 5
                'signals': {
                    k: float(v) if isinstance(v, (int, float, np.number)) and not isinstance(v, bool)
                    else bool(v) if isinstance(v, (bool, np.bool_))
                    else [float(x) if isinstance(x, (int, float, np.number)) and not isinstance(x, bool) else str(x) for x in v] if isinstance(v, list)
                    else str(v) for k, v in signals.items()
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"SMC analiz hatası: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _generate_smc_signals(self, current_price: float) -> Dict:
        """
        SMC konseptlerine göre trading sinyalleri üret
        
        Returns:
            Trading sinyalleri
        """
        try:
            signals = {
                'action': 'WAIT',
                'strength': 0,
                'reasons': [],
                'target': None,
                'stop': None,
                'risk_reward': 0
            }
            
            buy_score = 0
            sell_score = 0
            reasons = []
            
            # Market structure sinyalleri
            if self.market_structure:
                if self.market_structure.trend == "bullish":
                    buy_score += 20
                    reasons.append("Bullish market structure")
                elif self.market_structure.trend == "bearish":
                    sell_score += 20
                    reasons.append("Bearish market structure")
                
                # BOS/CHoCH kontrol
                if self.market_structure.bos_level:
                    if current_price < self.market_structure.bos_level:
                        reasons.append("BOS level kırıldı - trend değişimi riski")
                        buy_score -= 10
                        sell_score += 10
                
                if self.market_structure.choch_level:
                    if self.market_structure.trend == "bullish" and current_price < self.market_structure.choch_level:
                        reasons.append("CHoCH - Karakter değişimi sinyali")
                        buy_score -= 15
                        sell_score += 15
                    elif self.market_structure.trend == "bearish" and current_price > self.market_structure.choch_level:
                        reasons.append("CHoCH - Karakter değişimi sinyali")
                        sell_score -= 15
                        buy_score += 15
            
            # Order block sinyalleri
            for ob in self.order_blocks:
                if ob.broken:
                    continue
                    
                distance_pct = abs(current_price - ob.mid_point) / current_price * 100
                
                if ob.type == "bullish" and not ob.touched:
                    if distance_pct < 0.5:  # %0.5'ten yakın
                        buy_score += ob.strength / 2
                        reasons.append(f"Bullish order block yakın (güç: {ob.strength:.0f})")
                        
                elif ob.type == "bearish" and not ob.touched:
                    if distance_pct < 0.5:  # %0.5'ten yakın
                        sell_score += ob.strength / 2
                        reasons.append(f"Bearish order block yakın (güç: {ob.strength:.0f})")
            
            # Fair Value Gap sinyalleri
            for fvg in self.fair_value_gaps:
                if fvg.filled:
                    continue
                
                if fvg.type == "bullish":
                    if current_price >= fvg.low and current_price <= fvg.high:
                        buy_score += 25
                        reasons.append(f"Bullish FVG içinde (boyut: {fvg.size:.2f}%)")
                        
                elif fvg.type == "bearish":
                    if current_price >= fvg.low and current_price <= fvg.high:
                        sell_score += 25
                        reasons.append(f"Bearish FVG içinde (boyut: {fvg.size:.2f}%)")
            
            # Liquidity zone sinyalleri
            for zone in self.liquidity_zones[:3]:  # Top 3 zone
                distance_pct = abs(current_price - zone['level']) / current_price * 100
                
                if distance_pct < 0.3:  # %0.3'ten yakın
                    if zone['type'] in ['buy_side_liquidity', 'swing_high_liquidity']:
                        reasons.append(f"Buy side liquidity yakın ({zone['touches']} dokunuş)")
                        # Liquidity sweep potansiyeli
                        if current_price > zone['level']:
                            sell_score += 15
                            reasons.append("Potansiyel liquidity sweep")
                    
                    elif zone['type'] in ['sell_side_liquidity', 'swing_low_liquidity']:
                        reasons.append(f"Sell side liquidity yakın ({zone['touches']} dokunuş)")
                        # Liquidity sweep potansiyeli
                        if current_price < zone['level']:
                            buy_score += 15
                            reasons.append("Potansiyel liquidity sweep")
            
            # Final sinyal kararı
            if buy_score >= 60:
                signals['action'] = 'BUY'
                signals['strength'] = min(buy_score, 100)
                signals['reasons'] = reasons
                
                # Target ve stop hesapla
                if self.market_structure:
                    signals['target'] = self.market_structure.last_high
                    signals['stop'] = self.market_structure.last_low
                    
                    if signals['target'] and signals['stop']:
                        risk = abs(current_price - signals['stop'])
                        reward = abs(signals['target'] - current_price)
                        signals['risk_reward'] = reward / risk if risk > 0 else 0
                        
            elif sell_score >= 60:
                signals['action'] = 'SELL'
                signals['strength'] = min(sell_score, 100)
                signals['reasons'] = reasons
                
                # Target ve stop hesapla
                if self.market_structure:
                    signals['target'] = self.market_structure.last_low
                    signals['stop'] = self.market_structure.last_high
                    
                    if signals['target'] and signals['stop']:
                        risk = abs(signals['stop'] - current_price)
                        reward = abs(current_price - signals['target'])
                        signals['risk_reward'] = reward / risk if risk > 0 else 0
                        
            elif buy_score >= 40 or sell_score >= 40:
                signals['action'] = 'WATCH'
                signals['strength'] = max(buy_score, sell_score)
                signals['reasons'] = reasons
            
            return signals
            
        except Exception as e:
            logger.error(f"SMC sinyal üretme hatası: {e}")
            return {
                'action': 'WAIT',
                'strength': 0,
                'reasons': ['Sinyal üretme hatası'],
                'target': None,
                'stop': None,
                'risk_reward': 0
            }


def calculate_smc_analysis(df: pd.DataFrame) -> Dict:
    """
    Smart Money Concepts analizi yap
    
    Args:
        df: OHLC verisi
        
    Returns:
        SMC analiz sonuçları
    """
    try:
        analyzer = SmartMoneyConcepts()
        return analyzer.analyze(df)
    except Exception as e:
        logger.error(f"SMC analiz hatası: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }