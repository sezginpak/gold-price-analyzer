#!/usr/bin/env python3
"""
Zorla bir analiz çalıştır ve debug çıktıları göster
"""
import sys
sys.path.insert(0, '/root/gold-price-analyzer')

# Önce logging'i ayarla
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Console'a yaz
)

# Tüm logger'ları DEBUG yap
for name in ['strategies.hybrid.signal_combiner', 'gold_analyzer', 'strategies.hybrid_strategy']:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

from storage.sqlite_storage import SQLiteStorage
from collectors.harem_price_collector import HaremPriceCollector
from analyzers.gram_altin_analyzer import GramAltinAnalyzer
from strategies.hybrid_strategy import HybridStrategy
from datetime import datetime, timedelta
import asyncio

async def force_analysis():
    """Tek bir analiz çalıştır"""
    print("=== ZORLANMIŞ ANALİZ ===\n")
    
    storage = SQLiteStorage()
    collector = HaremPriceCollector(storage)
    analyzer = GramAltinAnalyzer()
    strategy = HybridStrategy()
    
    # Veri topla
    print("📊 Veri toplanıyor...")
    await collector.collect_price()
    
    # Son verileri al
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=2)
    
    # 15m analizi
    timeframe = '15m'
    print(f"\n🔍 {timeframe} analizi başlıyor...")
    
    # Mum verilerini al
    candles = list(storage.generate_candles('GRAM_ALTIN', timeframe))
    recent_candles = candles[-100:] if len(candles) >= 100 else candles
    
    print(f"✅ {len(recent_candles)} mum hazır")
    
    # Market data
    market_data = {
        'gram_candles': recent_candles,
        'ons_candles': recent_candles,
        'usd_try_candles': recent_candles
    }
    
    # Strateji analizi
    print("\n🎯 Hybrid strateji analizi...")
    result = strategy.analyze(market_data, timeframe)
    
    print(f"\n📈 SONUÇ:")
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Strength: {result['signal_strength']}")
    
    # Gram analiz
    gram = result.get('gram_analysis', {})
    print(f"\nGram Signal: {gram.get('signal')} ({gram.get('confidence', 0):.2%})")
    print(f"Trend: {gram.get('trend')}")
    print(f"RSI: {gram.get('indicators', {}).get('rsi', 'N/A')}")

# Çalıştır
if __name__ == "__main__":
    asyncio.run(force_analysis())