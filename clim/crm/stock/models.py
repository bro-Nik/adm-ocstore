from datetime import datetime
import json
from flask import flash

from ..models import db, Product
from ..utils import JsonMixin


class Stock(db.Model):
    __tablename__ = 'adm_stock'
    stock_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    sort = db.Column(db.Integer)
    products = db.relationship('StockProduct',
                               backref=db.backref('stock', lazy=True))

    def edit(self, form):
        self.name = form.get('name')
        self.sort = form.get('sort')

    def delete(self):
        if self.products:
            flash(f'У склада "{self.name}" есть товары', 'warning')
        else:
            db.session.delete(self)


class StockProduct(db.Model):
    __tablename__ = 'adm_stock_product'
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('adm_stock.stock_id'),
                         primary_key=True)
    quantity = db.Column(db.Float, default=0)
    main_product = db.relationship('Product',
                                   backref=db.backref('stocks', lazy=True))


class StockMovement(db.Model, JsonMixin):
    __tablename__ = 'adm_stock_movement'
    movement_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    date = db.Column(db.Date)
    posted = db.Column(db.Boolean)
    products = db.Column(db.Text)
    movement_type = db.Column(db.String(32))
    details = db.Column(db.Text)
    stocks = db.Column(db.Text)
    contact_id = db.Column(db.Integer, db.ForeignKey('adm_contact.contact_id'))

    def save(self, data):
        details = self.get('details', {})
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
                flash(f'Нет столько товаров на складе {stock_product.stock.name}', 'warning')
                db.session.rollback()
                error = True
                return

            # Удаление, если нет остатков
            if stock_product.quantity == 0:
                db.session.delete(stock_product)

        if direction == 1 and self.posted:
            flash(f'Документ {self.info["name"]} уже проведен', 'warning')
            return

        if direction == -1 and not self.posted:
            flash(f'Документ {self.info["name"]} еще не проведен', 'warning')
            return

        products = json.loads(self.products)
        if not products:
            flash(f'{self.info["name"]} - Нет товаров', 'warning')
            return

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

        if not error:
            self.products = json.dumps(products)
            self.posted = direction == 1

    def unposting(self):
        self.posting(-1)

    def delete(self):
        db.session.delete(self)


class StockCategory(db.Model):
    __tablename__ = 'adm_stock_category'
    stock_category_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
