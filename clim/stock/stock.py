import json
from flask import render_template, redirect, url_for, request, flash, Blueprint
from flask_login import login_required
from datetime import datetime, timedelta

from clim.models import db, Category, Module, OptionValue, OptionValueSetting, Product, ProductDescription, ProductToCategory, Stock, StockMovement, StockProduct, WeightClass
# from clim.routes import get_categories, get_consumables, get_module, get_product, get_products, products


stock = Blueprint('stock', __name__, template_folder='templates', static_folder='static')


def get_products():
    return db.session.execute(db.select(Product)).scalars()


def get_product(id):
    return db.session.execute(
        db.select(Product).filter_by(product_id=id)).scalar()


def get_stocks():
    return db.session.execute(db.select(Stock)).scalars()


def get_stock(id):
    return db.session.execute(
        db.select(Stock).filter_by(stock_id=id)).scalar()


def get_categories():
    return db.session.execute(
        db.select(Category).order_by(Category.sort_order)).scalars()


def get_consumables():
    """ Получить расходные материалы """
    settings = get_settings()
    ids = settings.get('consumables_categories_ids')

    request_base = Product.query
    request_base = (request_base.join(Product.categories)
                   .where(Category.category_id.in_(ids)))
    request_base = request_base.order_by(Product.mpn)

    return request_base.all()


@stock.route('/products', methods=['GET'])
@login_required
def products():
    products = tuple(db.session.execute(
        db.select(Product)
        .filter(Product.stocks != None)).scalars())

    return render_template('stock/products.html',
                           products=products,
                           stocks=tuple(get_stocks()))


@stock.route('/movements/<string:movement_type>', methods=['GET'])
@login_required
def movements(movement_type):
    movements = tuple(db.session.execute(
        db.select(StockMovement)
        .filter(StockMovement.movement_type == movement_type)).scalars())

    return render_template('stock/movements.html',
                           movements=movements,
                           movement_type=movement_type)


@stock.route('/movements/<string:movement_type>/action', methods=['POST'])
@login_required
def movements_action(movement_type):
    ids_list = request.form.get('movements-ids')
    ids_list = json.loads(ids_list) if ids_list else []

    for id in ids_list:
        db.session.delete(get_movement(id))
    db.session.commit()

    return redirect(url_for('.movements',
                            movement_type=movement_type))


def get_movement(movement_id):
    return db.session.execute(
        db.select(StockMovement).filter_by(movement_id=movement_id)).scalar()


@stock.route('/movements/<string:movement_type>/new', methods=['GET'])
@stock.route('/movements/<string:movement_type>/<int:movement_id>', methods=['GET'])
@login_required
def movement_info(movement_type, movement_id=None):

    return render_template('stock/movement.html',
                           movement=get_movement(movement_id),
                           movement_type=movement_type,
                           products=tuple(get_products()),
                           stocks=tuple(get_stocks()))


@stock.route('/movement_add/<string:movement_type>', methods=['POST'])
@stock.route('/movement_update/<string:movement_type>_<int:movement_id>', methods=['POST'])
@login_required
def movement_update(movement_type, movement_id=None):
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

    return redirect(url_for('.movement_info',
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


def product_in_stock(product_id, stock_id):
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
        stock1 = product_in_stock(product['product_id'], product['stock_id'])
        stock2 = product_in_stock(product['product_id'], product['stock2_id'])

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
        stock1 = product_in_stock(product['product_id'], product['stock_id'])
        stock2 = product_in_stock(product['product_id'], product['stock2_id'])

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


@stock.route('/stocks', methods=['GET'])
@login_required
def stocks():
    return render_template('stock/stocks.html',
                           stocks=tuple(get_stocks()))


@stock.route('/stocks/new_stock', methods=['GET'])
@stock.route('/stocks/<int:stock_id>/settings', methods=['GET'])
@login_required
def stock_settings(stock_id=None):
    return render_template('stock/stock_settings.html',
                           stock=get_stock(stock_id))


@stock.route('/stocks/add_stock', methods=['POST'])
@stock.route('/stocks/<int:stock_id>/update', methods=['POST'])
@login_required
def stock_settings_update(stock_id=None):
    stock = get_stock(stock_id)
    if not stock:
        stock = Stock()
        db.session.add(stock)

    stock.name = request.form.get('name')
    stock.sort = request.form.get('sort')
    db.session.commit()

    return redirect(url_for('.stocks'))


def get_settings(settings={}):
    name = 'crm_stock'
    settings_in_base = db.session.execute(
        db.select(Module).filter_by(name=name)).scalar()
    if not settings_in_base:
        settings_in_base = Module(name=name)
        db.session.add(settings_in_base)

    if settings:
        settings_in_base.value = json.dumps(settings)
        db.session.commit()
        return ''

    if settings_in_base.value:
        settings = json.loads(settings_in_base.value)
    return settings


@stock.route('/settings', methods=['GET'])
@login_required
def settings():
    return render_template('stock/settings.html',
                           categories=tuple(get_categories()),
                           settings=get_settings())


@stock.route('/settings_update', methods=['POST'])
@login_required
def settings_update():
    settings = get_settings()
    ids = request.form.getlist('consumables_categories_ids')
    settings['consumables_categories_ids'] = ids
    
    return redirect(url_for('.settings'))


@stock.route('/json/products_in_stocks', methods=['GET'])
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


@stock.route('/json/consumables_in_option', methods=['GET'])
@stock.route('/json/consumables_in_option/<int:option_value_id>', methods=['GET'])
@login_required
def json_consumables_in_option(option_value_id=None):
    option_value = db.session.execute(
        db.select(OptionValueSetting)
        .filter(OptionValueSetting.option_value_id == option_value_id)).scalar()

    consumables = []
    if option_value:
        consumables = option_value.consumables

    return consumables


@stock.route('/json/consumables', methods=['GET'])
@login_required
def json_consumables():
    consumables = get_consumables()
    result = []
    for consumable in consumables:
        result.append({'name': consumable.description.name,
                       'id': consumable.product_id})

    return json.dumps(result)


@stock.route('/json/all_products', methods=['GET'])
@login_required
def json_all_products():
    result = []
    products = get_products()
    for product in products:
        result.append({'id': product.product_id,
                       'name': product.description.name,
                       'cost': product.cost,
                       'unit': product.unit_class.description.unit})

    return json.dumps(result)


@stock.route('/product/', methods=['GET'])
@stock.route('/product/<int:product_id>', methods=['GET'])
@login_required
def product_info(product_id=None):
    product = get_product(product_id)
    categories_ids = []
    if product:
        for category in product.categories:
            categories_ids.append(category.category_id)

    unit_classes = db.session.execute(db.select(WeightClass)).scalars()
    main_category = db.session.execute(
        db.select(ProductToCategory)
        .filter_by(product_id=product_id, main_category=True)).scalar()

    return render_template('stock/product_info.html',
                           product=product,
                           categories_ids=categories_ids,
                           categories=tuple(get_categories()),
                           main_category=main_category,
                           unit_classes=unit_classes)


@stock.route('/product/add_new', methods=['POST'])
@stock.route('/product/<int:product_id>/update', methods=['POST'])
@login_required
def product_info_update(product_id=None):
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

    # return redirect(url_for('.product_info',
    #                         product_id=product.product_id))
    return ''


@stock.route('/rename_products', methods=['GET'])
@login_required
def rename_products():
    products = tuple(db.session.execute(db.select(Product)).scalars())
    for product in products:
        product.description.name = product.mpn
        product.mpn = ''
    db.session.commit()

    return 'OK'
