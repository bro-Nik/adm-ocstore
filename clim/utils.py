import json
from typing import Callable

from flask import request, session

from clim.site.other_shops.models import OtherProduct

from .app import db


class DiscountProducts:
    def __init__(self):
        self.attributes = None

    def load(self):
        from .models import AttributeDescription, ProductAttribute
        if not self.attributes:
            # Получем метки
            label = db.session.execute(
                db.select(AttributeDescription).filter_by(name='Метка')).scalar()
            self.attributes = list(db.session.execute(
                    db.select(ProductAttribute)
                    .filter(ProductAttribute.attribute_id == label.attribute_id,
                            ProductAttribute.text.contains('Спецпредложение'))
            ).scalars())

    def get(self):
        self.load()
        attrs = self.attributes
        return [attribute.product_id for attribute in attrs] if attrs else []


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


def json_loads(data_str: bytes):
    try:
        return json.loads(data_str)
    except json.JSONDecodeError:
        return None


def actions_in(function_or_obj: Callable, **kwargs):

    def try_action_and_save(obj):
        if obj:
            # Вызов метода, если есть изменения - записываем
            if obj.try_action(action) is not False:
                db.session.commit()

    data = json_loads(request.data)

    if isinstance(data, dict):
        action = data.get('action', '')

        if isinstance(function_or_obj, Callable):
            # Несколько объектов
            get_obj = function_or_obj
            for obj_id in data.get('ids', []):
                # Получение объекта
                obj = get_obj(obj_id, **kwargs)
                try_action_and_save(obj)
        else:
            # Один объект
            # Добавление объекта в сессию
            obj = function_or_obj
            obj.save_data = data
            new_obj = not obj.get_id
            if not obj.get_id:
                db.session.add(obj)
            try_action_and_save(obj)
            # если это новый объект - отправляем url
            if new_obj and obj.get_id:
                return {'url': obj.urls(key_type='new')[0][2]}
            # если объект удален - отправляем close
            if not obj.get_id:
                return {'close': 'true'}
    return ''


class OptionUtils:

    @property
    def price(self):
        return self.settings.price if self.settings else 0


class ProductUtils:

    @classmethod
    def all_by_filter(cls, pagination=True, filter=None):
        from .models import Category, Product, ProductAttribute, ProductOptionValue
        filter = filter or {}
        products = db.select(Product)

        if filter.get('group_attribute'):
            ga = filter.get('group_attribute')
            products = (products.join(Product.attributes)
                        .where(ProductAttribute.attribute_id == ga)
                        .order_by(ProductAttribute.text))

        if filter.get('stock'):
            stock = filter.get('stock')
            if stock == 'not not in stock':
                products = products.filter(Product.quantity > 0)
            elif stock == 'in stock':
                products = products.filter(Product.quantity == 10,
                                           Product.price != 100001)
            elif stock == 'on order':
                products = products.filter(Product.quantity == 1)
            elif stock == 'not in stock':
                products = products.filter(Product.quantity == 0)
            elif stock == 'price request':
                products = products.filter(Product.price == 100001)

        if filter.get('field'):
            field = filter.get('field')
            if field == 'ean':
                products = products.filter(Product.ean != '')
            elif field == 'jan':
                products = products.filter(Product.jan != '')
            elif field == 'isbn':
                products = products.filter(Product.isbn != '')

        if filter.get('manufacturers_ids'):
            ids = filter.get('manufacturers_ids')
            products = products.where(Product.manufacturer_id.in_(ids))

        if filter.get('categories_ids'):
            categories_ids = filter.get('categories_ids')
            products = (products.join(Product.categories)
                        .filter(Category.category_id.in_(categories_ids)))

        if filter.get('attribute_id'):
            attribute_id = filter.get('attribute_id')
            attribute_values = filter.get('attribute_values')
            products = (products.join(Product.attributes)
                        .where(ProductAttribute.attribute_id == attribute_id,
                               ProductAttribute.text.in_(attribute_values))
                        .order_by(ProductAttribute.text))

        if filter.get('option_value_id'):
            ov = filter.get('option_value_id')
            products = (products.join(Product.options)
                        .filter(ProductOptionValue.option_value_id == ov))

        if filter.get('options') == 'whith options':
            products = products.filter(Product.options is not None)
        elif filter.get('options') == 'whithout options':
            products = products.filter(Product.options is None)

        if filter.get('other_filter') == 'not_confirmed':
            products = (products.join(Product.other_shop)
                        .filter(OtherProduct.product_id is not None,
                                OtherProduct.link_confirmed is None))

        if filter.get('other_filter') == 'not_matched':
            products = products.filter(Product.other_shop is None)

        elif filter.get('other_filter') == 'different_price':
            products = (products.join(Product.other_shop)
                        .filter(OtherProduct.price != Product.price,
                                OtherProduct.link_confirmed is not None,
                                OtherProduct.price is not None))

        elif filter.get('other_filter') == 'no_options':
            products = products.filter(Product.options is None)

        if filter.get('products_ids'):
            ids = filter.get('products_ids')
            products = products.filter(Product.product_id.in_(ids))

        if filter.get('new_products'):
            products = products.filter(Product.date_added == 0)

        if filter.get('sort') == 'viewed':
            products = products.order_by(Product.viewed.desc())
        else:
            products = products.order_by(Product.mpn)

        if pagination:
            return db.paginate(products,
                               page=request.args.get('page', 1, type=int),
                               per_page=float(session.get('results_per_page', 20)),
                               error_out=False)

        return db.session.execute(products).scalars()

    @property
    def price_request(self):
        return self.price == 100001

    @property
    def on_order(self):
        return self.quantity == 1

    @property
    def in_stock(self):
        return self.quantity > 1

    @property
    def unit(self):
        return self.unit_class.description.unit
