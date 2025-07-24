"""
Gelişmiş loglama sistemi
"""
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from utils.timezone import now, format_for_display


def setup_logger(
    name: str = "gold_analyzer",
    log_dir: str = "logs",
    level: str = "DEBUG",
    max_bytes: int = 5 * 1024 * 1024,  # 5MB per file
    backup_count: int = 3  # Keep 3 backups
) -> logging.Logger:
    """
    Gelişmiş logger kurulumu
    
    Features:
    - Rotating file handler (otomatik log rotation)
    - Separate error log file
    - Console output
    - Detailed formatting
    """
    
    # Log dizini oluştur
    Path(log_dir).mkdir(exist_ok=True)
    
    # Logger oluştur
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Eğer logger'ın zaten handler'ları varsa, yenilerini ekleme
    if logger.handlers:
        return logger
    
    # Formatter
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 1. Rotating File Handler - Tüm loglar
    all_log_file = os.path.join(log_dir, f"{name}.log")
    file_handler = logging.handlers.RotatingFileHandler(
        all_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # 2. Error File Handler - Sadece hatalar
    error_log_file = os.path.join(log_dir, f"{name}_errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # 3. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # DEBUG seviyesine çekildi
    console_handler.setFormatter(simple_formatter)
    
    # 4. Critical alerts file - Kritik hatalar için ayrı dosya
    critical_log_file = os.path.join(log_dir, f"{name}_critical.log")
    critical_handler = logging.handlers.RotatingFileHandler(
        critical_log_file,
        maxBytes=max_bytes,
        backupCount=2,
        encoding='utf-8'
    )
    critical_handler.setLevel(logging.CRITICAL)
    critical_handler.setFormatter(detailed_formatter)
    
    # Handler'ları ekle
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    logger.addHandler(critical_handler)
    
    return logger


def log_exception(logger: logging.Logger, exc: Exception, context: str = ""):
    """Exception'ları detaylı logla"""
    import traceback
    
    error_details = {
        "context": context,
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "traceback": traceback.format_exc()
    }
    
    logger.error(
        f"Exception in {context}: {type(exc).__name__}: {str(exc)}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )
    
    return error_details


# Global logger instance
main_logger = setup_logger()