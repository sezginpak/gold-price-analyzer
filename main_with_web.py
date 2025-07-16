"""
Gold Price Analyzer + Web Dashboard
"""
import asyncio
import uvicorn
from multiprocessing import Process
import signal
import sys
import os

# Ana analyzer'ı import et
from main_robust import RobustGoldPriceAnalyzer
from utils.logger import setup_logger

logger = setup_logger(name="gold_analyzer_web")


def run_analyzer():
    """Analyzer process'i"""
    analyzer = RobustGoldPriceAnalyzer()
    asyncio.run(analyzer.run_with_restart())


def run_web_server():
    """Web server process'i"""
    uvicorn.run(
        "web_server:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False
    )


def main():
    """Ana fonksiyon - iki process'i başlat"""
    logger.info("Starting Gold Price Analyzer with Web Dashboard...")
    
    # Process'leri oluştur
    analyzer_process = Process(target=run_analyzer)
    web_process = Process(target=run_web_server)
    
    # Signal handler
    def signal_handler(signum, frame):
        logger.info("Shutdown signal received")
        analyzer_process.terminate()
        web_process.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Process'leri başlat
        analyzer_process.start()
        web_process.start()
        
        logger.info("="*60)
        logger.info("🏆 GOLD PRICE ANALYZER WITH WEB DASHBOARD")
        logger.info("="*60)
        logger.info("✅ Analyzer başlatıldı")
        logger.info("🌐 Web arayüzü: http://localhost:8080")
        logger.info("="*60)
        
        # Process'lerin bitmesini bekle
        analyzer_process.join()
        web_process.join()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        analyzer_process.terminate()
        web_process.terminate()


if __name__ == "__main__":
    main()