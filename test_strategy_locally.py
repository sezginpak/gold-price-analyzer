#!/usr/bin/env python3
"""
Local test - Güncellenmiş stratejiyi test et
"""
import sys
sys.path.insert(0, '.')

from strategies.hybrid_strategy import HybridStrategy
from storage.sqlite_storage import SQLiteStorage
from models.market_data import GramAltinCandle
from datetime import datetime, timedelta
import json

def test_strategy():
    """Stratejiyi local veritabanıyla test et"""
    print("🧪 Strateji Testi Başlıyor...")
    
    # Storage ve strateji oluştur
    storage = SQLiteStorage()
    strategy = HybridStrategy()
    
    # Son verileri al
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=6)
    
    # 15m, 1h, 4h için test
    for timeframe in ['15m', '1h', '4h']:
        print(f"\n\n{'='*60}")
        print(f"📊 Timeframe: {timeframe}")
        print('='*60)
        
        # Mum verilerini al
        candles = storage.get_candles('GRAM_ALTIN', timeframe, start_time, end_time)
        
        if not candles or len(candles) < 30:
            print(f"❌ Yeterli veri yok: {len(candles) if candles else 0} mum")
            continue
            
        print(f"✅ {len(candles)} mum yüklendi")
        
        # Market data hazırla
        market_data = {
            'gram_candles': candles,
            'ons_candles': candles,  # Aynı veriyi kullan
            'usd_try_candles': candles  # Aynı veriyi kullan
        }
        
        # Strateji analizi
        result = strategy.analyze(market_data, timeframe)
        
        # Sonuçları yazdır
        print(f"\n📈 ANALİZ SONUÇLARI:")
        print(f"Signal: {result['signal']}")
        print(f"Confidence: {result['confidence']:.2%}")
        print(f"Strength: {result['signal_strength']}")
        
        # Dip detection kontrolü
        combined_signal = result.get('_debug_combined_signal', {})
        dip_detection = combined_signal.get('dip_detection', {})
        if dip_detection.get('is_dip_opportunity'):
            print(f"\n🎯 DIP FIRSAT TESPİTİ!")
            print(f"Dip Score: {dip_detection.get('score', 0):.2f}")
            for signal in dip_detection.get('signals', []):
                print(f"  - {signal}")
        
        # Gram analiz detayları
        gram_analysis = result.get('gram_analysis', {})
        if gram_analysis:
            print(f"\n📊 GRAM ANALİZ:")
            print(f"Trend: {gram_analysis.get('trend')}")
            print(f"RSI: {gram_analysis.get('indicators', {}).get('rsi', 'N/A')}")
            print(f"Gram Signal: {gram_analysis.get('signal')}")
            print(f"Gram Confidence: {gram_analysis.get('confidence', 0):.2%}")
        
        # Debug bilgileri
        if '_debug_combined_signal' in result:
            debug = result['_debug_combined_signal']
            print(f"\n🔍 DEBUG:")
            print(f"Raw Confidence: {debug.get('raw_confidence', 0):.3f}")
            print(f"Market Volatility: {debug.get('market_volatility', 0):.3f}%")
            scores = debug.get('scores', {})
            if scores:
                print(f"Signal Scores: BUY={scores.get('BUY', 0):.3f}, SELL={scores.get('SELL', 0):.3f}, HOLD={scores.get('HOLD', 0):.3f}")
        
        # Öneriler
        if result.get('recommendations'):
            print(f"\n💡 ÖNERİLER:")
            for rec in result['recommendations']:
                print(f"  - {rec}")
    
    print("\n\n✅ Test tamamlandı!")

def check_dip_conditions():
    """BEARISH trend'deki potansiyel dipler"""
    print("\n\n🔍 DIP YAKALAMA POTANSİYELİ ANALİZİ")
    print("="*60)
    
    storage = SQLiteStorage()
    
    # Son 24 saatlik hybrid analiz kayıtlarını kontrol et
    import sqlite3
    conn = sqlite3.connect('gold_prices.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            timeframe,
            json_extract(gram_analysis, '$.trend') as trend,
            json_extract(gram_analysis, '$.indicators.rsi') as rsi,
            signal,
            confidence,
            datetime(timestamp, 'localtime') as time
        FROM hybrid_analysis
        WHERE timestamp > datetime('now', '-24 hours')
        AND json_extract(gram_analysis, '$.trend') = 'BEARISH'
        AND json_extract(gram_analysis, '$.indicators.rsi') < 40
        ORDER BY timestamp DESC
        LIMIT 20
    ''')
    
    results = cursor.fetchall()
    
    print(f"\nBEARISH + RSI<40 durumları (son 24 saat):")
    print(f"{'Timeframe':<10} {'Trend':<10} {'RSI':<6} {'Signal':<8} {'Conf':<6} {'Time':<20}")
    print("-"*70)
    
    for row in results:
        tf, trend, rsi, signal, conf, time = row
        print(f"{tf:<10} {trend:<10} {rsi or 0:<6.1f} {signal:<8} {conf*100:<6.1f} {time:<20}")
    
    if not results:
        print("❌ BEARISH + düşük RSI durumu bulunamadı")
    else:
        print(f"\n✅ {len(results)} potansiyel dip fırsatı tespit edildi!")
    
    conn.close()

if __name__ == "__main__":
    test_strategy()
    check_dip_conditions()