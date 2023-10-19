import logging
import os
from time import time
from typing import Union

import requests
import telegram
from dotenv import load_dotenv

from custom_exeptions import APIError
from custom_types import JSONAnswer, Homework

load_dotenv()

logger = logging.getLogger(__name__)

f_handler = logging.FileHandler(f'{__name__}.log')
f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
f_handler.setLevel(logging.DEBUG)
f_handler.setFormatter(f_format)

logger.addHandler(f_handler)

PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = ''

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

PRACTICUM_PROFILE_LINK = 'https://practicum.yandex.ru/profile/'


def check_api_availability() -> None:
    pass

def check_tokens() -> None:
    tokens: list = [
        (
            PRACTICUM_TOKEN,
            'PRACTICUM_TOKEN',
            requests.Request(
                'GET',
                ENDPOINT,
                HEADERS,
                params={'from_date': int(time())},
            ).prepare(),
        ),
        (
            TELEGRAM_TOKEN,
            'TELEGRAM_TOKEN',
            requests.Request(
                'GET',
                f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe',
            ).prepare(),
        ),
    ]
    for token, token_name, prepped_req in tokens:
        if token is None:
            err_msg: str = f'Token {token_name} is not defined.'
            logger.error(err_msg)
            raise TypeError(err_msg)

        session = requests.Session()

        try:
            res = session.send(prepped_req)
        except requests.exceptions.RequestException as err:
            err_msg: str = (
                f'Endpoint error when checking token {token_name} validity.'
            )
            logger.error(err_msg)
            raise APIError(err_msg) from err

        if res.status_code != 200:
            err_msg: str = f'Token {token_name} is not valid.'
            logger.error(err_msg)
            raise ValueError(err_msg)


def send_message(bot, message):
    pass


def get_api_answer(
    timestamp: int,
) -> JSONAnswer:
    payload: dict[str, int] = {'from_date': timestamp}
    try:
        res: requests.Response = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
    except requests.exceptions.RequestException as err:
        print('log err')
        raise APIError(err)

    print('log ok')
    return res.json()


def check_response(response: JSONAnswer) -> None:
    """Проверяет верность полученного от API ответа."""
    homeworks_key = 'homeworks'
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
                _hw_field: Union[int, str] = hw[key]
            except KeyError as err:
                print('log no key in hw')
                raise KeyError(f'No key {key} in homework: {err}')


def parse_status(homework: Homework) -> str:
    """Получает имя и текущий статус домашней работы и возвращает информационное сообщение по ней."""
    homework_name: str = homework.get('homework_name')
    status: str = homework.get('status')
    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError as err:
        print('log key err')
        raise KeyError(f'No key {status} in verdicts: {err}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


check_tokens()


# def main():
#     """Основная логика работы бота."""
#
#     try:
#         check_tokens()
#     except TypeError:
#         msg = 'Ошибка при проверке API-токена.'
#
#     bot = telegram.Bot(token=TELEGRAM_TOKEN)
#     timestamp = int(time())
#
#     ...
#
#     while True:
#         try:
#             ...
#
#         except Exception as error:
#             message = f'Сбой в работе программы: {error}'
#             ...
#         ...
#
#
# if __name__ == '__main__':
#     main()
