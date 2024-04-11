import json
from typing import Dict

from ..models import Category, Module
from ..app import db
from .models import Stock, StockMovement, StockProduct, Product


def get_products():
    return db.session.execute(db.select(Product)).scalars()


def get_product(id):
    # return db.session.execute(db.select(Product).filter_by(product_id=id)).scalar()
    return Product.find(id)


def get_movement(movement_id):
    return db.session.execute(
        db.select(StockMovement).filter_by(movement_id=movement_id)).scalar()


def get_movements(type):
    return db.session.execute(
        db.select(StockMovement).filter_by(movement_type=type)).scalars()


def get_category(id):
    return db.session.execute(
        db.select(Category).filter_by(category_id=id)).scalar()


def get_stocks():
    return db.session.execute(db.select(Stock)).scalars()


def get_stock(id):
    return db.session.execute(
        db.select(Stock).filter_by(stock_id=id)).scalar()


def get_categories():
    return db.session.execute(
        db.select(Category).order_by(Category.sort_order)).scalars()


def json_dumps(data, default=None):
    return json.dumps(data, ensure_ascii=False) if data else default


def get_consumables():
    """ Получить расходные материалы """
    settings = StockSettings.get()
    ids = settings.get('consumables_categories_ids')

    request_base = Product.query
    request_base = (request_base.join(Product.categories)
                    .where(Category.category_id.in_(ids)))
    request_base = request_base.order_by(Product.mpn)

    return request_base.all()


def product_in_stock(product_id, stock_id):
    return db.session.execute(
        db.select(StockProduct)
        .filter_by(product_id=product_id, stock_id=stock_id)).scalar()


def new_product_in_stock(product_id, stock_id):
    product_in_stock = StockProduct(product_id=product_id,
                                    stock_id=stock_id,
                                    quantity=0)
    db.session.add(product_in_stock)
    return product_in_stock


class StockSettings:
    NAME = 'crm_stock'

    @classmethod
    def get_from_db(cls) -> None:
        settings = db.session.execute(
            db.select(Module).filter_by(name=cls.NAME)).scalar()
        if not settings:
            settings = Module(name=cls.NAME)
            db.session.add(settings)
        cls.settings = settings

    @classmethod
    def get(cls) -> Dict:
        cls.get_from_db()
        return json.loads(cls.settings.value) if cls.settings.value else {}

    @classmethod
    def get_item(cls, key):
        cls.get_from_db()
        settings = json.loads(cls.settings.value) if cls.settings.value else {}
        return settings.get(key)

    @classmethod
    def set(cls, settings: Dict | None) -> None:
        if settings:
            old_settings = cls.get()
            cls.settings.value = json.dumps(old_settings | settings)
            db.session.commit()


def get_consumables_categories_ids():
    return StockSettings.get_item('consumables_categories_ids')


def get_product_in_stock(product_id, stock_id):
    return db.session.execute(
        db.select(StockProduct)
        .filter_by(product_id=product_id, stock_id=stock_id)).scalar()
