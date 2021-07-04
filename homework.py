import logging
import logging.config
import os
import time
from http import HTTPStatus

import requests
import telegram
import telegram.error
from dotenv import load_dotenv

load_dotenv()

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

LOGING_CONFIG = {
    'version': 1,
    'formatters': {
        'default_formatter': {
            'format': '[%(levelname)s] : %(asctime)s : %(name)s : %(message)s',
        },
    },
    'handlers': {
        'file_handler': {
            'class': 'logging.FileHandler',
            'formatter': 'default_formatter',
            'filename': 'homework_bot_log.log',
        },
        'stream_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'default_formatter',
        },
    },
    'loggers': {
        '': {
            'level': logging.DEBUG,
            'handlers': ['file_handler', 'stream_handler'],
        },
    },
}

logging.config.dictConfig(LOGING_CONFIG)
logger = logging.getLogger(__name__)
logger.debug('Логгер сконфигурирован.')


class TGBotException(Exception):
    pass


def send_message(message):
    try:
        bot.send_message(CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logger.critical(f'Ошибка отправки сообщения. Ошибка telegram: {error}')
    except Exception as error:
        raise TGBotException(f'Ошибка {error}')
    else:
        logger.info(f'Сообщение отправлено. Текст сообщения:  {message}')


def parse_homework_status(homework):
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise TGBotException('При распаковке полученной домашней работы '
                             'произошла ошибка.')
    else:
        if homework['status'] == 'rejected':
            verdict = 'К сожалению, в работе нашлись ошибки.'
        elif homework['status'] == 'reviewing':
            verdict = 'Работа взята в ревью.'
        else:
            verdict = 'Ревьюеру всё понравилось, работа зачтена!'
        return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homeworks(current_timestamp):
    message = 'При получении домашней работы произошла ошибка.'
    try:
        homework_statuses = requests.get(
            'https://praktikum.yandex.ru/api/user_api/homework_statuses/',
            headers={'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'},
            params={'from_date': current_timestamp},
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            raise TGBotException(f'{message} Неверный запрос.')
        return homework_statuses.json()
    except requests.RequestException:
        raise TGBotException(message)


def main():
    logger.debug('Программа запущена')
    current_timestamp = int(time.time())

    while True:
        try:
            last_homework = get_homeworks(current_timestamp)
            if len(last_homework['homeworks']) != 0:
                hw_status = parse_homework_status(
                    last_homework['homeworks'][0])
                send_message(hw_status)
            current_timestamp = last_homework['current_date']
            time.sleep(5 * 60)
        except TGBotException as error:
            message = f'Бот упал с ошибкой: {error}'
            logger.error(message)
            send_message(message)
            time.sleep(5 * 60)
        except Exception as error:
            message = f'Неизвестная ошибка: {error}'
            logger.exception(message)
            send_message(message)
            time.sleep(5)


if __name__ == '__main__':
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
    except telegram.error.InvalidToken:
        logger.critical('Бот не запущен. Неверный токен бота.')
    except Exception as error:
        logger.critical(f'Бот не запущен {error}', exc_info=True)
    else:
        logger.debug('Бот сконфигурирован.')
        main()
