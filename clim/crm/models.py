from clim.models import *


def get_stock(self, stock_id, create=False):
    if stock_id:
        stock_id = int(stock_id)
        for stock in self.stocks:
            if stock.stock_id == stock_id:
                return stock
        if create:
            from .stock.models import StockProduct
            stock = StockProduct(stock_id=stock_id, quantity=0)
            self.stocks.append(stock)
            return stock


@property
def stock_quantity(self):
    return sum(stock.quantity for stock in self.stocks)


@property
def unit(self):
    return self.unit_class.description.unit


@property
def name(self):
    return self.description.name if self.description else ''


Product.get_stock = get_stock
Product.stock_quantity = stock_quantity
Product.unit = unit
Product.name = name

Category.name = name
Option.name = name
OptionValue.name = name

class Service(db.Model):
    __tablename__ = 'adm_deal_service'

    service_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45))
    time = db.Column(db.Integer)
