#!/usr/bin/env python3
"""
Yeni özellikleri test etmek için script
CCI, MFI, Pattern Recognition ve Kelly Risk Management testleri
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal

# Path'e ekle
sys.path.append('.')

from indicators.cci import CCI
from indicators.mfi import MFI
from indicators.advanced_patterns import AdvancedPatternRecognition
from utils.risk_management import KellyRiskManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_data(days=50, trend="sideways"):
    """Test için OHLCV verisi oluştur"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='1H')
    
    # Base price
    base_price = 4400  # Gram altın örnek fiyat
    
    data = []
    for i, date in enumerate(dates):
        # Trend simulation
        if trend == "bullish":
            trend_factor = 1 + (i / days) * 0.05  # %5 yükseliş
        elif trend == "bearish":
            trend_factor = 1 - (i / days) * 0.05  # %5 düşüş
        else:  # sideways
            trend_factor = 1 + 0.02 * np.sin(i / 5)  # Sinüzoidal hareket
        
        # Random volatility
        volatility = np.random.uniform(0.002, 0.01)  # %0.2 - %1 volatilite
        
        close = base_price * trend_factor * (1 + np.random.uniform(-volatility, volatility))
        high = close * (1 + np.random.uniform(0, volatility))
        low = close * (1 - np.random.uniform(0, volatility))
        open_price = close * (1 + np.random.uniform(-volatility/2, volatility/2))
        
        # Simulated volume
        volume = np.random.uniform(1000000, 5000000) * (1 + volatility * 10)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    return pd.DataFrame(data)

def test_cci():
    """CCI göstergesini test et"""
    print("\n" + "="*50)
    print("CCI (Commodity Channel Index) Testi")
    print("="*50)
    
    # Test verisi oluştur
    df = create_test_data(days=50, trend="bullish")
    
    # CCI hesapla
    cci = CCI(period=20)
    cci_values = cci.calculate(df)
    
    # Son değeri analiz et
    analysis = cci.get_analysis(df)
    
    print(f"\nSon CCI Değeri: {analysis['value']}")
    print(f"Sinyal: {analysis['signal']}")
    print(f"Güven Skoru: {analysis['confidence']}")
    print(f"Trend: {analysis['trend']} (Güç: {analysis['trend_strength']})")
    print(f"Divergence: {analysis['divergence']}")
    print(f"Aşırı Alım: {analysis['overbought']}")
    print(f"Aşırı Satım: {analysis['oversold']}")
    
    # CCI değerlerinin dağılımı
    print(f"\nCCI İstatistikleri:")
    print(f"Min: {cci_values.min():.2f}")
    print(f"Max: {cci_values.max():.2f}")
    print(f"Ortalama: {cci_values.mean():.2f}")
    print(f"Std Dev: {cci_values.std():.2f}")
    
    return analysis

def test_mfi():
    """MFI göstergesini test et"""
    print("\n" + "="*50)
    print("MFI (Money Flow Index) Testi")
    print("="*50)
    
    # Test verisi oluştur
    df = create_test_data(days=50, trend="bearish")
    
    # MFI hesapla
    mfi = MFI(period=14)
    mfi_values = mfi.calculate(df)
    
    # Son değeri analiz et
    analysis = mfi.get_analysis(df)
    
    print(f"\nSon MFI Değeri: {analysis['value']}")
    print(f"Sinyal: {analysis['signal']}")
    print(f"Güven Skoru: {analysis['confidence']}")
    print(f"Divergence: {analysis['divergence']}")
    print(f"Aşırı Alım: {analysis['overbought']}")
    print(f"Aşırı Satım: {analysis['oversold']}")
    
    # Hacim analizi
    volume_analysis = analysis['volume_analysis']
    print(f"\nHacim Analizi:")
    print(f"Hacim Trendi: {volume_analysis['volume_trend']} (Güç: {volume_analysis['trend_strength']})")
    print(f"Para Akışı: {volume_analysis['money_flow']} (Güç: {volume_analysis['flow_strength']})")
    print(f"Birikim: {volume_analysis['accumulation']}")
    print(f"Dağıtım: {volume_analysis['distribution']}")
    
    return analysis

def test_patterns():
    """Pattern tanıma test et"""
    print("\n" + "="*50)
    print("Pattern Recognition Testi")
    print("="*50)
    
    # Head & Shoulders pattern simülasyonu
    days = 60
    df = pd.DataFrame()
    
    # Sol omuz
    left_shoulder = np.linspace(4400, 4500, 15)
    left_valley = np.linspace(4500, 4450, 5)
    
    # Baş
    head = np.linspace(4450, 4550, 15)
    head_valley = np.linspace(4550, 4460, 5)
    
    # Sağ omuz
    right_shoulder = np.linspace(4460, 4510, 15)
    final_drop = np.linspace(4510, 4440, 5)
    
    # Birleştir
    prices = np.concatenate([left_shoulder, left_valley, head, head_valley, right_shoulder, final_drop])
    
    # DataFrame oluştur
    data = []
    for i, price in enumerate(prices):
        volatility = 0.002
        data.append({
            'high': price * (1 + volatility),
            'low': price * (1 - volatility),
            'close': price,
            'open': price * (1 + np.random.uniform(-volatility/2, volatility/2))
        })
    
    df = pd.DataFrame(data)
    
    # Pattern tanıma
    recognizer = AdvancedPatternRecognition()
    patterns = recognizer.analyze_all_patterns(df)
    
    print(f"\nPattern Bulundu: {patterns['pattern_found']}")
    if patterns['pattern_found']:
        best = patterns['best_pattern']
        print(f"Pattern: {best['pattern']}")
        print(f"Tip: {best['type']}")
        print(f"Güven: {best['confidence']}")
        print(f"Neckline: {best.get('neckline', 'N/A')}")
        print(f"Hedef: {best.get('target', 'N/A')}")
        print(f"Stop Loss: {best.get('stop_loss', 'N/A')}")
    
    return patterns

def test_kelly_risk():
    """Kelly risk yönetimini test et"""
    print("\n" + "="*50)
    print("Kelly Risk Management Testi")
    print("="*50)
    
    risk_manager = KellyRiskManager()
    
    # Test parametreleri
    capital = 10000  # 10K TL (daha makul)
    entry_price = 4400
    stop_loss_price = 4350  # ~%1.1 risk
    
    # Farklı güven skorları için test
    confidence_levels = [0.5, 0.7, 0.9]
    
    print(f"\nSermaye: ₺{capital:,}")
    print(f"Giriş Fiyatı: ₺{entry_price}")
    print(f"Stop Loss: ₺{stop_loss_price}")
    print(f"Fiyat Riski: %{((entry_price - stop_loss_price) / entry_price * 100):.2f}")
    
    for confidence in confidence_levels:
        position = risk_manager.calculate_position_size(
            capital, entry_price, stop_loss_price, confidence
        )
        
        print(f"\n--- Güven Skoru: {confidence} ---")
        print(f"Pozisyon Büyüklüğü: ₺{position['position_size']:,.2f}")
        print(f"Lot (Gram): {position['lots']:.3f}")
        print(f"Risk Miktarı: ₺{position['risk_amount']:,.2f}")
        print(f"Risk Yüzdesi: %{position['risk_percentage']}")
        print(f"Kelly Yüzdesi: %{position['kelly_percentage']}")
        
    # Trading istatistikleri simülasyonu
    print("\n--- Trading İstatistikleri ---")
    
    # Örnek trade'ler ekle
    trades = [
        (4400, 4450, 1000, 'BUY'),   # Kazanç
        (4450, 4420, 1000, 'SELL'),  # Kazanç
        (4420, 4400, 1000, 'BUY'),   # Kayıp
        (4400, 4480, 1000, 'BUY'),   # Kazanç
        (4480, 4450, 1000, 'SELL'),  # Kazanç
    ]
    
    for entry, exit, size, trade_type in trades:
        risk_manager.add_trade_result(entry, exit, size, trade_type)
    
    stats = risk_manager.calculate_trading_stats()
    print(f"Toplam İşlem: {stats['total_trades']}")
    print(f"Kazanma Oranı: %{stats['win_rate'] * 100:.1f}")
    print(f"Ortalama Kazanç/Kayıp: {stats['avg_win_loss_ratio']:.2f}")
    print(f"Profit Factor: {stats['profit_factor']}")
    
    return position

def test_integration():
    """Entegre sistem testi"""
    print("\n" + "="*50)
    print("Entegre Sistem Testi")
    print("="*50)
    
    try:
        from strategies.hybrid_strategy import HybridStrategy
        from models.market_data import GramAltinCandle, MarketData
        
        # Test verisi
        df = create_test_data(days=100, trend="bullish")
        
        # GramAltinCandle listesi oluştur
        gram_candles = []
        for _, row in df.iterrows():
            candle = GramAltinCandle(
                timestamp=row['timestamp'],
                open=Decimal(str(row['open'])),
                high=Decimal(str(row['high'])),
                low=Decimal(str(row['low'])),
                close=Decimal(str(row['close'])),
                volume=int(row['volume']),  # Integer olarak
                interval="1h"  # Zorunlu alan
            )
            gram_candles.append(candle)
        
        # Market data (basit)
        market_data = [
            MarketData(
                timestamp=datetime.now(),
                symbol="XAU/USD",
                price=Decimal("2650.50"),
                volume=Decimal("1000000")
            ),
            MarketData(
                timestamp=datetime.now(),
                symbol="USD/TRY",
                price=Decimal("34.50"),
                volume=Decimal("5000000")
            )
        ]
        
        # Hybrid strategy test
        strategy = HybridStrategy()
        result = strategy.analyze(gram_candles, market_data)
        
        print(f"\n--- Hybrid Strategy Sonuçları ---")
        print(f"Gram Fiyat: ₺{result['gram_price']}")
        print(f"Sinyal: {result['signal']}")
        print(f"Güven: {result['confidence']:.3f}")
        print(f"Sinyal Gücü: {result['signal_strength']}")
        
        # Risk yönetimi
        print(f"\n--- Risk Yönetimi ---")
        print(f"Pozisyon Boyutu (Lot): {result['position_size']:.3f}")
        print(f"Stop Loss: ₺{result['stop_loss']}")
        print(f"Take Profit: ₺{result['take_profit']}")
        print(f"Risk/Ödül Oranı: {result['risk_reward_ratio']:.2f}")
        
        # Gelişmiş göstergeler
        if 'advanced_indicators' in result:
            adv = result['advanced_indicators']
            print(f"\n--- Gelişmiş Göstergeler ---")
            print(f"CCI: {adv['cci']['value']} ({adv['cci']['signal']})")
            print(f"MFI: {adv['mfi']['value']} ({adv['mfi']['signal']})")
            print(f"Birleşik Sinyal: {adv['combined_signal']}")
        
        # Pattern analizi
        if 'pattern_analysis' in result:
            patterns = result['pattern_analysis']
            print(f"\n--- Pattern Analizi ---")
            print(f"Pattern Bulundu: {patterns['pattern_found']}")
            if patterns['pattern_found']:
                print(f"En İyi Pattern: {patterns['best_pattern']['pattern']}")
        
        print(f"\n--- Özet ---")
        print(f"Özet: {result['summary']}")
        print(f"Öneriler: {', '.join(result['recommendations'])}")
        
        return result
        
    except Exception as e:
        print(f"Entegrasyon testi hatası: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Ana test fonksiyonu"""
    print("🧪 Gold Price Analyzer - Yeni Özellikler Test Suite")
    print("=" * 60)
    
    # 1. CCI Testi
    cci_result = test_cci()
    
    # 2. MFI Testi
    mfi_result = test_mfi()
    
    # 3. Pattern Tanıma Testi
    pattern_result = test_patterns()
    
    # 4. Kelly Risk Yönetimi Testi
    kelly_result = test_kelly_risk()
    
    # 5. Entegre Sistem Testi
    integration_result = test_integration()
    
    print("\n" + "="*60)
    print("✅ Tüm testler tamamlandı!")
    print("="*60)

if __name__ == "__main__":
    main()