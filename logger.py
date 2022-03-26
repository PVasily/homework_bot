import logging
from logging.handlers import RotatingFileHandler


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
