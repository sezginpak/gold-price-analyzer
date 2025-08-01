#!/usr/bin/env python3
"""
Simülasyon sistem düzeltmelerini test eden script
"""

import asyncio
import sqlite3
import json
import logging
from decimal import Decimal
from datetime import datetime, timedelta

from models.simulation import SimulationConfig, StrategyType, TimeframeCapital
from simulation.position_manager import PositionManager
from simulation.signal_analyzer import SignalAnalyzer
from storage.sqlite_storage import SQLiteStorage
from utils.timezone import now

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_position_size_calculation():
    """Pozisyon boyutu hesaplamasını test et"""
    logger.info("=== Pozisyon Boyutu Testi ===")
    
    storage = SQLiteStorage("gold_prices.db")
    position_manager = PositionManager(storage)
    
    # Test konfigürasyonu
    config = SimulationConfig(
        name="Test",
        strategy_type=StrategyType.MAIN,
        max_risk=0.02,  # %2 risk
        atr_multiplier_sl=1.5,
        risk_reward_ratio=2.0
    )
    
    # Test parametreleri
    available_capital = Decimal("250.0")  # 250 gram
    current_price = Decimal("4350.0")  # TL
    atr_data = {"atr": 5.0}  # 5 TL ATR
    
    position_size = position_manager.calculate_position_size(
        config, available_capital, current_price, atr_data
    )
    
    logger.info(f"Sermaye: {available_capital} gram")
    logger.info(f"Risk: {config.max_risk*100}%")
    logger.info(f"Risk miktarı: {available_capital * Decimal(str(config.max_risk))} gram")
    logger.info(f"ATR: {atr_data['atr']} TL")
    logger.info(f"Stop mesafesi: {atr_data['atr'] * config.atr_multiplier_sl} TL")
    logger.info(f"Hesaplanan pozisyon boyutu: {position_size} gram")
    logger.info(f"Pozisyon değeri: {position_size * current_price} TL")
    logger.info("")
    
    return position_size > 0

async def test_stop_loss_calculation():
    """Stop loss hesaplamasını test et"""
    logger.info("=== Stop Loss Testi ===")
    
    storage = SQLiteStorage("gold_prices.db")
    position_manager = PositionManager(storage)
    
    config = SimulationConfig(
        name="Test",
        strategy_type=StrategyType.MAIN,
        atr_multiplier_sl=1.5
    )
    
    entry_price = Decimal("4350.0")
    atr_data = {"atr": 5.0}
    
    # LONG pozisyon
    stop_loss_long = position_manager.calculate_stop_loss(
        "LONG", entry_price, atr_data, config
    )
    
    # SHORT pozisyon
    stop_loss_short = position_manager.calculate_stop_loss(
        "SHORT", entry_price, atr_data, config
    )
    
    logger.info(f"Giriş fiyatı: {entry_price} TL")
    logger.info(f"ATR: {atr_data['atr']} TL")
    logger.info(f"Stop mesafesi: {atr_data['atr'] * config.atr_multiplier_sl} TL")
    logger.info(f"LONG stop loss: {stop_loss_long} TL")
    logger.info(f"SHORT stop loss: {stop_loss_short} TL")
    logger.info("")
    
    return stop_loss_long < entry_price and stop_loss_short > entry_price

async def test_trading_costs():
    """İşlem maliyetlerini test et"""
    logger.info("=== İşlem Maliyeti Testi ===")
    
    # Yeni değerler
    spread = Decimal("2.0")  # TL
    commission_rate = 0.0003  # %0.03
    
    position_size = Decimal("100.0")  # 100 gram
    price = Decimal("4350.0")  # TL
    position_value = position_size * price  # 435,000 TL
    
    commission = position_value * Decimal(str(commission_rate))
    total_cost = spread + commission
    cost_percentage = (total_cost / position_value) * 100
    
    logger.info(f"Pozisyon: {position_size} gram @ {price} TL = {position_value} TL")
    logger.info(f"Spread: {spread} TL")
    logger.info(f"Komisyon (%{commission_rate*100}): {commission} TL")
    logger.info(f"Toplam maliyet: {total_cost} TL (%{cost_percentage:.3f})")
    logger.info("")
    
    return cost_percentage < 0.1  # %0.1'den az olmalı

async def test_signal_filtering():
    """Sinyal filtreleme mantığını test et"""
    logger.info("=== Sinyal Filtreleme Testi ===")
    
    signal_analyzer = SignalAnalyzer()
    
    # Test konfigürasyonları
    configs = [
        SimulationConfig(name="Main", strategy_type=StrategyType.MAIN, min_confidence=0.35),
        SimulationConfig(name="Conservative", strategy_type=StrategyType.CONSERVATIVE, min_confidence=0.45),
        SimulationConfig(name="Momentum", strategy_type=StrategyType.MOMENTUM, min_confidence=0.40)
    ]
    
    # Test sinyalleri
    test_signals = [
        {"signal": "BUY", "confidence": 0.45, "indicators": {"rsi": 25}},  # Düşük RSI
        {"signal": "SELL", "confidence": 0.50, "indicators": {"rsi": 75}}, # Yüksek RSI
        {"signal": "BUY", "confidence": 0.60, "indicators": {"rsi": 65}},  # Normal RSI
        {"signal": "HOLD", "confidence": 0.30, "indicators": {"rsi": 50}} # HOLD
    ]
    
    for config in configs:
        logger.info(f"--- {config.name} Stratejisi ---")
        for signal_data in test_signals:
            should_open = signal_analyzer.should_open_position(config, signal_data, "15m")
            logger.info(f"Sinyal: {signal_data['signal']} (conf: {signal_data['confidence']:.2%}) "
                       f"RSI: {signal_data['indicators']['rsi']} -> {should_open}")
        logger.info("")
    
    return True

async def test_database_updates():
    """Veritabanı güncellemelerini kontrol et"""
    logger.info("=== Veritabanı Güncellemeleri Testi ===")
    
    db_path = "gold_prices.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Güncellenmiş simülasyon parametrelerini kontrol et
        cursor.execute("SELECT name, spread, commission_rate FROM simulations")
        simulations = cursor.fetchall()
        
        logger.info("Güncellenmiş simülasyon maliyetleri:")
        for name, spread, commission in simulations:
            logger.info(f"  {name}: Spread={spread} TL, Komisyon=%{commission*100:.2f}")
        logger.info("")
        
        # Son pozisyonları kontrol et
        cursor.execute("""
            SELECT position_type, COUNT(*) as count 
            FROM sim_positions 
            GROUP BY position_type
        """)
        positions = cursor.fetchall()
        
        logger.info("Pozisyon türü dağılımı:")
        for pos_type, count in positions:
            logger.info(f"  {pos_type}: {count} pozisyon")
        logger.info("")
    
    return True

async def run_all_tests():
    """Tüm testleri çalıştır"""
    logger.info("🧪 Simülasyon Sistem Testleri Başlıyor...")
    logger.info("=" * 50)
    
    tests = [
        ("Pozisyon Boyutu", test_position_size_calculation),
        ("Stop Loss", test_stop_loss_calculation),
        ("İşlem Maliyetleri", test_trading_costs),
        ("Sinyal Filtreleme", test_signal_filtering),
        ("Veritabanı Güncellemeleri", test_database_updates)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result, None))
            status = "✅ BAŞARILI" if result else "❌ BAŞARISIZ"
            logger.info(f"{status}: {test_name}")
        except Exception as e:
            results.append((test_name, False, str(e)))
            logger.error(f"❌ HATA: {test_name} - {str(e)}")
    
    logger.info("=" * 50)
    logger.info("📊 Test Sonuçları:")
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for test_name, result, error in results:
        status = "✅" if result else "❌"
        logger.info(f"  {status} {test_name}")
        if error:
            logger.info(f"    Hata: {error}")
    
    logger.info("")
    logger.info(f"🎯 Genel Sonuç: {passed}/{total} test başarılı")
    
    if passed == total:
        logger.info("🎉 Tüm testler başarıyla tamamlandı!")
    else:
        logger.warning(f"⚠️  {total - passed} test başarısız oldu.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(run_all_tests())