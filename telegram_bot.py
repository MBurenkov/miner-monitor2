import telebot
import config
import json
from urllib.parse import quote
import logging
import time
from queue import Queue
import threading

bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)
logger = logging.getLogger(__name__)

# Очередь для отправки сообщений
message_queue = Queue()
SENDING_INTERVAL = config.TELEGRAM_SEND_INTERVAL

def load_json_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Ошибка загрузки файла {filename}: {e}")
        return None

def compare_workers(old_data, new_data):
    status_changes = {"to_active": [], "to_inactive": [], "hashrate_drop": []}

    if not old_data or not new_data:
        return status_changes

    old_workers = {worker["id"]: worker for worker in old_data.get("data", [])}
    new_workers = {worker["id"]: worker for worker in new_data.get("data", [])}

    for worker_id, new_worker in new_workers.items():
        old_worker = old_workers.get(worker_id)
        if not old_worker:
            continue

        if old_worker["status"] != new_worker["status"]:
            if new_worker["status"] == "active":
                status_changes["to_active"].append(new_worker)
            elif (
                new_worker["status"] in ["unactive", "invalid"]
                and old_worker["status"] == "active"
            ):
                status_changes["to_inactive"].append(new_worker)

        if (
            new_worker["status"] == "active"
            and old_worker["status"] == "active"
            and old_worker.get("max_hashrate", 0) > 0
            and new_worker.get("last_hashrate", 0) > 0
        ):
            threshold = old_worker["max_hashrate"] * (
                old_worker["hashrate_threshold"] / 100
            )
            if new_worker["last_hashrate"] < threshold:
                status_changes["hashrate_drop"].append(new_worker)

    return status_changes

def generate_status_message(user_name, coin, changes, access_key, user_id=None):
    messages = []
    base_url = "https://www.viabtc.com/res/observer/worker/hashrate/chart"

    def make_worker_link(worker):
        params = {
            "coin": coin,
            "worker_id": worker["id"],
            "interval": "min",
            "access_key": access_key,
        }
        if worker.get("user_id"):
            params["user_id"] = worker["user_id"]

        url = base_url + "?" + "&".join(f"{k}={v}" for k, v in params.items())
        return f'<a href="{url}">{worker["name"]}</a>'

    def chunk_list(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    if changes["to_active"]:
        for chunk in chunk_list(changes["to_active"], config.TELEGRAM_MESSAGE_CHUNK_SIZE):
            worker_links = [make_worker_link(w) for w in chunk]
            messages.append(
                f"🟢 {user_name} ({coin})\nВключен:\n" + "\n".join(worker_links)
            )

    if changes["to_inactive"]:
        for chunk in chunk_list(changes["to_inactive"], config.TELEGRAM_MESSAGE_CHUNK_SIZE):
            worker_links = [make_worker_link(w) for w in chunk]
            messages.append(
                f"🔴 {user_name} ({coin})\nВыключен:\n" + "\n".join(worker_links)
            )

    if changes["hashrate_drop"]:
        for chunk in chunk_list(changes["hashrate_drop"], config.TELEGRAM_MESSAGE_CHUNK_SIZE):
            worker_links = [make_worker_link(w) for w in chunk]
            messages.append(
                f"⚠️ {user_name} ({coin})\nХешрейт упал:\n" + "\n".join(worker_links)
            )

    return messages

def send_telegram_message(chat_id, message, thread_id=None):
    """Добавляет сообщение в очередь для отправки"""
    message_queue.put((chat_id, message, thread_id))

def message_sender():
    """Отправляет сообщения из очереди с интервалом"""
    while True:
        if not message_queue.empty():
            chat_id, message, thread_id = message_queue.get()
            try:
                if thread_id:
                    bot.send_message(
                        chat_id, 
                        message, 
                        parse_mode="HTML", 
                        message_thread_id=thread_id
                    )
                else:
                    bot.send_message(chat_id, message, parse_mode="HTML")
                logger.info(f"Сообщение отправлено в чат {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки в Telegram: {str(e)}")
            message_queue.task_done()
        time.sleep(SENDING_INTERVAL)

# Запускаем поток для отправки сообщений
sender_thread = threading.Thread(target=message_sender)
sender_thread.daemon = True
sender_thread.start()

if __name__ == "__main__":
    from logger_setup import configure_logging

    configure_logging()
    logger.info("Запуск Telegram бота")
    bot.infinity_polling()