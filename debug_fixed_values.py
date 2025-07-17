"""
Debug script - Sabit değer sorununu test et
"""
from datetime import datetime
from decimal import Decimal
from models.market_data import MarketData, GramAltinCandle
from strategies.hybrid_strategy import HybridStrategy
import random

def create_test_data():
    """Test verisi oluştur"""
    # Farklı senaryolar için gram altın mumları
    gram_candles = []
    base_price = 2800
    
    for i in range(50):
        # Değişken fiyatlar oluştur
        variation = random.uniform(-50, 50)
        open_price = base_price + variation
        close_price = open_price + random.uniform(-20, 20)
        high_price = max(open_price, close_price) + random.uniform(0, 10)
        low_price = min(open_price, close_price) - random.uniform(0, 10)
        
        candle = GramAltinCandle(
            timestamp=datetime.now(),
            open=Decimal(str(open_price)),
            high=Decimal(str(high_price)),
            low=Decimal(str(low_price)),
            close=Decimal(str(close_price)),
            interval="15m"
        )
        gram_candles.append(candle)
        base_price = close_price
    
    # Market data - farklı USD/TRY değerleri
    market_data = []
    usd_try_base = 35.0
    
    for i in range(100):
        # USD/TRY'de değişkenlik
        usd_variation = random.uniform(-0.5, 0.5)
        usd_try = usd_try_base + usd_variation
        
        # ONS/USD
        ons_usd = 2000 + random.uniform(-50, 50)
        
        data = MarketData(
            timestamp=datetime.now(),
            ons_usd=Decimal(str(ons_usd)),
            usd_try=Decimal(str(usd_try)),
            ons_try=Decimal(str(ons_usd * usd_try)),
            gram_altin=Decimal(str((ons_usd * usd_try) / 31.1035))
        )
        market_data.append(data)
        usd_try_base = usd_try
    
    return gram_candles, market_data

def test_hybrid_strategy():
    """Hibrit stratejiyi test et"""
    strategy = HybridStrategy()
    
    print("🧪 HİBRİT STRATEJİ TEST")
    print("=" * 80)
    
    # 5 farklı senaryo test et
    scenarios = [
        ("Yükseliş Trendi", 2800, 2900, 0.1),
        ("Düşüş Trendi", 2800, 2700, -0.1),
        ("Yatay Piyasa", 2800, 2800, 0),
        ("Yüksek Volatilite", 2800, 2850, 0.2),
        ("Düşük Volatilite", 2800, 2810, 0.05)
    ]
    
    results = []
    
    for scenario_name, start_price, end_price, volatility in scenarios:
        print(f"\n📊 Senaryo: {scenario_name}")
        print("-" * 60)
        
        # Test verisi oluştur
        gram_candles, market_data = create_test_data()
        
        # Senaryoya göre ayarla
        price_range = end_price - start_price
        for i, candle in enumerate(gram_candles):
            progress = i / len(gram_candles)
            new_price = start_price + (price_range * progress)
            noise = random.uniform(-abs(volatility) * 50, abs(volatility) * 50)
            
            candle.close = Decimal(str(new_price + noise))
            candle.open = Decimal(str(new_price + noise * 0.5))
            candle.high = candle.close + Decimal(str(abs(noise) * 0.3))
            candle.low = candle.close - Decimal(str(abs(noise) * 0.3))
        
        # Analiz yap
        result = strategy.analyze(gram_candles, market_data)
        
        # Sonuçları göster
        print(f"  Sinyal: {result['signal']} ({result['signal_strength']})")
        print(f"  Güven: {result['confidence']:.2%}")
        print(f"  Pozisyon: {result['position_size']['recommended_size']:.2%}")
        print(f"  Global Trend: {result['global_trend']['trend_direction']}")
        print(f"  Kur Riski: {result['currency_risk']['risk_level']}")
        
        # Detaylı skorları göster
        if 'scores' in result:
            scores = result.get('scores', {})
            print(f"  Sinyal Skorları:")
            print(f"    - BUY: {scores.get('BUY', 0):.3f}")
            print(f"    - SELL: {scores.get('SELL', 0):.3f}")
            print(f"    - HOLD: {scores.get('HOLD', 0):.3f}")
        
        results.append({
            'scenario': scenario_name,
            'signal': result['signal'],
            'confidence': result['confidence'],
            'position': result['position_size']['recommended_size']
        })
    
    # Özet
    print("\n" + "=" * 80)
    print("📈 TEST SONUÇ ÖZETİ")
    print("=" * 80)
    
    # Değerlerin çeşitliliğini kontrol et
    confidences = [r['confidence'] for r in results]
    positions = [r['position'] for r in results]
    
    print(f"\nGüven Değerleri: {[f'{c:.2%}' for c in confidences]}")
    print(f"Pozisyon Değerleri: {[f'{p:.2%}' for p in positions]}")
    
    unique_conf = len(set(f"{c:.2f}" for c in confidences))
    unique_pos = len(set(f"{p:.2f}" for p in positions))
    
    print(f"\nBenzersiz güven değeri sayısı: {unique_conf}/5")
    print(f"Benzersiz pozisyon değeri sayısı: {unique_pos}/5")
    
    if unique_conf == 1:
        print("❌ SORUN: Tüm güven değerleri aynı!")
    else:
        print("✅ Güven değerleri dinamik!")
    
    if unique_pos == 1:
        print("❌ SORUN: Tüm pozisyon değerleri aynı!")
    else:
        print("✅ Pozisyon değerleri dinamik!")

if __name__ == "__main__":
    test_hybrid_strategy()