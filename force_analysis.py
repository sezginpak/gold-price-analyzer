#!/usr/bin/env python3
"""Zorla analiz tetikle"""
import asyncio
from main import HybridGoldAnalyzer

async def force_analysis():
    analyzer = HybridGoldAnalyzer()
    await analyzer.storage.__aenter__()
    
    # Tüm timeframe'ler için analiz yap
    for timeframe in ["15m", "1h"]:
        print(f"\n{timeframe} analizi yapılıyor...")
        await analyzer.run_hybrid_analysis(timeframe)
        print(f"{timeframe} analizi tamamlandı")
    
    await analyzer.storage.__aexit__(None, None, None)

if __name__ == "__main__":
    asyncio.run(force_analysis())