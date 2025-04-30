import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import re
import logging
import time
import config

def extract_access_key_and_user_id(url):
    """Извлекает access_key и user_id из URL Viabtc"""
    if not url:
        return None, None

    access_key = None
    user_id = None

    access_match = re.search(r"access_key=([a-f0-9]+)", url)
    if access_match:
        access_key = access_match.group(1)

    user_match = re.search(r"user_id=(\d+)", url)
    if user_match:
        user_id = user_match.group(1)

    return access_key, user_id

def parse_google_sheets():
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("Начало парсинга Google Sheets")

    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "credentials.json", scope
        )
        client = gspread.authorize(creds)

        spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
        spreadsheet_name = spreadsheet.title
        logger.info(f"Работа с документом: {spreadsheet_name}")

        worksheet_names = config.WORKSHEET_NAMES if isinstance(config.WORKSHEET_NAMES, list) else [config.WORKSHEET_NAMES]
        
        all_records = []
        missing_sheets = []

        for sheet_name in worksheet_names:
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                records = worksheet.get_all_records()
                logger.info(f"Получено {len(records)} записей из листа '{sheet_name}'")
                all_records.extend(records)
            except gspread.WorksheetNotFound:
                error_msg = (
                    f"Лист '{sheet_name}' в документе '{spreadsheet_name}' не найден!\n"
                    f"Проверьте правильность имени листа в '{spreadsheet_name}' "
                    f"и параметр WORKSHEET_NAMES в config.py"
                )
                print(error_msg)
                logger.error(error_msg)
                missing_sheets.append(sheet_name)
                continue

        if not all_records and missing_sheets:
            logger.warning(f"Не найдены листы: {missing_sheets}. Повтор через 3 минуты.")
            time.sleep(180)
            return None

        valid_records = []
        required_fields = ["user_name", "coin", "url", "telegram_target"]

        for record in all_records:
            try:
                if not all(field in record for field in required_fields):
                    logger.warning(f"Пропущена запись с отсутствующими полями: {record}")
                    continue

                access_key, user_id = extract_access_key_and_user_id(record["url"])
                if not access_key:
                    logger.warning(f"Не удалось извлечь access_key из URL: {record['url']}")
                    continue

                record["access_key"] = access_key
                record["user_id"] = user_id

                if "hashrate_threshold" not in record or not record["hashrate_threshold"]:
                    record["hashrate_threshold"] = config.DEFAULT_HASHRATE_THRESHOLD
                else:
                    try:
                        record["hashrate_threshold"] = float(record["hashrate_threshold"])
                    except ValueError:
                        record["hashrate_threshold"] = config.DEFAULT_HASHRATE_THRESHOLD

                record["thread_id"] = int(record.get("thread_id", 0)) if record.get("thread_id") else None

                valid_records.append(record)

            except Exception as e:
                logger.error(f"Ошибка обработки записи: {str(e)}", exc_info=True)
                continue

        logger.info(f"Всего валидных записей: {len(valid_records)}")

        with open(config.JSON_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(valid_records, f, indent=2, ensure_ascii=False)

        logger.info(f"Сохранено {len(valid_records)} записей в {config.JSON_FILE_PATH}")
        return valid_records

    except Exception as e:
        logger.critical(f"Ошибка парсинга Google Sheets: {str(e)}", exc_info=True)
        raise