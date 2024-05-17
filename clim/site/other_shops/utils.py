from datetime import datetime, timedelta
import json
import re
from typing import Literal, TypeAlias
from flask import flash, request

from clim.app import db, redis
from clim.mixins import PageMixin


Events: TypeAlias = Literal['new_prices', 'new_products']


class ShopUtils(PageMixin):
    URL_PREFIX = '.shop_'
    PAGES = {'new': 'settings', 'actions': 'settings'}
    REDIS_KEY = 'parsing_shop_id'

    @property
    def actions(self):
        return {'save': [True],
                'delete_logs': [True],
                'start_parsing': [True, 'Старт парсинга',
                                  'Начать парсинг?', ''],
                'delete': [self.shop_id, 'Удадить', 'Удалить Магазин?',
                           'Все товары и категории будут удалены']}

    def pages_settings(self):
        return {'categories': [self.shop_id, 'Категории'],
                'settings': [True, 'Настройки'],
                'logs': [True, 'Логи']}

    def save(self):
        data = self.save_data

        for key in ['name', 'domain', 'parsing']:
            setattr(self, key, data.get(key, ''))

        db.session.flush()

    def start_parsing(self):
        for category in self.categories:
            category.start_parsing()

    def delete_logs(self):
        for category in self.categories:
            category.delete_logs()

    def start_work(self) -> None:
        redis.set(f'{self.REDIS_KEY}_{self.get_id}.working', str(datetime.now()))

    def is_working_now(self) -> bool:
        time_start = redis.get(f'{self.REDIS_KEY}_{self.get_id}.working')
        if not time_start:
            return False

        time_start = datetime.strptime(time_start.decode(),
                                       '%Y-%m-%d %H:%M:%S.%f')
        return datetime.now() < time_start + timedelta(hours=2)

    def end_work(self) -> None:
        redis.delete(f'{self.REDIS_KEY}_{self.get_id}.working')


class CategoryUtils(PageMixin):
    URL_PREFIX = '.category_'
    PAGES = {'new': 'settings', 'actions': 'settings'}

    def init_to_parsing(self):
        self.logs = Log(self.get_id)
        self.events = Event(self.get_id)

    @property
    def actions(self):
        return {'save': [True],
                'delete_logs': [True],
                'start_parsing': [self.parsing, 'Старт парсинга',
                                  'Начать парсинг?', ''],
                'accept_changes': [self.changes, 'Принять события',
                                   'Метки новых товаров и цен удалятся', ''],
                'delete_only_products': [self.products, 'Удалить товары',
                                         'Удалятся только товары', ''],
                'delete': [self.other_category_id, 'Удалить',
                           'Удалить Категорию?', 'Все товары будут удалены']}

    def url_id(self):
        url_id = dict(shop_id=self.shop_id)
        if self.other_category_id:
            url_id['category_id'] = self.other_category_id
        return url_id

    def pages_settings(self):
        return {'products': [True, 'Товары'],
                'settings': [True, 'Настройки'],
                'logs': [True, 'Логи']}

    def save(self):
        data = self.save_data
        parsing = {}

        # Параметры парсинга
        keys = ['blocks_type', 'blocks_class', 'block_name_type',
                'block_name_class', 'block_name_inside', 'block_link_type',
                'block_link_class', 'block_price_type', 'block_price_class',
                'block_other_price_type', 'block_other_price_class']
        for key in keys:
            if data.get(key):
                parsing[key] = data.get(key)

        minus = re.sub(r'( ,|, )', ',', data.get('minus', ''))
        if minus:
            parsing['minus'] = minus

        self.parsing = json.dumps(parsing) if parsing else None
        self.name = data.get('name')
        self.url = data.get('url')
        self.parent_id = data.get('parent_id') or 0
        self.sort = data.get('sort') or 0

        db.session.flush()

    def start_parsing(self):
        from .tasks import get_other_products_task
        get_other_products_task.delay(self.other_category_id)
        flash(f'{self.name} - парсинг запущен')

    def delete_logs(self):
        logs = Log(self.get_id)
        redis.delete(logs.key)
        flash(f'{self.name} - Логи удалены', 'info')

    def accept_changes(self):
        # Принять изменения
        self.new_price = None
        self.new_product = None

    def delete_only_products(self):
        for product in self.products:
            product.delete()
        self.accept_changes()


class Log:
    Category: TypeAlias = Literal['info', 'debug', 'warning', 'error']
    CATEGORIES: tuple[Category, ...] = ('info', 'debug', 'warning', 'error')

    def __init__(self, module_name: str) -> None:
        self.key = f'api.{module_name}.logs'

    def get(self, timestamp: float = 0.0) -> list:
        logs = []
        for key in redis.hkeys(self.key):
            key_timestamp = key.decode()
            if float(key_timestamp) > timestamp:
                log = redis.hget(self.key, key).decode()
                log = json.loads(log)
                log['timestamp'] = key.decode()
                logs.append(log)

        return logs

    def set(self, category: Category, text: str, task_name='') -> None:
        now = datetime.now()
        timestamp = str(now.timestamp())
        text = f'{task_name + " - " if task_name else ""}{text}'
        log = {'text': text, 'category': self.CATEGORIES.index(category),
               'timestamp': timestamp, 'time': str(now)}
        redis.hset(self.key, timestamp, json.dumps(log))


class Event:
    def __init__(self, module_id: str) -> None:
        self.key = f'api.{module_id}.events'
        self.list: dict[Events, str] = {
            'new_prices': 'Новые цены',
            'new_products': 'Новые товары'
        }

    def set(self, key: str, value: list | dict) -> None:
        redis.hset(self.key, key, json.dumps(value))

    def get(self, key: str):
        value = redis.hget(self.key, key)
        if value:
            value = json.loads(value.decode())

        return value if isinstance(value, list) else []

    def update(self, ids_new: list[str], event_name: Events) -> None:

        # Прошлые данные
        ids_old = self.get(event_name)

        ids = ids_old + ids_new
        if ids:
            # Сохранение данных
            self.set(event_name, ids)

    def delete(self, key):
        redis.hdel(self.key, key)
