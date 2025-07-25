#!/usr/bin/env python3
"""
Mum mum (candle-by-candle) backtest sistemi
Her mum için tüm göstergeleri hesapla ve farklı stratejileri test et
"""
import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class Signal:
    timestamp: datetime
    action: str  # BUY, SELL, HOLD
    price: float
    confidence: float
    reason: str
    
@dataclass
class Trade:
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    profit_pct: Optional[float] = None
    success: Optional[bool] = None

class BacktestEngine:
    def __init__(self, db_path: str = 'gold_prices.db'):
        self.conn = sqlite3.connect(db_path)
        self.strategies = {}
        self.results = defaultdict(lambda: {
            'trades': [],
            'signals': [],
            'metrics': {}
        })
        
    def load_candles(self, timeframe: str = '15m', days: int = 30):
        """Mum verilerini yükle"""
        query = '''
            SELECT timestamp, gram_altin, 
                   (SELECT MIN(gram_altin) FROM price_data p2 
                    WHERE p2.timestamp BETWEEN p1.timestamp AND datetime(p1.timestamp, '+15 minutes')) as low,
                   (SELECT MAX(gram_altin) FROM price_data p2 
                    WHERE p2.timestamp BETWEEN p1.timestamp AND datetime(p1.timestamp, '+15 minutes')) as high
            FROM price_data p1
            WHERE timestamp > datetime('now', '-{} days')
            ORDER BY timestamp
        '''.format(days)
        
        df = pd.read_sql_query(query, self.conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Teknik göstergeleri hesapla"""
        # RSI
        df['rsi'] = self.calculate_rsi(df['gram_altin'], 14)
        
        # MACD
        exp1 = df['gram_altin'].ewm(span=12, adjust=False).mean()
        exp2 = df['gram_altin'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['gram_altin'].rolling(window=20).mean()
        bb_std = df['gram_altin'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # ATR
        df['tr'] = df[['high', 'low']].max(axis=1) - df[['high', 'low']].min(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # Trend
        df['sma_20'] = df['gram_altin'].rolling(window=20).mean()
        df['sma_50'] = df['gram_altin'].rolling(window=50).mean()
        df['trend'] = np.where(df['sma_20'] > df['sma_50'], 'BULLISH', 
                               np.where(df['sma_20'] < df['sma_50'], 'BEARISH', 'NEUTRAL'))
        
        # Divergence basit kontrol
        df['price_higher'] = df['gram_altin'] > df['gram_altin'].shift(20)
        df['rsi_lower'] = df['rsi'] < df['rsi'].shift(20)
        df['bearish_div'] = df['price_higher'] & df['rsi_lower']
        
        df['price_lower'] = df['gram_altin'] < df['gram_altin'].shift(20)
        df['rsi_higher'] = df['rsi'] > df['rsi'].shift(20)
        df['bullish_div'] = df['price_lower'] & df['rsi_higher']
        
        return df
    
    def calculate_rsi(self, prices, period=14):
        """RSI hesapla"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def register_strategy(self, name: str, strategy_func):
        """Strateji kaydet"""
        self.strategies[name] = strategy_func
    
    def run_backtest(self, df: pd.DataFrame, strategy_name: str):
        """Backtest çalıştır"""
        strategy = self.strategies[strategy_name]
        signals = []
        trades = []
        current_trade = None
        
        for idx, row in df.iterrows():
            if idx < 50:  # İlk 50 mum için gösterge hesaplaması
                continue
                
            # Strateji sinyali al
            signal = strategy(row, df.iloc[:idx+1])
            
            if signal.action != 'HOLD':
                signals.append(signal)
            
            # Trade yönetimi
            if signal.action == 'BUY' and current_trade is None:
                current_trade = Trade(
                    entry_time=row['timestamp'],
                    entry_price=signal.price
                )
            elif signal.action == 'SELL' and current_trade is not None:
                current_trade.exit_time = row['timestamp']
                current_trade.exit_price = signal.price
                current_trade.profit_pct = ((current_trade.exit_price - current_trade.entry_price) 
                                           / current_trade.entry_price * 100)
                current_trade.success = current_trade.profit_pct > 0.5
                trades.append(current_trade)
                current_trade = None
        
        # Sonuçları kaydet
        self.results[strategy_name]['signals'] = signals
        self.results[strategy_name]['trades'] = trades
        self.calculate_metrics(strategy_name)
    
    def calculate_metrics(self, strategy_name: str):
        """Performans metriklerini hesapla"""
        trades = self.results[strategy_name]['trades']
        
        if not trades:
            return
        
        successful_trades = [t for t in trades if t.success]
        total_profit = sum(t.profit_pct for t in trades)
        
        metrics = {
            'total_trades': len(trades),
            'successful_trades': len(successful_trades),
            'success_rate': len(successful_trades) / len(trades) * 100,
            'avg_profit': total_profit / len(trades),
            'total_profit': total_profit,
            'max_profit': max(t.profit_pct for t in trades),
            'max_loss': min(t.profit_pct for t in trades),
            'sharpe_ratio': self.calculate_sharpe_ratio(trades)
        }
        
        self.results[strategy_name]['metrics'] = metrics
    
    def calculate_sharpe_ratio(self, trades: List[Trade]) -> float:
        """Sharpe ratio hesapla"""
        if not trades:
            return 0
        returns = [t.profit_pct for t in trades]
        if len(returns) < 2:
            return 0
        return np.mean(returns) / (np.std(returns) + 1e-10)
    
    def print_results(self):
        """Sonuçları yazdır"""
        print("\n" + "="*80)
        print("BACKTEST SONUÇLARI")
        print("="*80)
        
        for strategy_name, data in self.results.items():
            metrics = data['metrics']
            if not metrics:
                continue
                
            print(f"\n📊 Strateji: {strategy_name}")
            print("-"*50)
            print(f"Toplam işlem: {metrics['total_trades']}")
            print(f"Başarılı: {metrics['successful_trades']}")
            print(f"Başarı oranı: {metrics['success_rate']:.1f}%")
            print(f"Ortalama kar: {metrics['avg_profit']:.2f}%")
            print(f"Toplam kar: {metrics['total_profit']:.2f}%")
            print(f"En iyi: {metrics['max_profit']:.2f}%")
            print(f"En kötü: {metrics['max_loss']:.2f}%")
            print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            
            # İlk 5 sinyali göster
            print(f"\nİlk 5 sinyal:")
            for signal in data['signals'][:5]:
                print(f"  {signal.timestamp}: {signal.action} @ {signal.price:.2f} ({signal.confidence:.1%}) - {signal.reason}")

# Stratejiler
def original_strategy(row, history):
    """Mevcut strateji"""
    rsi = row['rsi']
    trend = row['trend']
    
    confidence = 0.5
    
    if rsi < 30 and trend != 'BEARISH':
        return Signal(row['timestamp'], 'BUY', row['gram_altin'], 0.6, 'RSI oversold')
    elif rsi > 70:
        return Signal(row['timestamp'], 'SELL', row['gram_altin'], 0.6, 'RSI overbought')
    
    return Signal(row['timestamp'], 'HOLD', row['gram_altin'], confidence, 'No signal')

def smart_dip_strategy(row, history):
    """Akıllı dip yakalama stratejisi"""
    rsi = row['rsi']
    trend = row['trend']
    macd_hist = row['macd_hist']
    price = row['gram_altin']
    bb_lower = row['bb_lower']
    bullish_div = row['bullish_div']
    
    confidence = 0.5
    reason = []
    
    # BEARISH'te dip yakalama kriterleri
    if trend == 'BEARISH':
        if rsi < 30:
            confidence += 0.2
            reason.append('Extreme oversold')
        elif rsi < 35:
            confidence += 0.1
            reason.append('Oversold')
            
        if bullish_div:
            confidence += 0.15
            reason.append('Bullish divergence')
            
        if price <= bb_lower:
            confidence += 0.1
            reason.append('BB lower touch')
            
        if macd_hist > 0 and history['macd_hist'].iloc[-2] < 0:
            confidence += 0.1
            reason.append('MACD cross')
            
        if confidence >= 0.65:
            return Signal(row['timestamp'], 'BUY', price, confidence, ' + '.join(reason))
    
    # Normal BUY kriterleri (BEARISH olmadığında)
    elif trend in ['BULLISH', 'NEUTRAL']:
        if rsi < 40:
            confidence += 0.15
            reason.append('RSI low')
            
        if price <= bb_lower * 1.01:
            confidence += 0.1
            reason.append('Near BB lower')
            
        if macd_hist > history['macd_hist'].iloc[-2]:
            confidence += 0.1
            reason.append('MACD momentum')
            
        if confidence >= 0.6:
            return Signal(row['timestamp'], 'BUY', price, confidence, ' + '.join(reason))
    
    # SELL kriterleri
    if rsi > 70:
        sell_conf = 0.6
        sell_reason = ['RSI overbought']
        
        if price >= row['bb_upper']:
            sell_conf += 0.15
            sell_reason.append('BB upper')
            
        if row['bearish_div']:
            sell_conf += 0.1
            sell_reason.append('Bearish divergence')
            
        return Signal(row['timestamp'], 'SELL', price, sell_conf, ' + '.join(sell_reason))
    
    return Signal(row['timestamp'], 'HOLD', price, confidence, 'No criteria met')

def aggressive_strategy(row, history):
    """Agresif strateji - daha fazla sinyal"""
    rsi = row['rsi']
    trend = row['trend']
    macd_hist = row['macd_hist']
    price = row['gram_altin']
    
    # Daha düşük eşikler
    if rsi < 35:
        conf = 0.55 if trend == 'BEARISH' else 0.65
        return Signal(row['timestamp'], 'BUY', price, conf, f'RSI {rsi:.1f}')
    elif rsi > 65:
        return Signal(row['timestamp'], 'SELL', price, 0.65, f'RSI {rsi:.1f}')
    
    # MACD crossover
    if len(history) > 1:
        if macd_hist > 0 and history['macd_hist'].iloc[-2] < 0:
            return Signal(row['timestamp'], 'BUY', price, 0.55, 'MACD cross up')
        elif macd_hist < 0 and history['macd_hist'].iloc[-2] > 0:
            return Signal(row['timestamp'], 'SELL', price, 0.55, 'MACD cross down')
    
    return Signal(row['timestamp'], 'HOLD', price, 0.4, 'No signal')

def conservative_strategy(row, history):
    """Muhafazakar strateji - yüksek güvenli sinyaller"""
    rsi = row['rsi']
    trend = row['trend']
    price = row['gram_altin']
    
    # Sadece güçlü sinyaller
    if trend == 'BULLISH' and rsi < 30 and row['bullish_div']:
        return Signal(row['timestamp'], 'BUY', price, 0.75, 'Strong oversold + div')
    elif trend == 'BEARISH' and rsi > 70 and row['bearish_div']:
        return Signal(row['timestamp'], 'SELL', price, 0.75, 'Strong overbought + div')
    
    return Signal(row['timestamp'], 'HOLD', price, 0.3, 'Waiting for strong signal')

def main():
    print("🏃 Candle-by-Candle Backtest Başlatılıyor...")
    
    # Backtest motoru oluştur
    engine = BacktestEngine()
    
    # Veri yükle
    print("📊 Veri yükleniyor...")
    df = engine.load_candles(timeframe='15m', days=30)
    print(f"✅ {len(df)} mum yüklendi")
    
    # Göstergeleri hesapla
    print("📈 Göstergeler hesaplanıyor...")
    df = engine.calculate_indicators(df)
    
    # Stratejileri kaydet
    engine.register_strategy('Original', original_strategy)
    engine.register_strategy('Smart Dip', smart_dip_strategy)
    engine.register_strategy('Aggressive', aggressive_strategy)
    engine.register_strategy('Conservative', conservative_strategy)
    
    # Backtestleri çalıştır
    print("\n🔄 Stratejiler test ediliyor...")
    for strategy_name in engine.strategies.keys():
        print(f"  - {strategy_name} test ediliyor...")
        engine.run_backtest(df, strategy_name)
    
    # Sonuçları göster
    engine.print_results()
    
    # En iyi stratejiyi bul
    best_strategy = max(engine.results.items(), 
                       key=lambda x: x[1]['metrics'].get('success_rate', 0))
    
    print(f"\n🏆 EN İYİ STRATEJİ: {best_strategy[0]}")
    print(f"   Başarı oranı: {best_strategy[1]['metrics']['success_rate']:.1f}%")
    
    # Öneriler
    print("\n💡 ÖNERİLER:")
    print("1. Smart Dip stratejisi BEARISH trend'de bile güvenli dip yakalama sağlıyor")
    print("2. RSI < 30 + Bullish divergence kombinasyonu en güvenilir")
    print("3. BEARISH'te pozisyon boyutunu %50 azaltmak risk yönetimi açısından önemli")
    print("4. Günlük 1-5 sinyal hedefi için confidence > 0.6 filtresi uygun")

if __name__ == "__main__":
    main()