from clim.site.other_shops.utils import CategoryUtils

from ..models import db
from .utils import MovementUtils, ProductUtils, StockUtils


class Stock(StockUtils, db.Model):
    __tablename__ = 'adm_stock'
    stock_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    sort = db.Column(db.Integer)
    products = db.relationship('StockProduct',
                               backref=db.backref('stock', lazy=True))


class StockProduct(ProductUtils, db.Model):
    __tablename__ = 'adm_stock_product'
    product_id = db.Column(db.Integer, db.ForeignKey('oc_product.product_id'),
                           primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('adm_stock.stock_id'),
                         primary_key=True)
    quantity = db.Column(db.Float, default=0)
    main_product = db.relationship('Product',
                                   backref=db.backref('stocks', lazy=True))


class StockMovement(MovementUtils, db.Model):
    __tablename__ = 'adm_stock_movement'
    movement_id = db.Column(db.Integer, primary_key=True)
    # name = db.Column(db.String(64))
    date = db.Column(db.Date)
    posted = db.Column(db.Boolean)
    products = db.Column(db.Text)
    movement_type = db.Column(db.String(32))
    details = db.Column(db.Text)
    stocks = db.Column(db.Text)
    contact_id = db.Column(db.Integer, db.ForeignKey('adm_contact.contact_id'))


class StockCategory(CategoryUtils, db.Model):
    __tablename__ = 'adm_stock_category'
    stock_category_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
