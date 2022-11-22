import logging
import os
import sys
import time
from http import HTTPStatus
from json import JSONDecodeError

import requests
import telegram
from dotenv import load_dotenv

import exceptions

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

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
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
        logging.debug(f'Сообщение {message} отправлено')


def get_api_answer(timestamp):
    """Функция делает запрос к API сервиса.
    Возвращает ответ, преобразовывая данные к типам данных Python.
    """
    params = {'from_date': timestamp}

    try:
        homework_statuses = requests.get(
            url=ENDPOINT, headers=HEADERS, params=params)
        if homework_statuses.status_code != HTTPStatus.OK:
            raise exceptions.GeneralErorrs('Сбой работы сервера')
        return homework_statuses.json()
    except JSONDecodeError as e:
        raise exceptions.GeneralErorrs(f'Ошибка формата данных {e}') from e
    except requests.exceptions.RequestException as e:
        raise exceptions.GeneralErorrs(f'Ошибка соединения {e}') from e


def check_response(response):
    """Функция проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ответ вернулся не в виде словаря')
    if 'homeworks' not in response:
        raise exceptions.CommonErrors('Ключа homeworks нет в словаре')
    if 'current_date' not in response:
        raise exceptions.CommonErrors('Ключа current_date нет в словаре')
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'Запрос к серверу пришёл не в виде списка')
    return response['homeworks']


def parse_status(homeworks):
    """Функция извлекает информации домашней работе и ее статус."""
    if 'homework_name' not in homeworks:
        raise exceptions.CommonErrors(
            'Ключ homework_name не обнаружен в словаре')
    homework_name = homeworks['homework_name']
    if 'status' not in homeworks:
        raise exceptions.CommonErrors('Ключ status не обнаружен в словаре')
    homework_status = homeworks.get('status')
    if homework_status is None:
        raise exceptions.CommonErrors('Пришел пустой список')
    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.CommonErrors('Статус не обнаружен в списке')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Токены не доступны')
        sys.exit('Ничего не работает, токены не доступны')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            logging.info(f'Получен список работ {response}')
            if homeworks:
                send_message(bot, parse_status(homeworks[0]))
            else:
                logging.debug('Нет новых статусов')
                send_message(bot, 'Нет новых статусов')
            timestamp = response.get('current_date')

        except exceptions.GeneralErorrs as error:
            logging.error(f'{error}')
            send_message(bot, f'{error}')
        except Exception as error:
            logging.error(f'{error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
