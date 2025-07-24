"""
Gerçek veri ile HybridStrategy testi
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategies.hybrid_strategy import HybridStrategy
from storage.sqlite_storage import SQLiteStorage
from models.market_data import MarketData
from utils import timezone


def test_with_real_data():
    """Gerçek veri ile test"""
    print("🔧 Gerçek veri testi başlıyor...\n")
    
    # Storage ve strategy oluştur
    storage = SQLiteStorage()
    strategy = HybridStrategy(storage)
    
    # Test edilecek timeframe'ler
    timeframes = ["15m", "1h", "4h", "1d"]
    
    for timeframe in timeframes:
        print(f"\n📊 {timeframe} Timeframe Testi")
        print("=" * 50)
        
        try:
            # Son candle'ları al
            candles = storage.get_recent_candles(timeframe, 100)
            
            if not candles or len(candles) < 20:
                print(f"❌ Yetersiz veri: {len(candles) if candles else 0} candle")
                continue
            
            print(f"✅ {len(candles)} candle bulundu")
            
            # Son market data'yı oluştur
            latest_candle = candles[-1]
            market_data = [
                MarketData(
                    gram_altin=latest_candle.close,
                    ons_usd=2000,  # Varsayılan
                    usd_try=30,     # Varsayılan
                    ons_try=60000   # Varsayılan
                )
            ]
            
            # Analiz yap
            result = strategy.analyze(candles, market_data, timeframe)
            
            # Sonuçları yazdır
            print(f"\n📈 Analiz Sonuçları:")
            print(f"Sinyal: {result['signal']}")
            print(f"Güven: {result['confidence']:.2%}")
            print(f"Güç: {result['signal_strength']}")
            print(f"Pozisyon Boyutu: {result['position_size']:.2f} lot")
            
            # Modül sonuçları
            print(f"\n🔍 Modül Analizleri:")
            
            # Divergence
            div = result.get('divergence_analysis', {})
            print(f"- Divergence: {div.get('divergence_type', 'NONE')} "
                  f"(Skor: {div.get('total_score', 0)}, Güç: {div.get('strength', 'NONE')})")
            
            # Structure
            struct = result.get('structure_analysis', {})
            print(f"- Structure: {struct.get('current_structure', 'NEUTRAL')} "
                  f"(Break: {struct.get('structure_break', False)})")
            
            # Momentum
            mom = result.get('momentum_analysis', {})
            if mom.get('exhaustion_detected'):
                print(f"- Momentum: {mom.get('exhaustion_type', 'NONE')} EXHAUSTION "
                      f"(Skor: {mom.get('exhaustion_score', 0):.2f})")
            else:
                print(f"- Momentum: Normal (Skor: {mom.get('exhaustion_score', 0):.2f})")
            
            # Smart Money
            sm = result.get('smart_money_analysis', {})
            print(f"- Smart Money: {sm.get('smart_money_direction', 'NEUTRAL')} "
                  f"(Manipulation: {sm.get('manipulation_score', 0):.2f})")
            
            # Confluence
            conf = result.get('confluence_analysis', {})
            print(f"- Confluence: {conf.get('confluence_score', 0):.1f}% "
                  f"(Parent: {conf.get('parent_confirmation', False)})")
            
            # Risk levels
            if result['signal'] != 'HOLD':
                print(f"\n💰 Risk Yönetimi:")
                print(f"Stop Loss: {result['stop_loss']:.2f}")
                print(f"Take Profit: {result['take_profit']:.2f}")
                print(f"Risk/Reward: {result['risk_reward_ratio']:.2f}")
            
            # Öneriler
            if result.get('recommendations'):
                print(f"\n💡 Öneriler:")
                for rec in result['recommendations']:
                    print(f"- {rec}")
            
        except Exception as e:
            print(f"❌ Hata: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n\n🎯 Özet Analiz")
    print("=" * 50)
    
    # Tüm timeframe'lerde son sinyalleri topla
    all_signals = {}
    for tf in timeframes:
        try:
            analysis = storage.get_latest_hybrid_analysis(tf)
            if analysis:
                all_signals[tf] = {
                    'signal': analysis.get('signal', 'HOLD'),
                    'confidence': analysis.get('confidence', 0),
                    'timestamp': analysis.get('timestamp')
                }
        except:
            pass
    
    if all_signals:
        print("\n🔄 Son Sinyaller:")
        for tf, signal_data in all_signals.items():
            print(f"{tf}: {signal_data['signal']} ({signal_data['confidence']:.2%})")
    
    # Dip/Tepe yakalama özeti
    print("\n🎯 Dip/Tepe Yakalama Analizi:")
    
    # En son 1h analizi için detaylı kontrol
    try:
        analysis_1h = storage.get_latest_hybrid_analysis("1h")
        if analysis_1h:
            # Divergence kontrolü
            div = analysis_1h.get('divergence_analysis', {})
            if div.get('strength') in ['STRONG', 'MODERATE']:
                print(f"⚡ {div.get('divergence_type')} Divergence tespit edildi!")
            
            # Momentum exhaustion
            mom = analysis_1h.get('momentum_analysis', {})
            if mom.get('exhaustion_detected'):
                if mom.get('exhaustion_type') == 'BULLISH':
                    print("📈 DİP sinyalleri güçlü - Alım fırsatı yakın!")
                elif mom.get('exhaustion_type') == 'BEARISH':
                    print("📉 TEPE sinyalleri güçlü - Satış fırsatı yakın!")
            
            # Structure break
            struct = analysis_1h.get('structure_analysis', {})
            if struct.get('structure_break'):
                print(f"🔄 Market structure kırılımı: {struct.get('break_type')}")
            
            # Smart money
            sm = analysis_1h.get('smart_money_analysis', {})
            if sm.get('stop_hunt_detected'):
                print("🎣 Stop hunt tespit edildi - Kurumsal hareket var!")
    except:
        pass
    
    print("\n✅ Test tamamlandı!")


if __name__ == "__main__":
    test_with_real_data()