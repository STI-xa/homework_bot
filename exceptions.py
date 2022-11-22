

class CommonErrors(Exception):
    """Общие ошибки, не требующие отправки сообщения в Телеграм."""
    pass

class GeneralErorrs(Exception):
    """Важные ошибки, требующие отправки в Телеграм."""
    pass