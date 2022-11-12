import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='bot.log',
    format='%(asctime)s, %(levelname)s, %(funcName)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

BOT = telegram.Bot(token=TELEGRAM_TOKEN)


class MyException(Exception):
    """Кастомные исключения."""

    pass


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(f'Сообщение {message} отправлено')
    except MyException as error:
        logging.error(f'Ошибка отправки сообщения {error}')
        send_message(BOT, 'Сообщение не удалось отправить')


def get_api_answer(current_timestamp):
    """Функция делает запрос к API сервиса.
    Возвращает ответ, преобразовывая данные к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    homework_statuses = requests.get(
        ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != HTTPStatus.OK:
        logging.error(
            f'Сбой работы. Ответ сервера {homework_statuses.status_code}'
        )
        send_message(
            BOT, f'Сбой работы. Ответ сервера {homework_statuses.status_code}'
        )
        raise MyException('Сбой работы сервера')
    return homework_statuses.json()


def check_response(response):
    """Функция проверяет ответ API на корректность."""
    if not isinstance(response['homeworks'], list):
        logging.error('Запрос к серверу пришёл не в виде списка')
        send_message(
            BOT, 'Запрос к серверу пришёл не в виде списка')
        raise MyException('Запрос к серверу пришёл не в виде списка')
    return response['homeworks']


def parse_status(homework):
    """Функция извлекает информации домашней работе и ее статус."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        logging.error('Статус не обнаружен в списке')
        send_message(
            BOT, 'Статус не обнаружен в списке')
        raise MyException('Статус не обнаружен в списке')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет доступность переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('Токены не доступны')
        return 0

    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            logging.info(f'Получен список работ {response}')
            if len(homework) > 0:
                send_message(BOT, parse_status(homework[0]))
            elif len(homework) == 0:
                logging.debug('Нет новых статусов')
                send_message(BOT, 'Нет новых статусов')
            current_timestamp = response.get('current_date', current_timestamp)
            time.sleep(RETRY_TIME)

        except KeyError as error:
            logging.error(f'{error} Отсутствуют ключи')
            send_message(BOT, f'{error} Отсутствуют ключи')

        except Exception as error:
            send_message(BOT, f'Сбой в работе программы: {error}')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
