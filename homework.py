import logging
import os
import sys
import time
import exceptions
from json import JSONDecodeError

import requests
import telegram
from dotenv import load_dotenv
from http import HTTPStatus

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


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка отправки сообщения {error}')
    else:
        logging.info(f'Сообщение {message} отправлено')


def get_api_answer(current_timestamp):
    """Функция делает запрос к API сервиса.
    Возвращает ответ, преобразовывая данные к типам данных Python.
    """
    # timestamp = current_timestamp or int(time.time())
    params = {'from_date': 0}

    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as e:
        logging.error('Ошибка соединения')
        raise exceptions.GeneralErorrs(f'Ошибка соединения {e}') from e
    except JSONDecodeError as e:
        logging.error('Ошибка формата данных')
        raise exceptions.GeneralErorrs(f'Ошибка формата данных {e}') from e
    if homework_statuses.status_code != HTTPStatus.OK:
        logging.error(
            f'Сбой работы. Ответ сервера {homework_statuses.status_code}'
        )
        raise exceptions.GeneralErorrs('Сбой работы сервера')
    return homework_statuses.json()


def check_response(response):
    """Функция проверяет ответ API на корректность."""
    try:
        response['homeworks']
        if type(response) is not dict:
            raise exceptions.CommonErrors('Ответ вернулся не в виде словаря')
        elif 'homeworks' or 'current_date' not in response:
            raise KeyError('Нужных ключей нет в словаре')
    except exceptions.CommonErrors as ex:
        if not isinstance(response['homeworks'], list):
            raise TypeError('Запрос к серверу пришёл не в виде списка') from ex
    return response['homeworks']


def parse_status(homeworks):
    """Функция извлекает информации домашней работе и ее статус."""
    homework_name = homeworks['homework_name']
    if 'homework_name' not in homework_name:
        raise exceptions.CommonErrors(
            'Ключ homework_name не обнаружен в словаре')
    homework_status = homeworks['status']
    if 'status' not in homework_status:
        raise exceptions.CommonErrors('Ключ status не обнвружен в словаре')
    if homework_status not in HOMEWORK_STATUSES:
        raise exceptions.CommonErrors('Статус не обнаружен в списке')
    elif homework_status is None:
        raise exceptions.CommonErrors('Пришел пустой список')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Токены не доступны')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            logging.info(f'Получен список работ {response}')
            if type(homeworks) is list:
                send_message(bot, parse_status(homeworks[0]))
            else:
                logging.debug('Нет новых статусов')
                send_message(bot, 'Нет новых статусов')
                return False
            current_timestamp = response.get('current_date', current_timestamp)

        except exceptions.GeneralErorrs as error:
            logging.error(f'{error}')
            send_message(bot, f'{error}')
        except Exception as error:
            send_message(bot, f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
