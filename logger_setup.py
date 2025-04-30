import logging
from logging.handlers import RotatingFileHandler
import config 

def configure_logging():
    """Настройка логгера для всего приложения"""
    logger = logging.getLogger()
    logger.setLevel(config.LOG_LEVEL)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Удаляем существующие обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Файловый обработчик с ротацией
    fh = RotatingFileHandler(
        'miner_monitor.log',
        maxBytes=config.LOG_FILE_MAX_SIZE,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    fh.setLevel(config.LOG_LEVEL)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Консольный обработчик
    ch = logging.StreamHandler()
    ch.setLevel(config.LOG_LEVEL)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger