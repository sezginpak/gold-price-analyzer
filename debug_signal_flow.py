#!/usr/bin/env python3
"""
Signal akışını debug et - Nerede takılıyor?
"""
import sys
sys.path.insert(0, '/root/gold-price-analyzer')

from strategies.hybrid_strategy import HybridStrategy
from storage.sqlite_storage import SQLiteStorage
from datetime import datetime, timedelta
import logging
import json

# Debug için tüm log'ları aç
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def debug_signal_flow():
    print("=== SIGNAL FLOW DEBUG ===\n")
    
    storage = SQLiteStorage()
    strategy = HybridStrategy()
    
    # Son 1 saatlik veri
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    # 15m timeframe test
    timeframe = '15m'
    print(f"📊 Testing {timeframe} timeframe")
    print("-" * 80)
    
    # Mum verilerini al
    candles = list(storage.generate_candles('GRAM_ALTIN', timeframe))
    recent_candles = [c for c in candles if start_time <= c.timestamp <= end_time]
    
    if len(recent_candles) < 30:
        # Daha eski veriler al
        all_candles = candles[-100:] if len(candles) >= 100 else candles
        print(f"✅ Using last {len(all_candles)} candles")
    else:
        all_candles = recent_candles
        print(f"✅ Using {len(all_candles)} recent candles")
    
    # Market data
    market_data = {
        'gram_candles': all_candles,
        'ons_candles': all_candles,
        'usd_try_candles': all_candles
    }
    
    # Debug noktaları ekle
    print("\n🔍 DEBUGGING SIGNAL FLOW:")
    print("="*80)
    
    # 1. Gram Analyzer çıktısı
    print("\n1️⃣ GRAM ANALYZER OUTPUT:")
    gram_result = strategy.gram_analyzer.analyze(all_candles)
    print(f"   Signal: {gram_result.get('signal')}")
    print(f"   Confidence: {gram_result.get('confidence', 0):.2%}")
    print(f"   Trend: {gram_result.get('trend')}")
    print(f"   RSI: {gram_result.get('indicators', {}).get('rsi', 'N/A')}")
    
    # 2. Advanced Indicators
    print("\n2️⃣ ADVANCED INDICATORS:")
    adv_result = strategy._analyze_advanced_indicators(all_candles)
    print(f"   Combined Signal: {adv_result.get('combined_signal')}")
    print(f"   Combined Confidence: {adv_result.get('combined_confidence', 0):.2%}")
    print(f"   RSI from adv: {adv_result.get('rsi', 'N/A')}")
    
    # 3. Full Analysis
    print("\n3️⃣ HYBRID STRATEGY FULL ANALYSIS:")
    try:
        full_result = strategy.analyze(market_data, timeframe)
        
        print(f"   Final Signal: {full_result['signal']}")
        print(f"   Final Confidence: {full_result['confidence']:.2%}")
        print(f"   Signal Strength: {full_result['signal_strength']}")
        
        # Debug bilgisi varsa
        if '_debug_combined_signal' in full_result:
            debug_info = full_result['_debug_combined_signal']
            print(f"\n   📊 SIGNAL COMBINER DEBUG:")
            print(f"      Raw Confidence: {debug_info.get('raw_confidence', 0):.3f}")
            print(f"      Market Volatility: {debug_info.get('market_volatility', 0):.3f}%")
            print(f"      Dip Score: {debug_info.get('dip_detection', {}).get('score', 0):.3f}")
            
            scores = debug_info.get('scores', {})
            if scores:
                print(f"      Signal Scores:")
                for sig, score in scores.items():
                    print(f"         {sig}: {score:.3f}")
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Son hybrid_analysis kaydını kontrol et
    print("\n4️⃣ DATABASE CHECK:")
    conn = storage.conn
    cursor = conn.cursor()
    cursor.execute('''
        SELECT signal, confidence, gram_analysis
        FROM hybrid_analysis 
        WHERE timeframe = ?
        ORDER BY timestamp DESC 
        LIMIT 1
    ''', (timeframe,))
    
    db_result = cursor.fetchone()
    if db_result:
        signal, conf, gram_json = db_result
        print(f"   DB Signal: {signal}")
        print(f"   DB Confidence: {conf:.2%}")
        
        gram_data = json.loads(gram_json) if gram_json else {}
        print(f"   DB Gram Signal: {gram_data.get('signal', 'N/A')}")
        print(f"   DB Gram Conf: {gram_data.get('confidence', 0):.2%}")

if __name__ == "__main__":
    debug_signal_flow()