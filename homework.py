import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from custom_exeptions import APIError
from custom_types import Homework, JSONAnswer

load_dotenv()

logger: logging.Logger = logging.getLogger(__name__)

s_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
formatter: logging.Formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - line'
    ' #%(lineno)d - %(message)s'
)
s_handler.setLevel(logging.DEBUG)
s_handler.setFormatter(formatter)

logger.addHandler(s_handler)

PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORKS_KEY = 'homeworks'
CURR_TIME_KEY = 'current_date'

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens() -> None:
    """Checks tokens availability and validity.

    Raises: TypeError
    """
    token_names = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    empty_tokens: list[str] = []
    for name in token_names:
        if globals().get(name) is None:
            empty_tokens.append(name)
    if empty_tokens:
        names = ', '.join(empty_tokens)
        err_msg = f'Tokens [{names}] are not defined.'
        logger.critical(err_msg)
        raise TypeError(err_msg)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Sends provided message by Telegram Bot."""
    logger.debug(f'Starting to send message to chat ID {TELEGRAM_CHAT_ID}')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(
            f'Sent message: "{message}" to chat ID {TELEGRAM_CHAT_ID}'
        )
    except telegram.error.TelegramError as err:
        err_msg = (
            f'Error while sending message to chat ID {TELEGRAM_CHAT_ID}: {err}'
        )
        logger.error(err_msg)


def get_api_answer(
    timestamp: int,
) -> JSONAnswer:
    """Gets answer from homeworks endpoint.

    Raises: APIError, ConnectionError
    """
    payload = {'from_date': timestamp}
    try:
        res = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.exceptions.RequestException as err:
        err_msg = (
            f'Error while requesting API answer from endpoint "{ENDPOINT}"'
            f' with parameters: {payload}\n {err}'
        )
        raise ConnectionError(err_msg) from err

    logger.info(
        f'Made successful request to homework API, status: {res.status_code}.'
    )
    if res.status_code != HTTPStatus.OK:
        err_msg: str = (
            f'Got unexpected status ({res.status_code} - {res.reason}) from'
            ' API.'
        )
        raise APIError(err_msg)
    return res.json()


def check_response(response: JSONAnswer) -> None:
    """Checks if API answer was valid.

    Raises: KeyError, TypeError
    """
    logger.debug('Starting to check API answer...')
    if not isinstance(response, dict):
        err_msg = (
            f'Response object type is {type(response)}, expected type: dict.'
        )
        raise TypeError(err_msg)

    answer_keys = [HOMEWORKS_KEY, CURR_TIME_KEY]
    missing_keys: list[str] = []
    for key in answer_keys:
        if key not in response:
            missing_keys.append(key)
    if missing_keys:
        keys = ', '.join(missing_keys)
        err_msg = f'Not found keys [{keys}] in response.'
        raise KeyError(err_msg)

    homeworks: list[Homework] = response.get(HOMEWORKS_KEY)
    if not isinstance(homeworks, list):
        err_msg = (
            f'Homeworks object type is {type(homeworks)}, expected type: list.'
        )
        raise TypeError(err_msg)
    logger.debug('API answer checked successfully.')


def parse_status(homework: Homework) -> str:
    """Returns info message from homework obj.

    Raises: KeyError
    """
    logger.debug('Starting to check homework status...')
    homework_keys = {'name': 'homework_name', 'status': 'status'}
    missing_keys = []
    for key in homework_keys.values():
        if key not in homework:
            missing_keys.append(key)
    if missing_keys:
        keys = ', '.join(missing_keys)
        err_msg = f'Not found keys [{keys}] in homework obj.'
        raise KeyError(err_msg)

    status: str = homework.get(homework_keys['status'])
    try:
        verdict: str = HOMEWORK_VERDICTS[status]
    except KeyError:
        err_msg = f'Not found key {status} in verdicts dict.'
        raise KeyError(err_msg)
    logger.debug('Homework status checked successfully.')

    homework_name: str = homework.get(homework_keys['name'])
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Main flow.

    Creates Telegram bot and checks endpoint and tokens.
    Then makes API request to get homework updates and sends them
    to TELEGRAM_CHAT_ID via bot.
    """
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    msg = ''
    while True:
        try:
            api_ans: JSONAnswer = get_api_answer(timestamp)
        except Exception as err:
            err_msg = f'Ошибка при обращении к API: {err}'
            if err_msg != msg:
                send_message(bot, err_msg)
                msg = err_msg
            logger.error(err, exc_info=True)
            time.sleep(RETRY_PERIOD)
            continue

        try:
            check_response(api_ans)
        except Exception as err:
            err_msg = f'Непредусмотренный ответ от API: {err}'
            if err_msg != msg:
                send_message(bot, err_msg)
                msg = err_msg
            logger.error(err, exc_info=True)
            time.sleep(RETRY_PERIOD)
            continue

        try:
            homeworks: list[Homework] = api_ans.get(HOMEWORKS_KEY)
            if not homeworks:
                logger.debug('No new statuses in homeworks.')
                timestamp = api_ans.get(CURR_TIME_KEY)
                continue
            msg = parse_status(homeworks.pop())
            send_message(bot, msg)
        except Exception as err:
            err_msg = f'Ошибка при проверке статуса ДЗ: {err}'
            if err_msg != msg:
                send_message(bot, err_msg)
                msg = err_msg
            logger.error(err, exc_info=True)
            continue
        finally:
            time.sleep(RETRY_PERIOD)

        timestamp = api_ans.get(CURR_TIME_KEY)


if __name__ == '__main__':
    main()
