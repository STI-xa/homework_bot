

class CommonErrors(Exception):
    """Общие ошибки, не требующие отправки сообщения в Телеграм."""

    def __init__(self, text):
        """Вохвращает название."""
        self.text = text


class GeneralErorrs(Exception):
    """Важные ошибки, требующие отправки в Телеграм."""

    def __init__(self, text):
        """Вохвращает название."""
        self.text = text
