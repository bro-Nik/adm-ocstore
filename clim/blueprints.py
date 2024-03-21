from . import stock, deal, other_shops, option, product, main


def make_blueprints(app):
    app.register_blueprint(stock.bp, url_prefix='/crm/stock')
    app.register_blueprint(deal.bp, url_prefix='/crm/deal')
    app.register_blueprint(other_shops.bp, url_prefix='/site/other_shops')
    app.register_blueprint(option.bp, url_prefix='/site/option')
    app.register_blueprint(product.bp, url_prefix='/site/product')
    app.register_blueprint(main.bp)

