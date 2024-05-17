from datetime import datetime
import json
from typing import Dict

from flask import flash, url_for

from ..models import db, Product, Category, Module


class StockUtils:
    URL_PREFIX = '.stock_'

    @property
    def actions(self):
        return {
            'save': [True],
            'delete': [self.stock_id, 'Удадить', 'Удалить склад?', '']
        }

    @property
    def url_id(self):
        return dict(stock_id=self.stock_id) if self.stock_id else {}


    def pages_settings(self):
        return {'info': [True, 'Инфо']}

    def save(self):
        data = self.save_data
        self.name = data.get('name')
        self.sort = data.get('sort')
        db.session.flush()
        return {'url': url_for('.stock_info', stock_id=self.stock_id)}

    def delete(self):
        if self.products:
            flash(f'У склада "{self.name}" есть товары', 'warning')
            return False
        super().delete()

    @property
    def products_cost(self):
        return sum(p.quantity * p.main_product.cost for p in self.products)


class MovementUtils:
    URL_PREFIX = '.movement_'

    @property
    def name(self):
        print('this')
        print(self.get_json('details'))
        print(self.get_json('details').get('name'))
        return self.get_json('details').get('name')

    @property
    def actions(self):
        return {
            'save': [True],
            'posting': [self.movement_id and not self.posted, 'Провести документ',
                        'Провести документ?', ''],
            'unposting': [self.posted, 'Отменить проведение',
                          'Отменить проводку документа?', ''],
            'delete': [self.movement_id, 'Удадить', 'Удалить документ?', ''],
        }

    @property
    def url_id(self):
        url_id = dict(movement_type = self.movement_type)
        if self.movement_id:
            url_id['movement_id'] = self.movement_id
        return url_id

    def pages_settings(self):
        return {'info': [True, 'Инфо']}

    def save(self):
        details = self.get_json('details') or {}
        print('save')
        data = self.save_data
        info = data.get('info', {})

        # Название
        details['name'] = (info.get('name') or
            f'{self.type_ru} #{StockMovement.query.filter_by(movement_type=self.movement_type).count()}')

        # Дата
        details['date'] = (info.get('date') or
                           datetime.strftime(datetime.now(), "%d.%m.%Y %H:%M"))

        # Комментарий
        details['comment'] = info.get('comment', '')

        # Contact
        self.contact_id = info.get('contact_id')

        if not self.posted:
            # Товары
            products = data.get('products', [])
            self.products = json.dumps(products, ensure_ascii=False)

            details['stocks'] = []
            details['sum'] = 0
            for product in products:
                # Склады
                for key, value in product.items():
                    if 'stock' in key and 'name' in key and value not in details['stocks']:
                        details['stocks'].append(value)

                # Сумма
                details['sum'] += float(product['quantity'] or 0) * float(product['price'] or 0)

        self.details = json.dumps(details, ensure_ascii=False)
        db.session.flush()
        return {'url': url_for('.movement_info', **self.url_id)}

    @property
    def type_ru(self):
        types = {'coming': 'Приход', 'moving': 'Перемещение'}
        return types.get(self.movement_type, '')

    def posting(self, direction=1):
        def change_quantity(stock_product, quantity, direction):
            nonlocal error
            # Изменение количества на складе
            stock_product.quantity += quantity * direction
            if stock_product.quantity < 0:
                flash(f'Товара {stock_product.name} не хватает на складе '
                      f'{stock_product.stock.name}', 'warning')
                db.session.rollback()
                error = True
                return

            # Удаление, если нет остатков
            if stock_product.quantity == 0:
                db.session.delete(stock_product)

        info = self.get_json('details') or {}

        if direction == 1 and self.posted:
            flash(f'Документ {info["name"]} уже проведен', 'warning')
            return False

        if direction == -1 and not self.posted:
            flash(f'Документ {info["name"]} еще не проведен', 'warning')
            return False

        products = json.loads(self.products)
        if not products:
            flash(f'{info["name"]} - Нет товаров', 'warning')
            return False

        error = False
        for p in products:
            product = Product.find(p['id'])
            quantity = float(p['quantity'] or 0) * direction
            price = float(p['price'] or 0)

            if not product or quantity == 0:
                continue

            # Приход
            if self.movement_type == 'coming':

                # Средняя закупочная стоимость
                all_spent = product.cost * product.stock_quantity + price * quantity
                all_quantity = product.stock_quantity + quantity
                product.cost = (all_spent / all_quantity) if all_quantity else 0

                # Поиск или создание товара на складе
                stock = product.get_stock(p['stock_id'], create=True)
                db.session.flush()

                change_quantity(stock, quantity, +1)

            # Перемещение
            elif self.movement_type == 'moving':
                # Поиск или создание товара на складе
                stock1 = product.get_stock(p['stock_id'], create=True)
                stock2 = product.get_stock(p['stock2_id'], create=True)

                change_quantity(stock1, quantity, -1)
                change_quantity(stock2, quantity, +1)

        if error:
            return False

        self.products = json.dumps(products)
        self.posted = direction == 1

    def unposting(self):
        return self.posting(-1)


class ProductUtils:

    @classmethod
    def get(cls, product_id, stock_id, create=False):
        product = db.session.execute(
            db.select(cls)
            .filter_by(product_id=product_id, stock_id=stock_id)).scalar()
        if not product and create:
            product = cls.create(product_id=product_id, stock_id=stock_id,
                                 quantity=0)
        return product


def get_consumables():
    """ Получить расходные материалы """
    settings = StockSettings.get()
    ids = settings.get('consumables_categories_ids')

    consumables = db.session.execute(
        db.select(Product).join(Product.categories)
        .where(Category.category_id.in_(ids)).order_by(Product.mpn)).scalar()

    return consumables


class StockSettings:

    @classmethod
    def get_from_db(cls) -> None:
        if not hasattr(cls, 'settings') or not cls.settings:
            settings = Module.get('crm_stock') or Module.create(name='crm_stock')
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
        self.settings = None


def get_consumables_categories_ids():
    return StockSettings.get_item('consumables_categories_ids')
