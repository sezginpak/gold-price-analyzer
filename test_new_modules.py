#!/usr/bin/env python3
"""
Yeni eklenen modülleri test et
Fibonacci Retracement ve Smart Money Concepts
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from storage.sqlite_storage import SQLiteStorage
from indicators.fibonacci_retracement import calculate_fibonacci_analysis
from indicators.smart_money_concepts import calculate_smc_analysis
from utils.logger import logger
import json


def test_new_modules():
    """Yeni modülleri test et"""
    
    logger.info("=" * 50)
    logger.info("YENİ MODÜL TESTLERİ BAŞLIYOR")
    logger.info("=" * 50)
    
    try:
        # Storage bağlantısı
        storage = SQLiteStorage()
        
        # Gram altın mum verilerini çek (son 100 veri)
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, open, high, low, close
                FROM gram_candles
                WHERE interval = '15m'
                ORDER BY timestamp DESC
                LIMIT 100
            """)
            
            rows = cursor.fetchall()
            candles = rows
        
        if not candles:
            logger.error("Mum verisi bulunamadı!")
            return
        
        # DataFrame'e çevir
        df = pd.DataFrame([{
            'timestamp': c['timestamp'],
            'open': c['open'],
            'high': c['high'],
            'low': c['low'],
            'close': c['close']
        } for c in candles])
        
        logger.info(f"Test verisi: {len(df)} mum")
        logger.info(f"Fiyat aralığı: {df['low'].min():.2f} - {df['high'].max():.2f}")
        logger.info(f"Son fiyat: {df['close'].iloc[-1]:.2f}")
        
        # 1. Fibonacci Retracement Testi
        logger.info("\n" + "=" * 30)
        logger.info("FIBONACCI RETRACEMENT TESTİ")
        logger.info("=" * 30)
        
        fib_result = calculate_fibonacci_analysis(df)
        
        if fib_result['status'] == 'success':
            logger.info(f"✅ Fibonacci analizi başarılı!")
            logger.info(f"Trend: {fib_result['trend']}")
            logger.info(f"Swing High: {fib_result['swing_high']:.2f}")
            logger.info(f"Swing Low: {fib_result['swing_low']:.2f}")
            logger.info(f"Range: {fib_result['range']:.2f}")
            
            if fib_result['nearest_level']:
                logger.info(f"\n📍 En yakın Fibonacci seviyesi:")
                logger.info(f"  Level: {fib_result['nearest_level']['description']}")
                logger.info(f"  Fiyat: {fib_result['nearest_level']['price']:.2f}")
                logger.info(f"  Güç: {fib_result['nearest_level']['strength']}")
            
            logger.info(f"\nBounce Potansiyeli: {fib_result['bounce_potential']:.1f}/100")
            
            if fib_result['signals']['action'] != 'WAIT':
                logger.info(f"\n🎯 Fibonacci Sinyali:")
                logger.info(f"  Aksiyon: {fib_result['signals']['action']}")
                logger.info(f"  Güç: {fib_result['signals']['strength']:.1f}")
                logger.info(f"  Sebep: {', '.join(fib_result['signals']['reason'])}")
                
                if fib_result['signals']['target_levels']:
                    logger.info(f"  Hedefler: {[f'{t:.2f}' for t in fib_result['signals']['target_levels'] if t]}")
                if fib_result['signals']['stop_level']:
                    logger.info(f"  Stop: {fib_result['signals']['stop_level']:.2f}")
        else:
            logger.warning(f"Fibonacci analizi başarısız: {fib_result.get('message', 'Bilinmeyen hata')}")
        
        # 2. Smart Money Concepts Testi
        logger.info("\n" + "=" * 30)
        logger.info("SMART MONEY CONCEPTS TESTİ")
        logger.info("=" * 30)
        
        smc_result = calculate_smc_analysis(df)
        
        if smc_result['status'] == 'success':
            logger.info(f"✅ SMC analizi başarılı!")
            
            # Market Structure
            ms = smc_result['market_structure']
            logger.info(f"\n📊 Market Structure:")
            logger.info(f"  Trend: {ms['trend']}")
            logger.info(f"  Higher Highs: {ms['higher_highs']}, Higher Lows: {ms['higher_lows']}")
            logger.info(f"  Lower Highs: {ms['lower_highs']}, Lower Lows: {ms['lower_lows']}")
            
            if ms['bos_level']:
                logger.info(f"  BOS Level: {ms['bos_level']:.2f}")
            if ms['choch_level']:
                logger.info(f"  CHoCH Level: {ms['choch_level']:.2f}")
            
            # Order Blocks
            if smc_result['order_blocks']:
                logger.info(f"\n📦 Order Blocks ({len(smc_result['order_blocks'])} adet):")
                for ob in smc_result['order_blocks'][:3]:  # İlk 3
                    logger.info(f"  {ob['type'].upper()}: {ob['low']:.2f}-{ob['high']:.2f} (Güç: {ob['strength']:.0f})")
            
            # Fair Value Gaps
            if smc_result['fair_value_gaps']:
                logger.info(f"\n🕳️ Fair Value Gaps ({len(smc_result['fair_value_gaps'])} adet):")
                for fvg in smc_result['fair_value_gaps'][:3]:  # İlk 3
                    logger.info(f"  {fvg['type'].upper()}: {fvg['low']:.2f}-{fvg['high']:.2f} (Boyut: {fvg['size_pct']:.2f}%)")
            
            # Liquidity Zones
            if smc_result['liquidity_zones']:
                logger.info(f"\n💧 Liquidity Zones:")
                for zone in smc_result['liquidity_zones'][:3]:  # İlk 3
                    logger.info(f"  {zone['level']:.2f}: {zone['description']}")
            
            # SMC Sinyalleri
            signals = smc_result['signals']
            if signals['action'] != 'WAIT':
                logger.info(f"\n🎯 SMC Sinyali:")
                logger.info(f"  Aksiyon: {signals['action']}")
                logger.info(f"  Güç: {signals['strength']:.1f}")
                logger.info(f"  Sebepler: {', '.join(signals['reasons'][:3])}")  # İlk 3 sebep
                
                if signals['target']:
                    logger.info(f"  Hedef: {signals['target']:.2f}")
                if signals['stop']:
                    logger.info(f"  Stop: {signals['stop']:.2f}")
                if signals['risk_reward'] > 0:
                    logger.info(f"  Risk/Reward: 1:{signals['risk_reward']:.2f}")
        else:
            logger.warning(f"SMC analizi başarısız: {smc_result.get('message', 'Bilinmeyen hata')}")
        
        logger.info("\n" + "=" * 50)
        logger.info("TESTLER TAMAMLANDI")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Test hatası: {e}", exc_info=True)
    finally:
        pass  # SQLiteStorage'da close metodu yok


if __name__ == "__main__":
    test_new_modules()