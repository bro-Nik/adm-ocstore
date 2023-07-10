import json
from flask import render_template, redirect, url_for, request, session, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from clim.app import app, db, redis, celery, login_manager
from clim.models import Category, Module, OptionValue, OptionValueSetting, Product, ProductDescription, ProductToCategory, Stock, StockMovement, StockProduct, WeightClass
from clim.routes import get_categories, get_consumables, get_module, get_product, get_products, products


@app.route('/crm/stock/products', methods=['GET'])
@login_required
def stock_products():
    # categories = tuple(Category.query
    #                    .order_by(Category.sort_order)
    #                    .join(Category.products)
    #                    .where(Product.stocks).all())
    #
    # products = tuple(ProductToCategory.query
    #                    .where(ProductToCategory.main_category == True)
    #                    .join(ProductToCategory.main_product)
    #                    .where(Product.stocks).all())

    products = tuple(db.session.execute(
        db.select(Product)
        .filter(Product.stocks != None)).scalars())

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

    return render_template('stock/movements.html',
                           movements=movements,
                           movement_type=movement_type)


@app.route('/crm/stock/movements/<string:movement_type>/action', methods=['POST'])
@login_required
def stock_movements_action(movement_type):
    ids_list = request.form.get('movements-ids')
    ids_list = json.loads(ids_list) if ids_list else []

    for id in ids_list:
        db.session.delete(get_movement(id))
    db.session.commit()

    return redirect(url_for('stock_movements', movement_type=movement_type))


def get_movement(movement_id):
    return db.session.execute(
        db.select(StockMovement).filter_by(movement_id=movement_id)).scalar()


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
                movement_count = (StockMovement.query
                    .filter(StockMovement.movement_type == movement_type)
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
        error = ''
        if movement.products:
            if movement_type == 'coming':
                error = stock_coming_unposting(movement)

            elif movement_type == 'moving':
                error = stock_moving_unposting(movement)

        if not error:
            movement.posted = False
            db.session.commit()
        else:
            flash(error)

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

            cost = product_in_base.cost
            product_in_base.cost = (
                (cost * quantity
                + product['cost'] * product['quantity'])
                / (quantity + product['quantity'])
            )
        else:
            product_in_base.cost = product['cost']
            
        if not product_in_stock:
            new_product = StockProduct(
                product_id=product['product_id'],
                stock_id=product['stock_id'],
                quantity=product['quantity']
            )
            db.session.add(new_product)
            db.session.commit()
            product['stock_name'] = new_product.stock.name
        product['product_name'] = product_in_base.description.meta_h1
        product['unit'] = product_in_base.unit_class.description.unit

    movement.products = json.dumps(products)
    return ''


def stock_coming_unposting(movement):
    products = json.loads(movement.products) if movement.products else []
    for product in products:
        product_in_base = get_product(product['product_id'])

        quantity = 0
        for product_stock in product_in_base.stocks:
            quantity += product_stock.quantity
            if product_stock.stock_id == product['stock_id']:
                if product_stock.quantity < product['quantity']:
                    return 'Нет столько товаров на складе'
                product_stock.quantity -= product['quantity']

        cost = product_in_base.cost
        if quantity == product['quantity']:
            product_in_base.cost = 0
        else:
            product_in_base.cost = (
                (cost * quantity
                - product['cost'] * product['quantity'])
                / (quantity - product['quantity'])
            )

    return ''


def get_product_in_stock(product_id, stock_id):
    return db.session.execute(
        db.select(StockProduct)
        .filter_by(product_id=product_id, stock_id=stock_id)).scalar()


def new_product_in_stock(product_id, stock_id):
    product_in_stock = StockProduct(
        product_id=product_id,
        stock_id=stock_id,
        quantity=0
    )
    db.session.add(product_in_stock)
    return product_in_stock


def stock_moving_posting(movement):
    products = json.loads(movement.products) if movement.products else []
    for product in products:
        stock1 = get_product_in_stock(product['product_id'], product['stock_id'])
        stock2 = get_product_in_stock(product['product_id'], product['stock2_id'])

        if not stock1:
            return 'Нет товаров на складе'
        if not stock2:
            stock2 = new_product_in_stock(product['product_id'],
                                          product['stock2_id'])
            db.session.commit()

        if stock1.quantity < product['quantity']:
            return 'Нет столько товаров на складе'
        stock1.quantity -= product['quantity']
        stock2.quantity += product['quantity']

        product['stock_name'] = stock1.stock.name
        product['stock2_name'] = stock2.stock.name
        product['product_name'] = stock1.main_product.description.meta_h1
        product['unit'] = stock1.main_product.unit_class.description.unit

        # delete product if quantity 0
        if stock1.quantity == 0:
            db.session.delete(stock1)

    movement.products = json.dumps(products)
    return ''


def stock_moving_unposting(movement):
    products = json.loads(movement.products) if movement.products else []
    for product in products:
        stock1 = get_product_in_stock(product['product_id'], product['stock_id'])
        stock2 = get_product_in_stock(product['product_id'], product['stock2_id'])

        if not stock1:
            stock1 = new_product_in_stock(product['product_id'],
                                          product['stock_id'])
        if not stock2:
            return 'Нет товаров на складе'

        if stock2.quantity < product['quantity']:
            return 'Нет столько товаров на складе'

        stock1.quantity += product['quantity']
        stock2.quantity -= product['quantity']

    return ''


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


@app.route('/crm/stock/settings', methods=['GET'])
@login_required
def crm_stock_settings():
    settings_in_base = get_module('crm_stock')
    settings = {}
    if settings_in_base.value:
        settings = json.loads(settings_in_base.value)

    categories = tuple(get_categories())
    return render_template('stock/settings.html',
                           categories=categories,
                           settings=settings)


@app.route('/crm/stock/settings_update', methods=['POST'])
@login_required
def crm_stock_settings_update():
    settings_in_base = get_module('crm_stock')
    if not settings_in_base:
        settings_in_base = Module(name='crm_stock')
        db.session.add(settings_in_base)

    settings = {}
    if settings_in_base.value:
        settings = json.loads(settings_in_base.value)

    settings['consumables_categories_ids'] = request.form.getlist('consumables_categories_ids')

    settings_in_base.value = json.dumps(settings)
    db.session.commit()
    
    return redirect(url_for('crm_stock_settings'))


@app.route('/json/products_in_stocks', methods=['GET'])
@app.route('/json/products_in_stocks/<int:product_id>', methods=['GET'])
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
             # 'cost': product.main_product.cost,
             # 'unit': product.main_product.unit_class.description.unit,
             'quantity': product.quantity}
        )

    return json.dumps(products)


@app.route('/json/consumables_in_option', methods=['GET'])
@app.route('/json/consumables_in_option/<int:option_value_id>', methods=['GET'])
@login_required
def json_consumables_in_option(option_value_id=None):
    option_value = db.session.execute(
        db.select(OptionValueSetting)
        .filter(OptionValueSetting.option_value_id == option_value_id)).scalar()

    consumables = []
    if option_value:
        consumables = option_value.consumables

    return consumables




@app.route('/json/consumables', methods=['GET'])
@login_required
def json_consumables():
    consumables = get_consumables()
    result = []
    for consumable in consumables:
        result.append({'name': consumable.description.name,
                       'id': consumable.product_id})

    return json.dumps(result)


@app.route('/json/all_products', methods=['GET'])
@login_required
def json_all_products():
    result = []
    products = get_products(pagination=False)
    for product in products:
        result.append({'id': product.product_id,
                       'name': product.description.name,
                       'cost': product.cost,
                       'unit': product.unit_class.description.unit})

    return json.dumps(result)


@app.route('/crm/stock/product/', methods=['GET'])
@app.route('/crm/stock/product/<int:product_id>', methods=['GET'])
@login_required
def stock_product(product_id=None):
    product = get_product(product_id)
    categories_ids = []
    if product:
        for category in product.categories:
            categories_ids.append(category.category_id)

    categories = tuple(get_categories())
    unit_classes = db.session.execute(db.select(WeightClass)).scalars()
    main_category = db.session.execute(db.select(ProductToCategory).filter_by(product_id=product_id, main_category=True)).scalar()

    return render_template('stock/product_info.html',
                           product=product,
                           categories_ids=categories_ids,
                           categories=categories,
                           main_category=main_category,
                           unit_classes=unit_classes)


@app.route('/crm/stock/product/add_new', methods=['POST'])
@app.route('/crm/stock/product/<int:product_id>/update', methods=['POST'])
@login_required
def stock_product_update(product_id=None):
    product = get_product(product_id)
    if not product:
        product = Product(
            model='',
            sku='',
            upc='',
            ean='',
            jan='',
            isbn='',
            mpn='',
            location='',
            quantity=0,
            stock_status_id=0,
            manufacturer_id=0,
            shipping=0,
            options_buy=0,
            price=0,
            points=0,
            tax_class_id=0,
            date_available=0,
            weight=0,
            weight_class_id=0,
            length=0,
            width=0,
            height=0,
            length_class_id=0,
            subtract=0,
            minimum=0,
            sort_order=0,
            status=0,
            viewed=0,
            date_added=0,
            date_modified=0,
            noindex=1,
            cost=15000,
            suppler_code=0,
            suppler_type=0
        )
        db.session.add(product)
        db.session.commit()

    if not product.description:
        product.description = ProductDescription(
            product_id=product.product_id,
            language_id=1,
            name='',
            description='',
            short_description='',
            tag='',
            meta_title='',
            meta_description='',
            meta_keyword='',
            meta_h1=''
        )

    product.price = request.form.get('price')
    product.cost = request.form.get('cost')
    product.weight_class_id = request.form.get('unit_id')
    product.description.name = request.form.get('short_name')
    product.description.meta_h1 = request.form.get('full_name')

    main_category_id = int(request.form.get('main_category_id'))

    product_to_categories = db.session.execute(
        db.select(ProductToCategory)
        .filter_by(product_id=product.product_id)).scalars()

    not_main_category = True
    for product_to_category in product_to_categories:
        if product_to_category.category_id == main_category_id:
            product_to_category.main_category = True
            not_main_category = False
        else:
            product_to_category.main_category = False

    if not_main_category:
        main_category = ProductToCategory(
            product_id=product.product_id,
            category_id=main_category_id,
            main_category=True
        )
        db.session.add(main_category)

    categories_ids = request.form.getlist('categories_ids')
    if categories_ids:
        for category in product.categories:
            if category.category_id not in categories_ids and category.category_id != main_category_id:
                product.categories.remove(category)
            else:
                categories_ids.remove(category.category_id)

        for category_id in categories_ids:
            category = db.session.execute(
                db.select(Category).filter(Category.category_id == int(category_id))).scalar()

            product.categories.append(category)
    
    db.session.commit()

    return redirect(url_for('stock_product', product_id=product.product_id))


@app.route('/crm/stock/rename_products', methods=['GET'])
@login_required
def stock_rename_products():
    products = tuple(db.session.execute(db.select(Product)).scalars())
    for product in products:
        product.description.name = product.mpn
        product.mpn = ''
    db.session.commit()

    return 'OK'
