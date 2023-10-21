class APIError(Exception):
    """Raised when API request failed."""

    pass


class TgBotError(Exception):
    """Raised when tg bot action causes error."""

    pass
