import time
import sys
from logger_setup import configure_logging
import google_sheets_parser
import miner_monitor
import config
from telegram_bot import send_telegram_message

class MonitorState:
    _instance = None
    cycle_count = 0
    first_run = True
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MonitorState, cls).__new__(cls)
        return cls._instance

def main():
    # Настройка логгера
    logger = configure_logging()
    logger.info("=" * 80)
    logger.info("Запуск системы мониторинга майнеров")
    
    state = MonitorState()
    
    try:
        monitor = miner_monitor.MinerMonitor()
        
        while True:
            try:
                state.cycle_count += 1
                logger.info("-" * 80)
                logger.info(f"Начало нового цикла мониторинга ({state.cycle_count} цикл)")
                
                # Получение данных из Google Sheets
                logger.info("Обновление данных из Google Sheets...")
                tracking_data = None
                
                while tracking_data is None:
                    tracking_data = google_sheets_parser.parse_google_sheets()
                    if tracking_data is None:
                        logger.warning("Не удалось получить данные. Повтор через 3 минуты...")
                        time.sleep(180)
                        continue
                
                if tracking_data:
                    logger.info(f"Получено {len(tracking_data)} записей")
                    valid_records = [r for r in tracking_data if r.get('отслеживать', '').lower() == 'да']
                    
                    if not valid_records:
                        logger.warning("Нет записей с 'отслеживать=да'")
                    else:
                        logger.info(f"Найдено {len(valid_records)} активных записей")
                        monitor.run_monitoring(valid_records)
                        
                        # Отправка уведомления о запуске
                        if state.first_run:
                            for record in valid_records:
                                if record.get('telegram_target'):
                                    msg = "🚥 Система мониторинга майнеров включена 🚥"
                                    send_telegram_message(
                                        record['telegram_target'],
                                        msg,
                                        record.get('thread_id')
                                    )
                                    logger.info(f"Уведомление о запуске отправлено в {record['telegram_target']}")
                            state.first_run = False
                
                logger.info(f"Ожидание {config.CHECK_INTERVAL} сек. до следующей проверки...")
                time.sleep(config.CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("\nЗавершение работы...")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Ошибка: {str(e)}", exc_info=True)
                time.sleep(60)
                
    except KeyboardInterrupt:
        logger.info("\nРабота завершена")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()