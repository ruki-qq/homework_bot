import os
from typing import Union

import requests
from dotenv import load_dotenv

load_dotenv()


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


class APIRequestError(Exception):
    pass


def check_tokens():
    pass


def send_message(bot, message):
    pass


def get_api_answer(timestamp: int) -> Union[dict[str, object], requests.exceptions.RequestException]:
    payload: dict[str, int] = {'from_date': timestamp}
    try:
        res: requests.Response = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
    except requests.exceptions.RequestException as err:
        print('log err')
        return err

    print('log ok')
    return res.json()


def check_response(response: dict[str, object]):
    keys = ['homeworks', 'current_date']
    if list(response.keys()) != keys:
        print('log wrong keys in res')


res = get_api_answer(1624968474)

check_response(res)

# def parse_status(homework):
#     ...
#
#     return f'Изменился статус проверки работы "{homework_name}". {verdict}'
#
#
# def main():
#     """Основная логика работы бота."""
#
#     ...
#
#     bot = telegram.Bot(token=TELEGRAM_TOKEN)
#     timestamp = int(time.time())
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
