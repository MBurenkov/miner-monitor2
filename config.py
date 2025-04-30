# Настройки системы
TELEGRAM_BOT_TOKEN = "7631711323:AAFAQ4utK5B7YMBWyT8BcrfPms1kTEO9NZQ"
JSON_FILE_PATH = "tracking_data.json"
GOOGLE_SHEET_ID = "1HVRVMwYPiKTKE68Nhj0mNwRiaQzB9j7PsgnOcBnV-x8"
SPREADSHEET_ID = "1HVRVMwYPiKTKE68Nhj0mNwRiaQzB9j7PsgnOcBnV-x8"
CHECK_INTERVAL = 300  # Интервал проверки в секундах (5 минут)

# Пути к файлам
JSON_FILE_PATH = "tracking_data.json"
PREVIOUS_STATUS_FILE = "previous_status.json"
HASHRATE_HISTORY_FILE = "hashrate_history.json"
WORKERS_CACHE_FILE = "workers_cache.json"

# Настройки Google Sheets
SPREADSHEET_NAME = "Mining Monitor"
WORKSHEET_NAMES = ["оповещения_1"]  # Может быть как список, так и одна строка вид списка страниц ["оповещения", "оповещения_2"]

# Параметры мониторинга
#DEFAULT_HASHRATE_THRESHOLD = 30  # 30% по умолчанию для не указаных % порога в гугл шитс
WORKERS_REQUEST_LIMIT = 500  # Лимит запроса воркеров за один раз
WORKERS_REQUEST_DELAY = 1  # Задержка между запросами воркеров в секундах

# Настройки Telegram
TELEGRAM_SEND_INTERVAL = 3  # Интервал между отправками сообщений в секундах
TELEGRAM_MESSAGE_CHUNK_SIZE = 20  # Количество воркеров в одном сообщении

# Настройки логирования
LOG_LEVEL = "INFO"  # Можно менять на INFO в production (и DEBUG для отладки )
LOG_FILE_MAX_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

# Настройки параллельных запросов
MAX_API_THREADS = 10  # Максимальное количество параллельных запросов к API списка воркеров (3)
MAX_HASHRATE_THREADS = 20  # Максимальное количество параллельных запросов хешрейтов (10)
WORKERS_PAGE_SIZE = 200  # Количество воркеров на одной странице (100)
API_REQUEST_TIMEOUT = 60  # Таймаут запроса в секундах
API_RETRY_DELAY = 2  # Задержка между повторными попытками в секундах
API_MAX_RETRIES = 3  # Максимальное количество попыток запроса
WORKERS_CACHE_TTL = 600  # Время жизни кэша воркеров в секундах (5 минут)