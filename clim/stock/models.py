import json
from flask import flash

from clim.models import Product

from ..app import db


def get_stock(self, stock_id, create=False):
    for stock in self.stocks:
        if stock.stock_id == stock_id:
            return stock
    if create:
        stock = StockProduct(stock_id=stock_id, quantity=0)
        self.stocks.append(stock)
        return stock


@property
def stock_quantity(self):
    return sum(stock.quantity for stock in self.stocks)


@property
def unit(self):
    return self.unit_class.description.unit


Product.get_stock = get_stock
Product.stock_quantity = stock_quantity
Product.unit = unit


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
            flash(f'У склада "{self.name}" есть товары, он не удален')
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


class StockMovement(db.Model):
    __tablename__ = 'adm_stock_movement'
    movement_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    date = db.Column(db.Date)
    posted = db.Column(db.Boolean)
    products = db.Column(db.Text)
    movement_type = db.Column(db.String(32))
    details = db.Column(db.Text)
    stocks = db.Column(db.Text)

    def save(self):
        data = self.data
        info = {i['name']: i['value'] for i in data.get('info', {})}

        name = info.get('name')
        if name:
            self.name = name
        elif not self.name:
            types = {'coming': 'Приход', 'moving': 'Перемещение'}
            count = StockMovement.query.filter_by(movement_type=self.movement_type).count()
            name = types.get(self.movement_type, '')
            self.name = f'{name} #{count}'

        self.products = json.dumps(data.get('products', {}), ensure_ascii=False)
        self.stocks = json.dumps(data.get('stocks', {}), ensure_ascii=False)

    def posting(self, direction=1):
        self.save()
        products = json.loads(self.products)

        for p in products:
            product = Product.find(p['product_id'])
            quantity = p['quantity'] * direction

            if not product or quantity == 0:
                continue

            # Coming
            if self.movement_type == 'coming':
                product_stock = product.get_stock(p['stock_id'], create=True)
                db.session.flush()

                product_stock.quantity += quantity
                if product_stock.quantity < 0:
                    flash('Нет столько товаров на складе отправителе', 'danger')
                    db.session.rollback()
                    return False

                p['stock_name'] = product_stock.stock.name
                p['product_name'] = product.description.meta_h1
                p['unit'] = product.unit

                product.cost = ((product.cost * product.stock_quantity
                                 + p['cost'] * quantity) /
                                (product.stock_quantity + quantity))

            # Moving
            elif self.movement_type == 'moving':
                stock1 = product.get_stock(p['stock_id'], create=True)
                stock2 = product.get_stock(p['stock2_id'], create=True)

                stock1.quantity -= quantity
                stock2.quantity += quantity

                if stock1.quantity < 0 or stock2.quantity < 0:
                    flash('Нет столько товаров на складе', 'danger')
                    db.session.rollback()
                    return False

                p['stock_name'] = stock1.stock.name
                p['stock2_name'] = stock2.stock.name
                p['product_name'] = stock1.main_product.description.meta_h1
                p['unit'] = stock1.main_product.unit_class.description.unit

                if stock1.quantity == 0:
                    db.session.delete(stock1)
                if stock2.quantity == 0:
                    db.session.delete(stock2)

        self.products = json.dumps(products)
        self.posted = True

    def unposting(self):
        self.posting(-1)
        self.posted = False

    def delete(self):
        db.session.delete(self)


class StockCategory(db.Model):
    __tablename__ = 'adm_stock_category'
    stock_category_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
