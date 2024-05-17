from __future__ import annotations
from datetime import datetime
import json
import time
import requests

from flask import current_app

from .app import redis


BASE_URL: str = 'https://proxy6.net/api'
DATA_KEY = 'proxy_list'
API_NAME = 'proxy'


def get_proxies() -> dict:
    attempts = 5
    redis_value = redis.hget(API_NAME, DATA_KEY)
    while attempts >= 0:
        attempts -= 1
        if redis_value:
            value = json.loads(redis_value.decode())

            # Отдаем, если прокси свежие
            updated = datetime.strptime(value['updated'], '%Y-%m-%d %H:%M:%S.%f')
            time_left = (datetime.now() - updated).total_seconds()
            period = 6*60*60  # По умолчанию 6 часов
            if period > time_left:
                return value

        time.sleep(30)
        proxy_update()


def proxy_update() -> None:
    method = 'getproxy/?state=active'
    key = current_app.config['PROXY_KEY']
    data = None
    while True:
        # Получение данных
        response = requests.get(f'{BASE_URL}/{key}/{method}')
        if response:
            # Ответ с данными
            if response.status_code == 200:
                data = response.json()
                if data and data.get('list'):
                    data = data['list']
                    break

    # Сохранение данных
    # Не использовать прокси, если скоро закончится
    for _, proxy in list(data.items()):

        proxy_end = datetime.strptime(proxy['date_end'], '%Y-%m-%d %H:%M:%S')
        time_left = (proxy_end - datetime.now()).total_seconds()
        need_time = 6*60*60  # По умолчанию 6 часов
        if need_time > time_left:
            del data[proxy['id']]
    data['updated'] = str(datetime.now())

    redis.hset(API_NAME, DATA_KEY, json.dumps(data))
