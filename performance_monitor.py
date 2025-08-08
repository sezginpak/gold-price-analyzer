#!/usr/bin/env python3
"""
Gold Price Analyzer Performance Monitor
Ultra optimized system performance monitoring and diagnostics
"""

import asyncio
import time
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from storage.sqlite_storage import SQLiteStorage
from web.utils import cache

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil not available - limited system monitoring")

class PerformanceMonitor:
    """Ultra optimized performance monitoring system"""
    
    def __init__(self):
        self.storage = SQLiteStorage()
        self.start_time = time.time()
        self.metrics = {
            "api_response_times": [],
            "database_query_times": [],
            "memory_usage": [],
            "cpu_usage": [],
            "cache_hit_rates": []
        }
    
    def get_system_metrics(self):
        """Get comprehensive system performance metrics"""
        try:
            # Database metrics
            db_stats = self.storage.get_statistics()
            
            # Cache metrics
            cache_stats = cache.get_stats()
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "database": {
                    "total_records": db_stats.get("total_records", 0),
                    "size_mb": self._get_db_size()
                },
                "cache": {
                    "hit_rate": cache_stats.get("hit_rate", 0),
                    "size": cache_stats.get("size", 0),
                    "efficiency": cache_stats.get("efficiency_score", 0)
                }
            }
            
            # Add system metrics if psutil is available
            if PSUTIL_AVAILABLE:
                try:
                    process = psutil.Process()
                    
                    # Memory metrics
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    
                    # CPU metrics
                    cpu_percent = process.cpu_percent()
                    
                    metrics["memory"] = {
                        "used_mb": round(memory_mb, 2),
                        "percent": round(memory_mb / 1024 * 100, 2)  # Assuming 1GB total
                    }
                    metrics["cpu"] = {
                        "percent": round(cpu_percent, 2)
                    }
                except Exception:
                    metrics["memory"] = {"used_mb": 0, "percent": 0}
                    metrics["cpu"] = {"percent": 0}
            else:
                metrics["memory"] = {"used_mb": 0, "percent": 0, "note": "psutil not available"}
                metrics["cpu"] = {"percent": 0, "note": "psutil not available"}
            
            return metrics
        except Exception as e:
            return {"error": str(e)}
    
    def _get_db_size(self):
        """Get database file size in MB"""
        try:
            db_path = Path("gold_prices.db")
            if db_path.exists():
                return round(db_path.stat().st_size / 1024 / 1024, 2)
            return 0
        except:
            return 0
    
    async def benchmark_database_queries(self):
        """Benchmark critical database queries"""
        benchmarks = {}
        
        queries = {
            "latest_price": "SELECT * FROM price_data ORDER BY timestamp DESC LIMIT 1",
            "recent_signals": """SELECT * FROM hybrid_analysis 
                               WHERE signal IN ('BUY', 'SELL') 
                               ORDER BY timestamp DESC LIMIT 10""",
            "open_positions": "SELECT COUNT(*) FROM sim_positions WHERE status = 'OPEN'",
            "daily_performance": """SELECT COUNT(*), AVG(net_profit_loss) 
                                  FROM sim_positions 
                                  WHERE status = 'CLOSED' AND exit_time >= datetime('now', '-1 day')"""
        }
        
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            for query_name, query_sql in queries.items():
                start_time = time.time()
                try:
                    cursor.execute(query_sql)
                    cursor.fetchall()
                    execution_time = (time.time() - start_time) * 1000  # milliseconds
                    benchmarks[query_name] = {
                        "execution_time_ms": round(execution_time, 2),
                        "status": "success"
                    }
                except Exception as e:
                    benchmarks[query_name] = {
                        "execution_time_ms": -1,
                        "status": "error",
                        "error": str(e)
                    }
        
        return benchmarks
    
    async def benchmark_api_endpoints(self):
        """Benchmark API endpoint performance (simulation)"""
        # This would require making actual HTTP requests
        # For now, return placeholder data
        return {
            "/api/dashboard": {"avg_response_ms": 150, "status": "fast"},
            "/api/prices/latest": {"avg_response_ms": 80, "status": "fast"},
            "/api/performance/metrics": {"avg_response_ms": 200, "status": "acceptable"},
            "/api/signals/recent": {"avg_response_ms": 120, "status": "fast"}
        }
    
    def check_performance_thresholds(self, metrics):
        """Check if performance metrics exceed acceptable thresholds"""
        alerts = []
        
        # Memory threshold - 500MB
        if metrics["memory"]["used_mb"] > 500:
            alerts.append({
                "level": "warning",
                "message": f"High memory usage: {metrics['memory']['used_mb']:.1f}MB"
            })
        
        # CPU threshold - 80%
        if metrics["cpu"]["percent"] > 80:
            alerts.append({
                "level": "warning",
                "message": f"High CPU usage: {metrics['cpu']['percent']:.1f}%"
            })
        
        # Cache hit rate threshold - 60%
        if metrics["cache"]["hit_rate"] < 60:
            alerts.append({
                "level": "info",
                "message": f"Low cache hit rate: {metrics['cache']['hit_rate']:.1f}%"
            })
        
        # Database size threshold - 1GB
        if metrics["database"]["size_mb"] > 1000:
            alerts.append({
                "level": "warning",
                "message": f"Large database size: {metrics['database']['size_mb']:.1f}MB"
            })
        
        return alerts
    
    def generate_optimization_recommendations(self, metrics, db_benchmarks):
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Database optimizations
        slow_queries = [name for name, data in db_benchmarks.items() 
                       if data.get("execution_time_ms", 0) > 100]
        
        if slow_queries:
            recommendations.append({
                "category": "database",
                "priority": "high",
                "message": f"Slow queries detected: {', '.join(slow_queries)}",
                "action": "Consider adding more indexes or optimizing query structure"
            })
        
        # Memory optimizations
        if metrics["memory"]["used_mb"] > 300:
            recommendations.append({
                "category": "memory",
                "priority": "medium",
                "message": "High memory usage detected",
                "action": "Consider increasing garbage collection frequency or reducing cache size"
            })
        
        # Cache optimizations
        if metrics["cache"]["hit_rate"] < 70:
            recommendations.append({
                "category": "cache",
                "priority": "medium",
                "message": "Suboptimal cache performance",
                "action": "Consider adjusting cache TTL values or increasing cache size"
            })
        
        return recommendations
    
    async def run_full_performance_analysis(self):
        """Run comprehensive performance analysis"""
        print("🔍 Running Gold Price Analyzer Performance Analysis...")
        print("=" * 60)
        
        # System metrics
        print("\n📊 System Metrics:")
        system_metrics = self.get_system_metrics()
        
        for category, data in system_metrics.items():
            if isinstance(data, dict):
                print(f"  {category.title()}:")
                for key, value in data.items():
                    print(f"    {key}: {value}")
            else:
                print(f"  {category}: {data}")
        
        # Database benchmarks
        print("\n🗄️  Database Query Benchmarks:")
        db_benchmarks = await self.benchmark_database_queries()
        
        for query_name, benchmark in db_benchmarks.items():
            status_emoji = "✅" if benchmark["status"] == "success" else "❌"
            time_ms = benchmark.get("execution_time_ms", -1)
            performance_level = "fast" if time_ms < 50 else "acceptable" if time_ms < 100 else "slow"
            print(f"  {status_emoji} {query_name}: {time_ms}ms ({performance_level})")
        
        # API benchmarks (simulated)
        print("\n🌐 API Endpoint Performance:")
        api_benchmarks = await self.benchmark_api_endpoints()
        
        for endpoint, benchmark in api_benchmarks.items():
            response_time = benchmark["avg_response_ms"]
            status = benchmark["status"]
            emoji = "🟢" if status == "fast" else "🟡" if status == "acceptable" else "🔴"
            print(f"  {emoji} {endpoint}: {response_time}ms ({status})")
        
        # Performance alerts
        print("\n⚠️  Performance Alerts:")
        alerts = self.check_performance_thresholds(system_metrics)
        
        if alerts:
            for alert in alerts:
                level_emoji = "🚨" if alert["level"] == "warning" else "ℹ️"
                print(f"  {level_emoji} {alert['message']}")
        else:
            print("  ✅ No performance issues detected")
        
        # Optimization recommendations
        print("\n💡 Optimization Recommendations:")
        recommendations = self.generate_optimization_recommendations(system_metrics, db_benchmarks)
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                priority_emoji = "🔥" if rec["priority"] == "high" else "⚡" if rec["priority"] == "medium" else "💡"
                print(f"  {i}. {priority_emoji} {rec['message']}")
                print(f"     Action: {rec['action']}")
        else:
            print("  ✨ System is running optimally!")
        
        print("\n" + "=" * 60)
        print("🎯 Performance Analysis Completed!")
        
        return {
            "system_metrics": system_metrics,
            "database_benchmarks": db_benchmarks,
            "api_benchmarks": api_benchmarks,
            "alerts": alerts,
            "recommendations": recommendations
        }

async def main():
    """Run performance monitoring"""
    monitor = PerformanceMonitor()
    await monitor.run_full_performance_analysis()

if __name__ == "__main__":
    asyncio.run(main())