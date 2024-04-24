from datetime import datetime
import json
import locale
from typing import Callable

from .models import Service, db, ProductToCategory, Module, Category, Product, \
    AttributeDescription, ProductAttribute


def json_dumps(data, default=None):
    return json.dumps(data, ensure_ascii=False) if data else default


def json_loads(data, default=None):
    return json.loads(data) if data else default


def get_module(name):
    return db.session.execute(
        db.select(Module).filter_by(name=name)).scalar()


def get_category(category_id):
    return db.session.execute(
        db.select(Category).filter_by(category_id=category_id)).scalar()


def get_categories():
    return db.session.execute(
        db.select(Category).order_by(Category.sort_order)).scalars()


def get_product(product_id: int):
    return db.session.execute(
        db.select(Product).filter_by(product_id=product_id)).scalar()


def get_main_category(product_id):
    return db.session.execute(
        db.select(ProductToCategory)
        .filter_by(product_id=product_id, main_category=1)).scalar()


def get_discount_products():
    # Получем метки
    label = db.session.execute(
        db.select(AttributeDescription).filter_by(name='Метка')).scalar()
    attributes = db.session.execute(
            db.select(ProductAttribute)
            .filter_by(attribute_id=label.attribute_id)).scalars()

    # Отделяем акционные товары
    discount_product_ids = []
    for attribute in attributes:
        if 'Спецпредложение' in attribute.text:
            discount_product_ids.append(attribute.product_id)
    return discount_product_ids


# def get_other_product(product_id: int):
#     return db.session.execute(
#         db.select(OtherProduct).filter_by(other_product_id=product_id)).scalar()


def actions_in(data_str: bytes, function: Callable, **kwargs) -> None:
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        data = {}

    if isinstance(data, dict):
        ids = data.get('ids', [])
        action = data.get('action', '')

        for item_id in ids:
            item = function(item_id, **kwargs)
            if item and hasattr(item, action):
                getattr(item, action)()


class JsonMixin:
    def get(self, attr, default=None):
        attr_name = f'{attr}_'
        if not hasattr(self, attr_name):
            value = getattr(self, attr, '')
            setattr(self, attr_name, json.loads(value) if value else default)
        return getattr(self, attr_name)

    @property
    def info(self):
        return self.get('details', {})


def smart_int(num, default=0):
    ''' Float без точки, если оно целое '''
    if not num:
        return default

    try:
        num = float(num)
        num_abs = abs(num)
        if abs(num_abs - round(num_abs)) <= 0:
            num = round(num)

        return num
    except ValueError:  # строка не является float / int
        return default

    except TypeError:  # строка не является float / int
        return default


def money(number):
    number = smart_int(number)
    number = '{:,}'.format(number).replace(',', ' ')
    return number.replace('.', ',')


def to_json(str):
    if not str:
        return []
    return json.loads(str)


def smart_date(date_time):
    ''' Возвращает сколько прошло от входящей даты '''
    locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

    if isinstance(date_time, str):
        if 'T' in date_time:
            date_time = date_time.replace('T', ' ') + ':0.0'
        elif len(date_time) == 16:
            date_time = date_time + ':0.0'
        date_time = datetime.strptime(
            date_time, '%d.%m.%Y %H:%M:%S.%f')
            # date_time, '%Y-%m-%d %H:%M:%S.%f')

    delta_time = datetime.now() - date_time
    current_date = datetime.now().date()
    if current_date == datetime.date(date_time):
        if delta_time.total_seconds() < 60:
            result = 'только что'
        elif 60 <= delta_time.total_seconds() < 120:
            result = '1 минуту назад'
        elif 120 <= delta_time.total_seconds() < 300:
            result = str(int(delta_time.total_seconds() / 60)) + ' минуты назад'
        elif 300 <= delta_time.total_seconds() < 3600:
            result = str(int(delta_time.total_seconds() / 60)) + ' минут назад'
        else:
            result = 'сегодня, ' + str(datetime.strftime(date_time, '%H:%M'))
    elif 0 < (current_date - datetime.date(date_time)).days < 2:
        result = 'вчера, ' + str(datetime.strftime(date_time, '%H:%M'))
    else:
        date = str(datetime.strftime(date_time, '%d ')) + date_time.strftime('%B')
        year = datetime.date(date_time).year
        year = ' ' + str(year) if year != datetime.now().year else ''
        time = str(datetime.strftime(date_time, '%H:%M'))
        time = ', ' + time if time != '00:00' else ''

        result = date + year + time

    return result


def how_long_ago(event_date):
    ''' Возвращает сколько прошло от входящей даты '''
    if isinstance(event_date, str):
        event_date = datetime.strptime(event_date, '%Y-%m-%d')

    today = datetime.now().date()
    if today == datetime.date(event_date):
        result = 'сегодня'
    else:
        result = str((today - datetime.date(event_date)).days) + ' д. назад'

    return result


def smart_phone(phone_number: str) -> str:
    if not phone_number:
        return ''
    numbers = list(filter(str.isdigit, phone_number))[1:]
    return "+7 {}{}{} {}{}{}-{}{}-{}{}".format(*numbers)


def datetime_from_str(string: str) -> datetime | str:
    try:
        return datetime.strptime(string, "%d.%m.%Y %H:%M")
    except ValueError:
        return ''
    except TypeError:
        return ''


def dt_to_str(date_time):
    return datetime.strftime(date_time, "%d.%m.%Y %H:%M")


def get_services():
    return tuple(db.session.execute(db.select(Service)).scalars())
