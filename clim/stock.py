import json
from flask import render_template, redirect, url_for, request, session, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from clim.app import app, db, redis, celery, login_manager
from clim.models import OptionValue, OptionValueSetting, Product, Stock, StockMovement, StockProduct, StockProductInfo
from clim.routes import get_product, get_products, products


@app.route('/crm/stock/stocks', methods=['GET'])
@login_required
def stock_stocks():
    stocks = db.session.execute(db.select(Stock)).scalars()
    return render_template('stock/stocks.html', stocks=stocks)


@app.route('/crm/stock/stocks/new_stock', methods=['GET'])
@app.route('/crm/stock/stocks/<int:stock_id>/settings', methods=['GET'])
@login_required
def stock_settings(stock_id=None):
    stock = db.session.execute(
        db.select(Stock).filter(Stock.stock_id == stock_id)).scalar()
    return render_template('stock/stock_settings.html', stock=stock)


@app.route('/crm/stock/stocks/add_stock', methods=['POST'])
@app.route('/crm/stock/stocks/<int:stock_id>/update', methods=['POST'])
@login_required
def stock_settings_update(stock_id=None):
    stock = db.session.execute(
        db.select(Stock).filter(Stock.stock_id == stock_id)).scalar()
    if not stock:
        stock = Stock()
        db.session.add(stock)

    stock.name = request.form.get('name')
    stock.sort = request.form.get('sort')
    db.session.commit()

    return redirect(url_for('stock_stocks'))


@app.route('/crm/stock/products', methods=['GET'])
@login_required
def stock_products():
    products = tuple(db.session.execute(db.select(StockProductInfo)).scalars())

    stocks = tuple(db.session.execute(db.select(Stock)).scalars())
    return render_template('stock/products.html',
                           products=products,
                           stocks=stocks)


@app.route('/crm/stock/movements/<string:movement_type>', methods=['GET'])
@login_required
def stock_movements(movement_type):
    movements = tuple(db.session.execute(
        db.select(StockMovement)
        .filter(StockMovement.movement_type == movement_type)).scalars())

    return render_template('stock/movements.html', movements=movements,
                           movement_type=movement_type)

def get_movement(movement_id):
    return db.session.execute(
        db.select(StockMovement).filter_by(movement_id=movement_id)).scalar()


@app.route('/crm/stock/movements/<string:movement_type>/action', methods=['POST'])
@login_required
def stock_movements_action(movement_type):
    ids_list = request.form.get('movements-ids')
    ids_list = json.loads(ids_list) if ids_list else []

    for id in ids_list:
        db.session.delete(get_movement(id))

    db.session.commit()

    return redirect(url_for('stock_movements', movement_type=movement_type))


@app.route('/crm/stock/movements/<string:movement_type>/new', methods=['GET'])
@app.route('/crm/stock/movements/<string:movement_type>/<int:movement_id>', methods=['GET'])
@login_required
def stock_movement_info(movement_type, movement_id=None):
    movement = get_movement(movement_id)
    products = tuple(get_products(pagination=False))
    stocks = tuple(db.session.execute(db.select(Stock)).scalars())

    return render_template('stock/movement_info.html',
                           movement=movement,
                           movement_type=movement_type,
                           products=products,
                           stocks=stocks)


# @app.route('/json/all_products', methods=['GET'])
# @login_required
# def json_all_prodducts():
#     products = []
#     all_products = get_products(pagination=False)
#     for product in all_products:
#         products.append({'product_id': product.product_id, 'name': product.mpn})
#     products = json.dumps(products)
#
#     return products


@app.route('/json/stock', methods=['GET'])
@app.route('/json/stock/<int:product_id>', methods=['GET'])
@login_required
def json_products_in_stocks(product_id=None):
    products = {}
    products_in_stocks = tuple(db.session.execute(db.select(StockProduct)).scalars())
    for product in products_in_stocks:
        if not products.get(product.product_id):
            products[product.product_id] = []

        products[product.product_id].append(
            {'stock_id': product.stock_id,
             'stock_name': product.stock.name,
             'purchase_price': product.info.purchase_price,
             'unit': product.info.main_product.unit_class.description.unit,
             'quantity': product.quantity}
        )
    products = json.dumps(products)

    return products


@app.route('/json/consumables', methods=['GET'])
@app.route('/json/consumables/<int:option_value_id>', methods=['GET'])
@login_required
def json_consumables_in_option(option_value_id=None):
    option_value = db.session.execute(
        db.select(OptionValueSetting)
        .filter(OptionValueSetting.option_value_id == option_value_id)).scalar()

    consumables = []
    if option_value:
        consumables = option_value.consumables

    return consumables


@app.route('/movement_add/<string:movement_type>', methods=['POST'])
@app.route('/movement_update/<string:movement_type>_<int:movement_id>', methods=['POST'])
@login_required
def stock_movement_update(movement_type, movement_id=None):
    products = request.form.get('products_data')
    if products:
        products = json.loads(products.replace(',]', ']'))

    action = request.form.get('action')
    name = request.form.get('name')

    movement = get_movement(movement_id)

    if 'save' in action:
        if movement:
            movement.products = products
        else:
            if not name:
                movement_count = (StockMovement
                    .query.filter(StockMovement.movement_type == movement_type)
                    .count())
                if movement_type == 'coming':
                    name = 'Приход #'
                elif movement_type == 'moving':
                    name = 'Перемещение #'
                else:
                    pass
                name += str(movement_count + 1)

            movement = StockMovement(
                name=name,
                movement_type=movement_type,
                date=datetime.now().date(),
                products=products
            )
            db.session.add(movement)

    db.session.commit()

    if 'posting' in action:
        error = ''
        if movement_type == 'coming':
            error = stock_coming_posting(movement)
        elif movement_type == 'moving':
            error = stock_moving_posting(movement)

        if not error:
            movement.posted = True
            db.session.commit()
        else:
            flash(error)

    if 'cancel' in action:
        if movement.products:
            if movement_type == 'coming':
                stock_coming_unposting(json.loads(movement.products))
            elif movement_type == 'moving':
                stock_moving_unposting(json.loads(movement.products))
        movement.posted = False
        db.session.commit()

    return redirect(url_for('stock_movement_info',
                            movement_type=movement_type,
                            movement_id=movement.movement_id))


def stock_coming_posting(movement):
    products = json.loads(movement.products) if movement.products else []
    for product in products:
        product_in_stock = False
        product_in_base = get_product(product['product_id'])

        if product_in_base.stocks:
            quantity = 0
            for product_stock in product_in_base.stocks:
                quantity += product_stock.quantity
                if product_stock.stock_id == product['stock_id']:
                    product_stock.quantity += product['quantity']
                    product_in_stock = True
                    product['stock_name'] = product_stock.stock.name

            purchase_price = product_in_base.stocks[0].info.purchase_price
            product_in_base.stocks[0].info.purchase_price = (
                (purchase_price * quantity
                + product['purchase_price'] * product['quantity'])
                / (quantity + product['quantity'])
            )
        else:
            product_info = StockProductInfo(
                product_id=product['product_id'],
                purchase_price=product['purchase_price']
            )
            db.session.add(product_info)
            
        if not product_in_stock:
            new_product = StockProduct(
                product_id=product['product_id'],
                stock_id=product['stock_id'],
                quantity=product['quantity']
            )
            db.session.add(new_product)
            db.session.commit()
            product['stock_name'] = new_product.stock.name
        product['product_name'] = product_in_base.mpn
        product['unit'] = product_in_base.unit_class.description.unit

    movement.products = json.dumps(products)
    return ''


def stock_coming_unposting(products):
    for product in products:
        product_in_base = get_product(product['product_id'])

        quantity = 0
        for product_stock in product_in_base.stocks:
            quantity += product_stock.quantity
            if product_stock.stock_id == product['stock_id']:
                product_stock.quantity -= product['quantity']

        purchase_price = product_in_base.stocks[0].info.purchase_price
        if quantity == product['quantity']:
            product_in_base.stocks[0].info.purchase_price = 0
        else:
            product_in_base.stocks[0].info.purchase_price = (
                (purchase_price * quantity
                - product['purchase_price'] * product['quantity'])
                / (quantity - product['quantity'])
            )
    db.session.commit()


def stock_moving_posting(movement):
    products = json.loads(movement.products) if movement.products else []
    for product in products:
        stock1 = product_in_stock(product['product_id'], product['stock_id'])
        stock2 = product_in_stock(product['product_id'], product['stock2_id'])

        if not stock1:
            return 'Нет товаров на складе'
        if not stock2:
            stock2 = StockProduct(
                product_id=product['product_id'],
                stock_id=product['stock2_id'],
                quantity=0
            )
            db.session.add(stock2)

        if stock1.quantity < product['quantity']:
            return 'Нет столько товаров на складе'
        stock1.quantity -= product['quantity']
        stock2.quantity += product['quantity']

        product['stock_name'] = stock1.stock.name
        product['stock2_name'] = stock2.stock.name
        product['product_name'] = stock1.product.mpn
        product['unit'] = stock1.product.unit_class.description.unit

    movement.products = json.dumps(products)
    return ''


def stock_moving_unposting(products):
    for product in products:
        stock1 = product_in_stock(product['product_id'], product['stock_id'])
        stock2 = product_in_stock(product['product_id'], product['stock2_id'])

        stock1.quantity += product['quantity']
        stock2.quantity -= product['quantity']

    db.session.commit()


def product_in_stock(product_id, stock_id):
    return db.session.execute(
        db.select(StockProduct)
        .filter_by(product_id=product_id, stock_id=stock_id)).scalar()
