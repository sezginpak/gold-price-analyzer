"""
Basit analiz testi
"""
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import random
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from models.price_data import PriceData, PriceCandle
from analyzers.signal_generator import SignalGenerator
from collectors.price_collector import MockPriceCollector

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_test_candles(base_price: float = 79000, num_candles: int = 200) -> list:
    """Test için mum verisi oluştur - gerçekçi destek/direnç seviyeleri ile"""
    candles = []
    current_time = datetime.now() - timedelta(hours=num_candles)
    
    # Sabit destek/direnç seviyeleri
    support_levels = [77000, 78000, 79000]
    resistance_levels = [80000, 81000, 82000]
    
    for i in range(num_candles):
        # Sinüs dalgası ile trend oluştur (daha gerçekçi)
        trend_factor = np.sin(i * 0.1) * 0.02  # %2 genlik
        
        # Mevcut fiyatı belirle
        if i == 0:
            current_price = base_price
        else:
            current_price = float(candles[-1].close)
        
        # Destek/Direnç seviyelerine yaklaşınca tepki ver
        for support in support_levels:
            if abs(current_price - support) / support < 0.01:  # %1 yakınlık
                trend_factor += 0.01  # Yukarı dön
                
        for resistance in resistance_levels:
            if abs(current_price - resistance) / resistance < 0.01:  # %1 yakınlık
                trend_factor -= 0.01  # Aşağı dön
        
        # Fiyat hesaplama
        base_change = current_price * trend_factor
        volatility = random.uniform(-0.002, 0.002) * current_price  # %0.2 volatilite
        
        open_price = current_price + base_change + volatility
        
        # High/Low hesaplama
        intraday_volatility = abs(random.uniform(0, 0.003)) * open_price
        if random.random() > 0.5:
            high = open_price + intraday_volatility
            low = open_price - intraday_volatility * 0.5
        else:
            high = open_price + intraday_volatility * 0.5
            low = open_price - intraday_volatility
            
        close = random.uniform(low, high)
        
        candle = PriceCandle(
            timestamp=current_time,
            open=Decimal(str(open_price)),
            high=Decimal(str(high)),
            low=Decimal(str(low)),
            close=Decimal(str(close)),
            interval="1h"
        )
        
        candles.append(candle)
        current_time += timedelta(hours=1)
        base_price = float(close)
    
    return candles


async def test_signal_generation():
    """Sinyal üretimini test et"""
    logger.info("Starting signal generation test...")
    
    # Test verileri oluştur
    candles = generate_test_candles()
    logger.info(f"Generated {len(candles)} test candles")
    
    # Son fiyat
    last_candle = candles[-1]
    current_price = PriceData(
        ons_usd=Decimal("2050"),
        usd_try=Decimal("38.5"),
        ons_try=last_candle.close
    )
    
    # Sinyal üretici
    signal_generator = SignalGenerator(min_confidence=0.6)
    
    # Farklı fiyat seviyelerinde test
    test_prices = [
        last_candle.close * Decimal("0.98"),  # %2 düşük (destek yakını)
        last_candle.close,  # Mevcut fiyat
        last_candle.close * Decimal("1.02"),  # %2 yüksek (direnç yakını)
    ]
    
    for test_price in test_prices:
        test_price_data = PriceData(
            ons_usd=Decimal("2050"),
            usd_try=Decimal("38.5"),
            ons_try=test_price
        )
        
        signal = signal_generator.generate_signal(test_price_data, candles, "medium")
        
        if signal:
            logger.info(f"\n{'='*50}")
            logger.info(f"Price: {test_price}")
            logger.info(f"Signal: {signal.signal_type.value}")
            logger.info(f"Confidence: {signal.overall_confidence:.2f}")
            logger.info(f"Risk: {signal.risk_level.value}")
            logger.info(f"Target: {signal.target_price}")
            logger.info(f"Stop Loss: {signal.stop_loss}")
            logger.info(f"Reasons: {', '.join(signal.reasons)}")
        else:
            logger.info(f"\nNo signal at price: {test_price}")


async def test_live_collection():
    """Canlı veri toplama testi"""
    logger.info("Starting live collection test...")
    
    # Mock collector
    collector = MockPriceCollector()
    await collector.start()
    
    # Mum verisi için buffer
    price_buffer = []
    candles = []
    candle_interval = 60  # 1 dakika
    last_candle_time = datetime.utcnow()
    
    # Sinyal üretici
    signal_generator = SignalGenerator(min_confidence=0.6)
    
    async def price_callback(price_data: PriceData):
        nonlocal last_candle_time, candles
        
        price_buffer.append(price_data)
        logger.info(f"Price: ONS/TRY={price_data.ons_try}, USD/TRY={price_data.usd_try}")
        
        # Her dakika bir mum oluştur
        current_time = datetime.utcnow()
        if (current_time - last_candle_time).total_seconds() >= candle_interval:
            if price_buffer:
                # Mum oluştur
                prices = [p.ons_try for p in price_buffer]
                candle = PriceCandle(
                    timestamp=last_candle_time,
                    open=price_buffer[0].ons_try,
                    high=max(prices),
                    low=min(prices),
                    close=price_buffer[-1].ons_try,
                    interval="1m"
                )
                candles.append(candle)
                
                # Buffer'ı temizle
                price_buffer.clear()
                last_candle_time = current_time
                
                # Yeterli veri varsa sinyal üret
                if len(candles) >= 50:
                    signal = signal_generator.generate_signal(price_data, candles[-100:], "medium")
                    if signal:
                        logger.warning(f"\n🚨 SIGNAL: {signal.signal_type.value} at {signal.price_level}")
                        logger.warning(f"Confidence: {signal.overall_confidence:.2f}, Risk: {signal.risk_level.value}")
    
    # 5 dakika boyunca topla
    collection_task = asyncio.create_task(collector.collect_prices(price_callback))
    
    await asyncio.sleep(300)  # 5 dakika
    
    collector.is_running = False
    await collection_task
    await collector.stop()
    
    logger.info(f"Collection completed. Generated {len(candles)} candles")


async def main():
    """Ana test fonksiyonu"""
    # Basit sinyal testi
    await test_signal_generation()
    
    # Canlı toplama testi (opsiyonel)
    # await test_live_collection()


if __name__ == "__main__":
    asyncio.run(main())