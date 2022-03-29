class EmptyResponse(Exception):
    """Обрабатываем пустой ответ."""

    def __init__(self, response):
        """Создаем поле response."""
        self.response = response

    def __str__(self):
        """Формируем сообщение об ошибке."""
        if 'homeworks' not in self.response:
            return 'В ответе отсутствует ключ "homeworks"'
        return 'В ответе отсутствует ключ "current_date"'


class UnreachableTelegram(Exception):
    """Telegram недоступен."""

    def __init__(self, message):
        """Создаем поле message."""
        self.message = message

    def __str__(self):
        """Формируем сообщение об ошибке."""
        return f'{self.message}'
