import os
import time
from logging import (
    DEBUG,
    FileHandler,
    Formatter,
    Logger,
    getLogger,
    StreamHandler,
)
from typing import Union

import requests
import telegram
from dotenv import load_dotenv
from requests import PreparedRequest, Session, Response
from telegram import Bot

from custom_exeptions import APIError, BotError
from custom_types import JSONAnswer, Homework

load_dotenv()

logger: Logger = getLogger(__name__)

s_handler: StreamHandler = StreamHandler()
f_handler: FileHandler = FileHandler(f'{__name__}.log')
formatter: Formatter = Formatter('%(asctime)s - %(levelname)s - %(message)s')
s_handler.setLevel(DEBUG)
s_handler.setFormatter(formatter)
f_handler.setLevel(DEBUG)
f_handler.setFormatter(formatter)

logger.addHandler(f_handler)

PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = ''

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
TG_BOT_API_ENDPOINT: str = (
    f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe'
)
HEADERS: dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS: dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

PRACTICUM_PROFILE_LINK: str = 'https://practicum.yandex.ru/profile/'


def check_api_availability(endpoint: str) -> None:
    """Checks endpoint availability.

    Raises: APIError
    """
    try:
        requests.get(endpoint)
    except requests.exceptions.RequestException as err:
        err_msg: str = f'Error while checking API availability: {err}'
        logger.error(err_msg)
        raise APIError(err_msg) from err


def check_tokens() -> None:
    """Checks tokens availability and validity.

    Raises: TypeError, ValueError
    """
    tokens: list[tuple[str, str, PreparedRequest]] = [
        (
            PRACTICUM_TOKEN,
            'PRACTICUM_TOKEN',
            requests.Request(
                'GET',
                ENDPOINT,
                HEADERS,
                params={'from_date': int(time.time())},
            ).prepare(),
        ),
        (
            TELEGRAM_TOKEN,
            'TELEGRAM_TOKEN',
            requests.Request('GET', TG_BOT_API_ENDPOINT).prepare(),
        ),
    ]
    for token, token_name, prepped_req in tokens:
        if token is None:
            err_msg: str = f'Token {token_name} is not defined.'
            logger.critical(err_msg)
            raise TypeError(err_msg)

        session: Session = requests.Session()
        res: Response = session.send(prepped_req)
        if res.status_code != 200:
            err_msg: str = f'Token {token_name} seems not valid.'
            logger.critical(err_msg)
            raise ValueError(err_msg)


def send_message(bot: Bot, message: str):
    """Sends provided message from Telegram Bot.

    Raises: BotError
    """
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as err:
        msg: str = (
            f'Error while sending message to chat ID {TELEGRAM_CHAT_ID}: {err}'
        )
        logger.error(msg)
        raise BotError(msg) from err


def get_api_answer(
    timestamp: int,
) -> JSONAnswer:
    """Gets answer from homeworks endpoint."""
    payload: dict[str, int] = {'from_date': timestamp}
    res: Response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    logger.info(
        f'Made successful request to homework API, status: {res.status_code}.'
    )
    return res.json()


def check_response(response: JSONAnswer) -> None:
    """Checks if API answer was valid.

    Raises: KeyError
    """
    homeworks_key: str = 'homeworks'
    try:
        hw_list: list[Homework] = response[homeworks_key]
    except KeyError as err:
        print('log no key in array')
        raise KeyError(f'No key {homeworks_key} in response: {err}')

    hw_keys: list[str] = [
        'id',
        'status',
        'homework_name',
        'reviewer_comment',
        'date_updated',
        'lesson_name',
    ]
    for hw in hw_list:
        for key in hw_keys:
            try:
                hw[key]
            except KeyError as err:
                print('log no key in hw')
                raise KeyError(f'No key {key} in homework: {err}')


def parse_status(homework: Homework) -> str:
    """Returns info message from homework obj.

    Raises: KeyError
    """
    homework_name: str = homework.get('homework_name')
    status: str = homework.get('status')
    try:
        verdict: str = HOMEWORK_VERDICTS[status]
    except KeyError as err:
        print('log key err')
        raise KeyError(f'No key {status} in verdicts: {err}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Main flow.

    Creates Telegram bot and checks endpoint and tokens.
    Then makes API request to get homework updates and sends them
    to TELEGRAM_CHAT_ID via bot.
    """
    bot: Bot = Bot(token=TELEGRAM_TOKEN)
    timestamp: int = int(time.time())
    while True:
        for endpoint in [ENDPOINT, TG_BOT_API_ENDPOINT]:
            try:
                check_api_availability(endpoint)
            except APIError as err:
                msg: str = (
                    f'Ошибка при обращении к API по пути {endpoint}: {err}'
                )
                send_message(bot, msg)
        try:
            check_tokens()
        except (TypeError, ValueError) as err:
            msg: str = f'Ошибка при проверке API-токена: {err}'
            bot.send_message(TELEGRAM_CHAT_ID, msg)

        api_ans: JSONAnswer = get_api_answer(timestamp)
        try:
            check_response(api_ans)
        except KeyError as err:
            msg: str = 'Непредусмотренный ответ от API: {err}'
            bot.send_message(TELEGRAM_CHAT_ID, msg)
        try:
            ...

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        timestamp = int(time.time())
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
