import json
import pickle
from flask import render_template, redirect, url_for, request, flash, Blueprint
from flask_login import login_required
from datetime import datetime, timedelta
from clim.general_functions import dict_get_or_other, get_category, get_main_category
from clim.jinja_filters import money, smart_int

from clim.models import Attribute, CategoryDescription, Option, db, Category, Module, OptionValue, OptionValueSetting, Product, ProductDescription, ProductToCategory, Stock, StockMovement, StockProduct, WeightClass
from clim.app import redis
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


def json_dumps_or_other(data, default=None):
    return json.dumps(data, ensure_ascii=False) if data else default


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

    return render_template('stock/products_general.html')


@stock.route('/productse', methods=['GET'])
@login_required
def products_load():
    page = dict_get_or_other(request.args, 'page', 1)
    category_id = request.args.get('category_id')
    parent_id = category_id if category_id else 0
    in_stock = True

    request_categories = (Category.query
        .where(Category.parent_id == parent_id))

    request_products = Product.query
    if in_stock:
        request_products = (request_products.where(Product.stocks != None))
        request_categories = (request_categories.join(Category.products)
            .where(Product.stocks != None))

    request_products = (request_products.join(Product.categories)
        .where(Category.category_id == category_id))

    categories = request_categories.all()
    products = request_products.paginate(page=page,
                                 per_page=20,
                                 error_out=False)

    return render_template('stock/products_load.html',
                           categories=categories,
                           products=products,
                           category=get_category(category_id),
                           stocks=tuple(get_stocks())
                           )


@stock.route('/products_all_sum/<int:category_id>', methods=['GET'])
@login_required
def products_all_sum(category_id):
    if category_id:
        products = get_category(category_id).products
    else:
        products = Product.query.where(Product.stocks != None).all()

    all_sum = 0
    for product in products: 
        for stock in product.stocks:
            all_sum += stock.main_product.cost * stock.quantity

    return money(all_sum)


@stock.route('/products2', methods=['GET'])
@login_required
def products2():
    products = tuple(db.session.execute(
        db.select(Product)
        .filter(Product.stocks != None)).scalars())

    return render_template('stock/products2.html',
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
    data = json.loads(request.data) if request.data else {}

    action = data.get('action')
    ids = data.get('ids')

    for id in ids:
        db.session.delete(get_movement(id))
    db.session.commit()

    return ''


def get_movement(movement_id):
    return db.session.execute(
        db.select(StockMovement).filter_by(movement_id=movement_id)).scalar()


@stock.route('/movements/<string:movement_type>/movement_info', methods=['GET'])
@login_required
def movement_info(movement_type):
    movement_id = request.args.get('movement_id')

    return render_template('stock/movement.html',
                           movement=get_movement(movement_id),
                           movement_type=movement_type,
                           products={},
                           stocks=tuple(get_stocks()))


@stock.route('/movement_add/<string:movement_type>', methods=['POST'])
@stock.route('/movement_update/<string:movement_type>_<int:movement_id>', methods=['POST'])
@login_required
def movement_update(movement_type, movement_id=None):
    movement = get_movement(movement_id)

    data = json.loads(request.data) if request.data else {}

    action = data.get('action')

    info_list = data.get('info') if data.get('info') else {}
    info = {}
    if info_list:
        for item in info_list:
            info[item['name']] = item['value']

    name = info.get('name')

    if 'save' in action:
        if not movement:
            movement = StockMovement(
                movement_type=movement_type,
                date=datetime.now().date()
            )
            db.session.add(movement)

            if not name:
                movement_count = (StockMovement.query
                    .filter(StockMovement.movement_type == movement_type)
                    .count())
                if movement_type == 'coming':
                    name = 'Приход #'
                elif movement_type == 'moving':
                    name = 'Перемещение #'
                name += str(movement_count + 1)

        movement.name = name
        movement.products = json_dumps_or_other(data.get('products'))
        movement.stocks = json_dumps_or_other(data.get('stocks'))

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

    return 'this is response'


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

    movement.products = json_dumps_or_other(products)
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

    movement.products = json_dumps_or_other(products)
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


@stock.route('/stocks_action', methods=['POST'])
@login_required
def stocks_action():
    data = json.loads(request.data) if request.data else {}

    action = data.get('action')
    ids = data.get('ids')

    for id in ids:
        stock = get_stock(id)
        if stock.products:
            flash('У склада "' + stock.name + '" есть товары, он не удален')
        else:
            db.session.delete(get_stock(id))
    db.session.commit()

    return ''


@stock.route('/stocks/stock_settings', methods=['GET'])
@login_required
def stock_settings():
    return render_template('stock/stock_settings.html',
                           stock=get_stock(request.args.get('stock_id')))


@stock.route('/stocks/stock_settings_update', methods=['POST'])
@login_required
def stock_settings_update():
    stock = get_stock(request.args.get('stock_id'))
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
    menu = [
    {'name': 'Расходные материалы', 'url': url_for('.settings_consumables')}
    ]
    return render_template('stock/settings/settings.html', menu=menu)


@stock.route('/settings/consumables', methods=['GET'])
@login_required
def settings_consumables():
    settings = get_settings()
    category = get_category(settings.get('consumables_category_id'))

    options = db.session.execute(db.select(Option)).scalars()
    return render_template('stock/settings/consumables.html',
                           settings=settings,
                           options=options,
                           category=category
                           )


@stock.route('/settings_update', methods=['POST'])
@login_required
def settings_consumables_update():
    settings = get_settings()
    id = request.form.get('consumables_category_id')
    settings['consumables_category_id'] = id
    get_settings(settings)
    
    return redirect(url_for('.settings'))


@stock.route('/settings/consumables_option', methods=['GET'])
@login_required
def settings_consumables_option():
    value = settings = attribute = None

    value_id = request.args.get('value_id')
    if value_id:
        value = db.session.execute(
            db.select(OptionValue).filter_by(option_value_id=value_id)).scalar()
        if value.settings and value.settings.settings:
            settings = json.loads(value.settings.settings)
            attribute = db.session.execute(
                db.select(Attribute)
                .filter_by(attribute_id=settings.get('attribute_id'))).scalar()
    return render_template('stock/settings/consumables_option.html',
                           option_id=request.args.get('option_id'),
                           value=value,
                           settings=settings,
                           attribute=attribute,
                           )


@stock.route('/settings/settings_consumables_option_update', methods=['POST'])
@login_required
def settings_consumables_option_update():
    """ Отправка настроек значения опции """
    value_id = request.args.get('value_id')
    value = db.session.execute(
        db.select(OptionValue).filter_by(option_value_id=value_id)).scalar()

    if not value.settings:
        value.settings = OptionValueSetting()

    data = json.loads(request.data) if request.data else {}
    value.settings.consumables = json_dumps_or_other(data.get('products'))
    db.session.commit()

    return ''




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
    unit_classes = db.session.execute(db.select(WeightClass)).scalars()
    main_category = get_main_category(product_id)

    return render_template('stock/product_info.html',
                           product=product,
                           main_category=main_category,
                           unit_classes=unit_classes)


@stock.route('/product/add_new', methods=['POST'])
@stock.route('/product/<int:product_id>/update', methods=['POST'])
@login_required
def product_info_update(product_id=None):
    product = get_product(product_id)
    if not product:
        product = Product()
        db.session.add(product)
        db.session.commit()

    if not product.description:
        product.description = ProductDescription(
            product_id=product.product_id,
            language_id=1
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
        db.session.commit()

    categories_ids = request.form.getlist('categories_ids')
    if categories_ids:
        print(categories_ids)
        for category in product.categories:
            if category.category_id not in categories_ids and category.category_id != main_category_id:
                product.categories.remove(category)
            else:
                categories_ids.remove(str(category.category_id))


        for category_id in categories_ids:
            category = db.session.execute(
                db.select(Category).filter(Category.category_id == int(category_id))).scalar()

            product.categories.append(category)
    
    db.session.commit()

    # return redirect(url_for('.product_info',
    #                         product_id=product.product_id))
    return str(product.product_id)


@stock.route('/ajax_products', methods=['GET'])
@login_required
def ajax_products():
    per_page = 20
    search = request.args.get('search')
    result_count = 0
    result = {'results': []}

    request_products = Product.query
    if search:
        request_products = (request_products.join(Product.description)
                   .where(ProductDescription.name.contains(search)))

    products = request_products.paginate(page=int(request.args.get('page')),
                                 per_page=per_page,
                                 error_out=False)


    for product in products:
        result['results'].append(
            {
                'id': str(product.product_id),
                'text': product.description.name,
                'cost': product.cost,
                'unit': product.unit_class.description.unit
            }
        )

    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}

    return json.dumps(result)


@stock.route('/ajax_products_one', methods=['GET'])
@login_required
def ajax_products_one():
    product_id = request.args.get('product_id')
    if not product_id:
        return ''

    product = Product.query.filter(Product.product_id == product_id).one()

    result = {}

    result['id'] = str(product.product_id)
    result['text'] = product.description.name
    result['cost'] = product.cost
    result['unit'] = product.unit_class.description.unit
    return json.dumps(result)


@stock.route('/ajax_stocks_first', methods=['GET'])
@login_required
def ajax_stocks_first():
    product_id = request.args.get('product_id')
    if not product_id:
        return ''

    stock_id = request.args.get('stock_id')

    request_stock = Stock.query

    if stock_id:
        request_stock = request_stock.filter(Stock.stock_id == stock_id)

    stock = db.session.execute(request_stock).scalar()

    quantity = 0
    for product in stock.products:
        if product.product_id == int(product_id):
            quantity = str(smart_int(product.quantity))
            if quantity != '0':
                quantity += ' ' + product.main_product.unit_class.description.unit
            break

    result = {}

    result['id'] = str(stock.stock_id) if stock else ''
    result['text'] = stock.name if stock else ''
    result['quantity'] = quantity if stock else ''
    return json.dumps(result)


@stock.route('/ajax_stocks', methods=['GET'])
@login_required
def ajax_stocks():
    search = request.args.get('search')
    product_id = request.args.get('product_id')
    per_page = 20
    result = {'results': []}

    request_stocks = Stock.query
                      
    if search:
        request_stocks = (request_stocks.where(Stock.name.contains(search)))

    stocks = request_stocks.paginate(page=int(request.args.get('page')),
                                     per_page=per_page,
                                     error_out=False)

    for stock in stocks:
        quantity = 0
        for product in stock.products:
            if product.product_id == int(product_id):
                quantity = str(smart_int(product.quantity))
                if quantity != '0':
                    quantity += ' ' + product.main_product.unit_class.description.unit
                break
        result['results'].append(
            {
                'id': str(stock.stock_id),
                'text': stock.name,
                'quantity': quantity
            }
        )

    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}
    return json.dumps(result)


# @stock.route('/ajax_categories', methods=['GET'])
# @login_required
# def get_list_all_categories():
#     query_redis = redis.get('all_categories')
#     if query_redis:
#         return pickle.loads(query_redis)
#
#     result = []
#     line = -1
#     def next(parent_id=0, line=0):
#         line += 1
#         categories = db.session.execute(
#             db.select(Category).filter_by(parent_id=int(parent_id))).scalars()
#
#         for category in categories:
#             result.append(
#                 {
#                     'id': category.category_id,
#                     'text': ' - ' * line + category.description.name
#                 }
#             )
#             next(parent_id=category.category_id,
#                  line=line)
#
#     next(line=line)
#
#     redis.set('all_categories', pickle.dumps(result))
#
#     return result


@stock.route('/rename_products', methods=['GET'])
@login_required
def rename_products():
    products = tuple(db.session.execute(db.select(Product)).scalars())
    for product in products:
        product.description.name = product.mpn
        product.mpn = ''
    db.session.commit()

    return 'OK'


@stock.route('/set_products_page', methods=['GET'])
@login_required
def set_products_page():
    return render_template('stock/set_products_page.html')


@stock.route('/set_products', methods=['GET'])
@login_required
def set_products():
    search = request.args.get('search')
    page = request.args.get('page')
    page = int(page) if page else 1
    category_id = request.args.get('category_id')
    parent_id = category_id if category_id else 0

    request_categories = (Category.query
        .where(Category.parent_id == parent_id))

    request_products = Product.query

    if search:
        search = search.replace('_', ' ')
        request_categories = (request_categories.join(Category.description)
                   .where(CategoryDescription.name.contains(search)))
        if category_id:
            request_products = (request_products.join(Product.categories)
                .where(Category.category_id == category_id))
        request_products = (request_products.join(Product.description)
                   .where(ProductDescription.name.contains(search)))
    else:
        request_products = (request_products.join(Product.categories)
            .where(Category.category_id == category_id))

    categories = request_categories.all()
    products = request_products.paginate(page=page,
                                 per_page=20,
                                 error_out=False)
    category = db.session.execute(db.select(Category)
                                  .filter_by(category_id=category_id)).scalar()

    return render_template('stock/set_products.html',
                           categories=categories,
                           products=products,
                           category=category)


def get_consumables_categories_ids():
    query_redis = redis.get('consumables_categories_ids')
    if query_redis:
        return pickle.loads(query_redis)

    settings = {}
    settings_in_base = db.session.execute(
        db.select(Module).filter_by(name='crm_stock')).scalar()

    if settings_in_base.value:
        settings = json.loads(settings_in_base.value)

    main_category_id = settings.get('consumables_category_id')

    result = []
    result.append(main_category_id)

    def next(parent_id):
        categories = db.session.execute(
            db.select(Category).filter_by(parent_id=int(parent_id))).scalars()

        for category in categories:
            result.append(category.category_id)
            next(category.category_id)

    if main_category_id:
        next(main_category_id)

    redis.set('consumables_categories_ids', pickle.dumps(result))
    return result


