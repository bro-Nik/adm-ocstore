from . import other_shops, option, product, main, user, crm


def make_blueprints(app):
    app.register_blueprint(crm.bp, url_prefix='/crm')
    app.register_blueprint(other_shops.bp, url_prefix='/site/other_shops')
    app.register_blueprint(option.bp, url_prefix='/site/option')
    app.register_blueprint(product.bp, url_prefix='/site/product')
    app.register_blueprint(user.bp, url_prefix='/crm/user')
    app.register_blueprint(main.bp)
