from clim.stock.stock import stock
from clim.deal.deal import deal
from clim.other_shops.other_shops import other_shops
from clim.option.option import option
from clim.product.product import product


# Blueprints
def make_blueprints(app):
    app.register_blueprint(stock, url_prefix='/crm/stock')
    app.register_blueprint(deal, url_prefix='/crm/deal')
    app.register_blueprint(other_shops, url_prefix='/site/other_shops')
    app.register_blueprint(option, url_prefix='/site/option')
    app.register_blueprint(product, url_prefix='/site/product')
