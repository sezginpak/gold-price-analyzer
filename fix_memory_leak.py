#!/usr/bin/env python3
"""
Memory leak analizi ve düzeltmeleri
"""
import sys
sys.path.append('/root/gold-price-analyzer')

import gc
import tracemalloc
import asyncio
from datetime import datetime
import psutil
import os

# Memory tracking başlat
tracemalloc.start()

def check_memory_usage():
    """Current memory usage'ı göster"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Memory Usage:")
    print(f"  RSS: {mem_info.rss / 1024 / 1024:.1f} MB")
    print(f"  VMS: {mem_info.vms / 1024 / 1024:.1f} MB")
    
    # Top memory allocations
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print("\nTop 10 memory allocations:")
    for stat in top_stats[:10]:
        print(f"  {stat}")

async def test_memory_leak():
    """Memory leak testi"""
    from storage.sqlite_storage import SQLiteStorage
    from strategies.hybrid_strategy import HybridStrategy
    from services.harem_altin_service import HaremAltinService
    
    print("=== Memory Leak Test ===")
    
    # Başlangıç memory
    check_memory_usage()
    
    storage = SQLiteStorage()
    strategy = HybridStrategy()
    service = HaremAltinService()
    
    # 5 kez analiz çalıştır ve memory artışını gözlemle
    for i in range(5):
        print(f"\n--- Iteration {i+1} ---")
        
        # Veri toplama simülasyonu
        try:
            data = await service.get_latest_prices()
            if data:
                storage.save_price(data)
        except Exception as e:
            print(f"Data collection error: {e}")
        
        # Analiz simülasyonu
        candles = storage.generate_candles(15, limit=50)
        if len(candles) > 30:
            # Hybrid analiz
            from models.market_data import GramAltinCandle
            gram_candles = []
            for candle in candles:
                gram_candles.append(GramAltinCandle(
                    timestamp=candle.timestamp,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    interval=candle.interval
                ))
            
            # Market data
            market_data = storage.get_latest_prices(100)
            
            # Analiz çalıştır
            result = strategy.analyze(gram_candles, market_data)
            storage.save_hybrid_analysis(result)
            
            print(f"✓ Analysis completed: {result['signal']}")
        
        # Memory durumu
        check_memory_usage()
        
        # Garbage collection
        gc.collect()
        
        # 10 saniye bekle
        await asyncio.sleep(10)
    
    print("\n=== Test Completed ===")
    print("\nMemory leak indicators:")
    print("- Sürekli artan RSS: Memory leak var")
    print("- Sabit RSS: Memory leak yok")
    
    # Final memory snapshot
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('traceback')
    
    print("\nTop memory consuming traceback:")
    for stat in top_stats[:3]:
        print(stat)
        for line in stat.traceback.format():
            print(f"  {line}")

def find_unclosed_resources():
    """Kapatılmamış kaynakları bul"""
    print("\n=== Resource Check ===")
    
    # SQLite connections
    import sqlite3
    import gc
    
    connections = []
    for obj in gc.get_objects():
        if isinstance(obj, sqlite3.Connection):
            connections.append(obj)
    
    print(f"Open SQLite connections: {len(connections)}")
    
    # Close them
    for conn in connections:
        try:
            conn.close()
            print("✓ Closed a connection")
        except:
            pass

if __name__ == "__main__":
    print("Gold Analyzer Memory Leak Analysis\n")
    
    # Resource check
    find_unclosed_resources()
    
    # Memory leak test
    asyncio.run(test_memory_leak())
    
    # Final resource check
    find_unclosed_resources()
    
    tracemalloc.stop()