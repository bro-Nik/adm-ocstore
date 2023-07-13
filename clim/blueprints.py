from clim.stock.stock import stock
from clim.deal.deal import deal
from clim.other_shops.other_shops import other_shops


# Blueprints
def make_blueprints(app):
    app.register_blueprint(stock, url_prefix='/crm/stock')
    app.register_blueprint(deal, url_prefix='/crm/deal')
    app.register_blueprint(other_shops, url_prefix='/site/other_shops')
