import sys
import time
import http
import logging
from logging.handlers import RotatingFileHandler

import telegram
import requests

from constants import (
    ENDPOINT,
    PRACTICUM_TOKEN,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    RETRY_TIME,
    HEADERS,
    HOMEWORK_STATUSES)
from exceptions import EmptyResponse, UnreachableTelegram, UnknownStatus


def get_logger():
    """Конфигурация логгера."""
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        filemode='w',
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
    return logger


logger = get_logger()


def send_message(bot, message):
    """Отправляем сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError:
        logger.error('Сбой при отправке сообщения')
        raise UnreachableTelegram('В данный момент Telegram недоступен')
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
    elif response.status_code in (
            http.HTTPStatus.INTERNAL_SERVER_ERROR,
            http.HTTPStatus.NETWORK_AUTHENTICATION_REQUIRED):
        logger.error('Код статуса в диапазоне 500')
        raise requests.exceptions.ConnectionError
    elif response.status_code == http.HTTPStatus.REQUEST_TIMEOUT:
        logger.error('Код статуса 408')
        raise requests.exceptions.ReadTimeout
    logger.error(f'Сбой в работе программы: Эндпоинт'
                 f'{ENDPOINT} недоступен.'
                 f'Код ответа API: {response.status_code}')


def check_response(response):
    """Проверяем ответ на соответствие типам данных Python."""
    if not isinstance(response, dict):
        logger.error('Тип ответа не словарь')
        raise TypeError('Тип ответа не словарь')
    elif 'homeworks' not in response or 'current_date' not in response:
        logger.error('Отсутствуют ключи "homeworks" или "current_date')
        raise EmptyResponse(response)
    elif type(response['homeworks']) is not list:
        logger.error('"homeworks" не список')
        raise TypeError('"homeworks" не список')
    return response['homeworks']


def parse_status(homework):
    """На основе данных формируем вердикт о статусе работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if HOMEWORK_STATUSES[homework_status] is not None:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise UnknownStatus('Неизвестный статус')


def check_tokens():
    """Проверяем наличие всех токенов."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    return False


def main():
    """Основная логика работы бота."""
    HOME_STATUS = dict()
    LAST_ERROR = None
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    send_message('Бот активирован.')
    while True:
        try:
            check = check_tokens()
            if check:
                api = get_api_answer(current_timestamp)
                current_timestamp = api['current_date']
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
            else:
                logger.CRITICAL('There is not any enviroment variable')
                sys.exit('Отсутствуют переменные окружения')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if LAST_ERROR != error:
                send_message(bot, message)
                LAST_ERROR = error
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
