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


Product.get_stock = get_stock
Product.stock_quantity = stock_quantity


class Service(db.Model):
    __tablename__ = 'adm_deal_service'

    service_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45))
    time = db.Column(db.Integer)
