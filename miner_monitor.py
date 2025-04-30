import requests
import json
import time
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from telegram_bot import compare_workers, generate_status_message, send_telegram_message
import config

class MinerMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Инициализация монитора майнеров")
        
        self.status_file = config.PREVIOUS_STATUS_FILE
        self.hashrate_file = config.HASHRATE_HISTORY_FILE
        self.workers_file = config.WORKERS_CACHE_FILE
        
        self._init_files()
        self.previous_status = self._load_json(self.status_file)
        self.hashrate_data = self._load_json(self.hashrate_file)
        self.workers_cache = self._load_json(self.workers_file)

    def _init_files(self):
        """Создает пустые файлы, если они не существуют"""
        for file_path in [self.status_file, self.hashrate_file, self.workers_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                self.logger.info(f"Создан новый файл: {file_path}")

    def _load_json(self, filename):
        """Загрузка данных из JSON файла"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Ошибка загрузки {filename}: {str(e)}")
            return {}

    def _save_json(self, filename, data):
        """Сохранение данных в JSON файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения {filename}: {str(e)}")

    def _make_api_request(self, url, params, max_retries=3):
        """Универсальный метод для выполнения API запросов"""
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url, 
                    params=params, 
                    timeout=config.API_REQUEST_TIMEOUT
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                delay = min(5, attempt * 2)
                self.logger.warning(
                    f"Ошибка запроса (попытка {attempt+1}/{max_retries}): {str(e)}. "
                    f"Повтор через {delay} сек."
                )
                time.sleep(delay)
        return None

    def get_worker_hashrates(self, access_key, coin, worker_id, user_id=None):
        """Получение данных о хешрейте воркера"""
        url = "https://www.viabtc.com/res/observer/worker/hashrate/chart"
        params = {
            "access_key": access_key,
            "coin": coin,
            "worker_id": worker_id,
            "interval": "hour"
        }
        if user_id:
            params['user_id'] = user_id
            
        data = self._make_api_request(url, params)
        if data and data.get('code') == 0:
            hashrates = data.get('data', {}).get('hashrate', [])
            if hashrates:
                return max(hashrates), hashrates[-1]
        return None, None

    def _fetch_workers_page(self, access_key, coin, limit, offset, user_id=None):
        """Запрос одной страницы со списком воркеров"""
        url = "https://www.viabtc.com/res/observer/worker"
        params = {
            "access_key": access_key,
            "coin": coin,
            "sort_by": "hashrate_10min",
            "sort_order": "desc",
            "limit": limit,
            "offset": offset
        }
        if user_id:
            params['user_id'] = user_id
            
        data = self._make_api_request(url, params)
        if data and data.get('code') == 0:
            return data.get('data', {}).get('data', []), data.get('data', {}).get('total', 0)
        return [], 0

    def _process_worker_batch(self, workers, access_key, coin, user_id, hashrate_threshold):
        """Обработка батча воркеров"""
        results = []
        for i, worker in enumerate(workers):
            if i > 0 and i % 5 == 0:
                time.sleep(1)
            
            worker_data = {
                "id": worker.get('id'),
                "user": worker.get('user'),
                "user_id": user_id,
                "name": worker.get('name'),
                "coin": coin,
                "last_active": worker.get('last_active'),
                "status": worker.get('status'),
                "max_hashrate": 0,
                "last_hashrate": 0,
                "hashrate_threshold": hashrate_threshold
            }
            
            if worker.get('status') == 'active':
                max_hr, last_hr = self.get_worker_hashrates(access_key, coin, worker['id'], user_id)
                if max_hr is not None:
                    worker_data['max_hashrate'] = max_hr
                    worker_data['last_hashrate'] = last_hr if last_hr is not None else 0
            
            results.append(worker_data)
        return results

    def get_workers_list(self, access_key, coin, user_id=None, hashrate_threshold=30.0):
        """Получение списка воркеров"""
        cache_key = f"{access_key}_{coin}_{user_id if user_id else 'main'}"
        
        if cache_key in self.workers_cache:
            cache_time = self.workers_cache[cache_key].get('timestamp', 0)
            if time.time() - cache_time < config.WORKERS_CACHE_TTL:
                self.logger.info(f"Используем кэшированные данные для {cache_key}")
                return self.workers_cache[cache_key]['data']
        
        workers, total = self._fetch_workers_page(access_key, coin, 1, 0, user_id)
        if total == 0:
            self.logger.warning(f"API вернуло 0 воркеров для {cache_key}")
            return []
        
        self.logger.info(f"Всего воркеров для {cache_key}: {total}")
        
        all_workers = []
        offsets = range(0, total, config.WORKERS_PAGE_SIZE)
        
        for offset in offsets:
            time.sleep(config.WORKERS_REQUEST_DELAY)
            workers, _ = self._fetch_workers_page(
                access_key, coin, 
                config.WORKERS_PAGE_SIZE, 
                offset, 
                user_id
            )
            if workers:
                all_workers.extend(workers)
        
        active_workers = [w for w in all_workers if w.get('status') == 'active']
        inactive_workers = [w for w in all_workers if w.get('status') != 'active']
        
        processed_workers = []
        batch_size = 50
        for i in range(0, len(active_workers), batch_size):
            batch = active_workers[i:i+batch_size]
            processed_workers.extend(
                self._process_worker_batch(batch, access_key, coin, user_id, hashrate_threshold)
            )
            time.sleep(1)
        
        for worker in inactive_workers:
            processed_workers.append({
                "id": worker.get('id'),
                "user": worker.get('user'),
                "user_id": user_id,
                "name": worker.get('name'),
                "coin": coin,
                "last_active": worker.get('last_active'),
                "status": worker.get('status'),
                "max_hashrate": 0,
                "last_hashrate": 0,
                "hashrate_threshold": hashrate_threshold
            })
        
        self.workers_cache[cache_key] = {
            'data': processed_workers,
            'timestamp': time.time()
        }
        self._save_json(self.workers_file, self.workers_cache)
        
        self.logger.info(f"Обработано {len(processed_workers)} воркеров для {cache_key}")
        return processed_workers

    def run_monitoring(self, tracking_data):
        """Основной метод мониторинга"""
        if not tracking_data:
            self.logger.warning("Нет данных для отслеживания!")
            return

        new_status = {}
        
        for config_entry in tracking_data:
            try:
                if config_entry.get('отслеживать', '').lower() != 'да':
                    continue
                
                user = config_entry['user_name']
                coin = config_entry['coin']
                access_key = config_entry['access_key']
                user_id = config_entry.get('user_id')
                threshold = float(config_entry['hashrate_threshold'])
                
                self.logger.info(f"Проверка {user} ({coin}), порог: {threshold}%")
                
                workers = self.get_workers_list(access_key, coin, user_id, threshold)
                if not workers:
                    self.logger.warning(f"Нет данных для {user} ({coin})")
                    continue
                
                cache_key = f"{access_key}_{coin}_{user_id if user_id else 'main'}"
                new_status[cache_key] = {
                    'data': workers,
                    'timestamp': time.time()
                }
                
                old_workers = self.previous_status.get(cache_key, {}).get('data', [])
                changes = compare_workers({'data': old_workers}, {'data': workers})
                
                if any(changes.values()):
                    messages = generate_status_message(user, coin, changes, access_key, user_id)
                    thread_id = config_entry.get('thread_id')
                    chat_id = config_entry.get('telegram_target')
                    
                    for msg in messages:
                        send_telegram_message(chat_id, msg, thread_id)
                        self.logger.info(f"Отправлено уведомление для {user}")
                        
            except Exception as e:
                self.logger.error(f"Ошибка обработки {config_entry.get('user_name')}: {str(e)}", exc_info=True)
                continue
        
        self.previous_status = new_status
        self._save_json(self.status_file, new_status)