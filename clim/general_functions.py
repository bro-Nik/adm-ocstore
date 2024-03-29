import json
from typing import Callable

from .app import db
from .models import AttributeDescription, Category, Module, OtherProduct, \
    Product, ProductAttribute, ProductToCategory


def json_dumps_or_other(data, default=None):
    return json.dumps(data, ensure_ascii=False) if data else default


def json_loads_or_other(data, default=None):
    return json.loads(data) if data else default


def dict_from_serialize_array(data):
    # info = {}
    # for item in data:
    #     name = item['name']
    #     value = item['value']
    #     if info.get(name):
    #         if type(info.get(name)) != list:
    #             info[name] = [info[name]]
    #
    #         info[name].append(value)
    #     else:
    #         info[name] = value
    # return info

    info = {}
    for name, value in data.items():
        if info.get(name):
            if not isinstance(info.get(name), list):
                info[name] = [info[name]]
            info[name].append(value)
        else:
            info[name] = value
    return info


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


def get_other_product(product_id: int):
    return db.session.execute(
        db.select(OtherProduct).filter_by(other_product_id=product_id)).scalar()


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

        db.session.commit()
