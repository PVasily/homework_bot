import logging
from logging.handlers import RotatingFileHandler

import os
import sys
from dotenv import load_dotenv

import time
import requests
import http

import telegram

load_dotenv()

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    filemode='w',
    encoding='UTF-8',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s')

handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    encoding='UTF-8',
    backupCount=5)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


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
    """Отправляем сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError:
        logger.error('Сбой при отправке сообщения')
    logger.info(f'Отправка сообщения: {message}')


def get_api_answer(current_timestamp):
    """Делаем запрос к API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    result = dict()
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == http.HTTPStatus.OK:
        try:
            result = response.json()
            return result
        except Exception as error:
            logger.error(error, exc_info=True)
    elif response.status_code in (500, 599):
        logger.error('Код статуса 500')
        raise requests.exceptions.ConnectionError
    elif response.status_code == http.HTTPStatus.REQUEST_TIMEOUT:
        logger.error('Код статуса 408')
        raise requests.exceptions.ReadTimeout
    else:
        logger.error(f'Сбой в работе программы: Эндпоинт'
                     f'{ENDPOINT} недоступен.'
                     f'Код ответа API: {response.status_code}')
        return result


def check_response(response):
    """ПРоверяем ответ на соответствие типам данных Python."""
    if type(response) != dict:
        logger.error('Тип ответа не словарь')
        raise TypeError('Тип ответа не словарь')
    elif 'homeworks' not in response:
        logger.error('Отсутствует ключ "homeworks"')
        raise KeyError('Отсутствует ключ "homeworks"')
    elif 'current_date' not in response:
        logger.error('Отсутствует ключ "current_date"')
        raise KeyError('Отсутствует ключ "current_date"')
    elif type(response['homeworks']) is not list:
        logger.error('"homeworks" не список')
        raise TypeError('"homeworks" не список')
    return response['homeworks']


def parse_status(homework):
    """На основе данных формируем вердикт о статусе работы."""
    if len(homework) > 0:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return []


def check_tokens():
    """Проверяем наличие всех токенов."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    return False


def main():
    """Основная логика работы бота."""
    HOME_STATUS = dict()
    LAST_ERROR = None
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            check = check_tokens()
            if check:
                api = get_api_answer(current_timestamp - 900)
                homeworks = check_response(api)
                if len(homeworks) > 0:
                    status = homeworks[0]['status']
                    if HOME_STATUS != status:
                        message = parse_status(homeworks[0])
                        send_message(bot, message)
                        HOME_STATUS = status
                    else:
                        logger.info('Нет изменений в статусе работы')
                else:
                    logger.debug('Response is empty')
                time.sleep(RETRY_TIME)
            else:
                logger.CRITICAL('There is not any enviroment variable')
                break

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if LAST_ERROR != error:
                send_message(bot, message)
                LAST_ERROR = error
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
