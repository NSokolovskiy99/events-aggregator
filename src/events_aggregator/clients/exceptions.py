"""Исключения слоя клиента внешнего Events Provider API."""


class ProviderError(Exception):
    """Базовая ошибка взаимодействия с Events Provider API."""


class SeatAlreadyTaken(ProviderError):
    """Провайдер отклонил регистрацию: место уже занято."""


class EmailAlreadyRegistered(ProviderError):
    """Провайдер отклонил регистрацию: email уже зарегистрирован на событие."""
