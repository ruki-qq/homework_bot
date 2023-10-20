import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

from custom_exeptions import APIError
from custom_types import Homework, JSONAnswer

load_dotenv()

logger: logging.Logger = logging.getLogger(__name__)

s_handler: logging.StreamHandler = logging.StreamHandler()
formatter: logging.Formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
s_handler.setLevel(logging.DEBUG)
s_handler.setFormatter(formatter)

logger.addHandler(s_handler)

PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('CHAT_ID')

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORKS_KEY: str = 'homeworks'

HOMEWORK_VERDICTS: dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens() -> None:
    """Checks tokens availability and validity.

    Raises: TypeError
    """
    tokens: list[tuple[str, str]] = [
        (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
        (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
        (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID'),
    ]
    for token, token_name in tokens:
        if token is None:
            err_msg: str = f'Token {token_name} is not defined.'
            logger.critical(err_msg)
            raise TypeError(err_msg)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Sends provided message from Telegram Bot."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(
            f'Sent message: "{message}" to chat ID {TELEGRAM_CHAT_ID}'
        )
    except telegram.error.TelegramError as err:
        msg: str = (
            f'Error while sending message to chat ID {TELEGRAM_CHAT_ID}: {err}'
        )
        logger.error(msg)


def get_api_answer(
    timestamp: int,
) -> JSONAnswer:
    """Gets answer from homeworks endpoint.

    Raises: APIError, ValueError
    """
    payload: dict[str, int] = {'from_date': timestamp}
    try:
        res: requests.Response = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
    except requests.exceptions.RequestException as err:
        err_msg: str = f'Error while requesting API answer: {err}'
        logger.error(err_msg)
        raise APIError(err_msg) from err
    logger.info(
        f'Made successful request to homework API, status: {res.status_code}.'
    )
    if res.status_code != 200:
        err_msg: str = f'Token {PRACTICUM_TOKEN} seems not valid.'
        logger.critical(err_msg)
        raise ValueError(err_msg)
    return res.json()


def check_response(response: JSONAnswer) -> None:
    """Checks if API answer was valid.

    Raises: KeyError, TypeError
    """
    try:
        hw_list: list[Homework] = response[HOMEWORKS_KEY]
        _curr_date: int = response['current_date']
    except KeyError as err:
        print('log no key in array')
        raise KeyError(f'No key {HOMEWORKS_KEY} in response: {err}')
    if type(hw_list) is not list:
        msg: str = 'Homeworks object type is not list'
        logger.error(msg)
        raise TypeError(msg)


def parse_status(homework: Homework) -> str:
    """Returns info message from homework obj.

    Raises: KeyError
    """
    try:
        homework_name: str = homework['homework_name']
        status: str = homework['status']
        verdict: str = HOMEWORK_VERDICTS[status]
    except KeyError as err:
        print('log key err')
        raise KeyError(f'Key is not found: {err}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Main flow.

    Creates Telegram bot and checks endpoint and tokens.
    Then makes API request to get homework updates and sends them
    to TELEGRAM_CHAT_ID via bot.
    """
    check_tokens()
    bot: telegram.Bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp: int = int(time.time())
    while True:
        try:
            api_ans: JSONAnswer = get_api_answer(timestamp)
        except APIError as err:
            msg: str = f'Ошибка при обращении к API: {err}'
            send_message(bot, msg)
            time.sleep(RETRY_PERIOD)
            continue

        try:
            check_response(api_ans)
        except KeyError as err:
            msg: str = f'Непредусмотренный ответ от API: {err}'
            send_message(bot, msg)
            time.sleep(RETRY_PERIOD)
            continue

        try:
            for hw in api_ans.get(HOMEWORKS_KEY):
                msg: str = parse_status(hw)
                send_message(bot, msg)
        except KeyError as err:
            msg: str = f'В объекте homework не найден ключ: {err}'
            send_message(bot, msg)
            time.sleep(RETRY_PERIOD)
            continue

        timestamp = int(time.time())
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
