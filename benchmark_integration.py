#!/usr/bin/env python3
"""
Integration Test Performance Benchmark
Bu script integration testlerinin performance metriklerini ölçer
"""

import time
import sys
import os
from datetime import datetime
from statistics import mean, stdev

# Proje root'unu path'e ekle
sys.path.insert(0, os.path.dirname(__file__))

from strategies.hybrid_strategy import HybridStrategy
from tests.test_helpers import generate_trending_candles
from tests.test_integration import TestHelpers


def benchmark_single_analysis(iterations=10):
    """Tek analiz performance benchmark"""
    strategy = HybridStrategy()
    helpers = TestHelpers()
    
    print(f"🔍 Single Analysis Benchmark ({iterations} iterations)")
    print("-" * 50)
    
    execution_times = []
    
    for i in range(iterations):
        # Test data
        candles = generate_trending_candles(2000, 50, "BULLISH")
        gram_candles = helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = helpers.create_market_data_series()
        
        # Benchmark
        start_time = time.time()
        result = strategy.analyze(gram_candles, market_data, "1h")
        execution_time = time.time() - start_time
        
        execution_times.append(execution_time)
        
        print(f"  Run {i+1:2d}: {execution_time:.3f}s - Signal: {result['signal']} (Conf: {result['confidence']:.2f})")
    
    # İstatistikler
    avg_time = mean(execution_times)
    min_time = min(execution_times)
    max_time = max(execution_times)
    std_time = stdev(execution_times) if len(execution_times) > 1 else 0
    
    print(f"\n📊 Single Analysis Stats:")
    print(f"  Average: {avg_time:.3f}s")
    print(f"  Min:     {min_time:.3f}s") 
    print(f"  Max:     {max_time:.3f}s")
    print(f"  StdDev:  {std_time:.3f}s")
    print(f"  Status:  {'✅ PASS' if avg_time < 2.0 else '❌ SLOW'} (Target: <2.0s)")
    
    return avg_time


def benchmark_multi_timeframe():
    """Multi-timeframe performance benchmark"""
    strategy = HybridStrategy()
    helpers = TestHelpers()
    timeframes = ["15m", "1h", "4h", "1d"]
    
    print(f"\n🕐 Multi-Timeframe Benchmark")
    print("-" * 50)
    
    # Test data
    candles = generate_trending_candles(2000, 100, "BULLISH")
    market_data = helpers.create_market_data_series(count=100)
    
    timeframe_results = {}
    total_start = time.time()
    
    for tf in timeframes:
        gram_candles = helpers.mock_candles_to_gram_candles(candles, tf)
        
        start = time.time()
        result = strategy.analyze(gram_candles, market_data, tf)
        execution_time = time.time() - start
        
        timeframe_results[tf] = {
            'time': execution_time,
            'signal': result['signal'],
            'confidence': result['confidence']
        }
        
        print(f"  {tf:3s}: {execution_time:.3f}s - {result['signal']:4s} (Conf: {result['confidence']:.2f})")
    
    total_time = time.time() - total_start
    
    print(f"\n📊 Multi-Timeframe Stats:")
    print(f"  Total Time: {total_time:.3f}s")
    print(f"  Avg/Frame:  {total_time/len(timeframes):.3f}s")
    print(f"  Status:     {'✅ PASS' if total_time < 8.0 else '❌ SLOW'} (Target: <8.0s)")
    
    return total_time


def benchmark_data_size_scaling():
    """Veri boyutu scaling benchmark"""
    strategy = HybridStrategy()
    helpers = TestHelpers()
    data_sizes = [20, 50, 100, 200, 500]
    
    print(f"\n📈 Data Size Scaling Benchmark")
    print("-" * 50)
    
    scaling_results = {}
    
    for size in data_sizes:
        candles = generate_trending_candles(2000, size, "BULLISH")
        gram_candles = helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = helpers.create_market_data_series(count=min(size, 100))
        
        start = time.time()
        result = strategy.analyze(gram_candles, market_data, "1h")
        execution_time = time.time() - start
        
        scaling_results[size] = execution_time
        
        per_candle_time = execution_time / size * 1000  # milliseconds
        
        print(f"  {size:3d} candles: {execution_time:.3f}s ({per_candle_time:.1f}ms/candle)")
    
    # Scaling efficiency check
    efficiency_20 = scaling_results[20] / 20
    efficiency_500 = scaling_results[500] / 500
    scaling_factor = efficiency_500 / efficiency_20
    
    print(f"\n📊 Scaling Stats:")
    print(f"  20 candles:  {efficiency_20*1000:.1f}ms/candle")
    print(f"  500 candles: {efficiency_500*1000:.1f}ms/candle")
    print(f"  Scaling:     {scaling_factor:.2f}x (Lower is better)")
    print(f"  Status:      {'✅ GOOD' if scaling_factor < 3.0 else '❌ POOR'} scaling")
    
    return scaling_factor


def benchmark_memory_usage():
    """Memory usage benchmark (basit versiyon)"""
    print(f"\n🧠 Memory Usage Benchmark")
    print("-" * 50)
    
    try:
        import psutil
        process = psutil.Process()
        
        # Baseline memory
        baseline = process.memory_info().rss / 1024 / 1024
        
        strategy = HybridStrategy()
        helpers = TestHelpers()
        
        # After initialization
        after_init = process.memory_info().rss / 1024 / 1024
        
        # After analysis
        candles = generate_trending_candles(2000, 200, "BULLISH")
        gram_candles = helpers.mock_candles_to_gram_candles(candles, "1h")
        market_data = helpers.create_market_data_series(count=200)
        
        result = strategy.analyze(gram_candles, market_data, "1h")
        after_analysis = process.memory_info().rss / 1024 / 1024
        
        print(f"  Baseline:      {baseline:.1f} MB")
        print(f"  After Init:    {after_init:.1f} MB (+{after_init-baseline:.1f} MB)")
        print(f"  After Analysis:{after_analysis:.1f} MB (+{after_analysis-after_init:.1f} MB)")
        print(f"  Total Usage:   {after_analysis:.1f} MB")
        print(f"  Status:        {'✅ GOOD' if after_analysis < 200 else '❌ HIGH'} (Target: <200 MB)")
        
        return after_analysis
        
    except ImportError:
        print("  ⚠️  psutil not available - skipping memory benchmark")
        return 0


def main():
    """Ana benchmark runner"""
    print("🚀 Gold Price Analyzer - Integration Performance Benchmark")
    print("=" * 70)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Benchmarks
    single_time = benchmark_single_analysis(5)
    multi_time = benchmark_multi_timeframe()
    scaling_factor = benchmark_data_size_scaling()
    memory_usage = benchmark_memory_usage()
    
    # Overall assessment
    print(f"\n🎯 Overall Performance Assessment")
    print("=" * 50)
    
    score = 0
    max_score = 4
    
    # Single analysis score
    if single_time < 1.0:
        single_score = "A+ (Excellent)"
        score += 1
    elif single_time < 2.0:
        single_score = "A (Good)"
        score += 0.8
    elif single_time < 3.0:
        single_score = "B (Acceptable)"
        score += 0.6
    else:
        single_score = "C (Needs Improvement)"
        score += 0.3
    
    # Multi-timeframe score
    if multi_time < 4.0:
        multi_score = "A+ (Excellent)"
        score += 1
    elif multi_time < 8.0:
        multi_score = "A (Good)"
        score += 0.8
    else:
        multi_score = "B (Needs Improvement)"
        score += 0.6
    
    # Scaling score
    if scaling_factor < 1.5:
        scaling_score = "A+ (Excellent)"
        score += 1
    elif scaling_factor < 3.0:
        scaling_score = "A (Good)"
        score += 0.8
    else:
        scaling_score = "B (Needs Improvement)"
        score += 0.6
    
    # Memory score
    if memory_usage == 0:
        memory_score = "N/A"
        score += 0.7  # Neutral
    elif memory_usage < 100:
        memory_score = "A+ (Excellent)"
        score += 1
    elif memory_usage < 200:
        memory_score = "A (Good)"
        score += 0.8
    else:
        memory_score = "B (High Usage)"
        score += 0.5
    
    print(f"Single Analysis:  {single_score}")
    print(f"Multi-Timeframe:  {multi_score}")
    print(f"Data Scaling:     {scaling_score}")
    print(f"Memory Usage:     {memory_score}")
    print()
    
    final_grade = score / max_score * 100
    if final_grade >= 90:
        grade = "A+ 🏆"
    elif final_grade >= 80:
        grade = "A  ✅"
    elif final_grade >= 70:
        grade = "B  👍"
    elif final_grade >= 60:
        grade = "C  ⚠️"
    else:
        grade = "D  ❌"
    
    print(f"🎖️  Final Grade: {grade} ({final_grade:.1f}%)")
    
    if final_grade >= 80:
        print("✅ System is performance-ready for production!")
    elif final_grade >= 70:
        print("👍 System performance is acceptable with minor optimizations needed.")
    else:
        print("⚠️ System needs performance optimization before production deployment.")


if __name__ == "__main__":
    main()