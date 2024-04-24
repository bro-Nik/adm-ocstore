import json
from flask import abort, render_template, redirect, url_for, request
from flask_login import login_required

from ..models import db, Category, Product, ProductDescription, \
    ProductToCategory, WeightClass, OptionValueSetting, OptionValue, Option, \
    Attribute
from ..utils import actions_in, get_main_category, smart_int
from . import bp
from .models import Stock, StockMovement
from .utils import StockSettings, get_category, get_movement, get_product, \
    get_stock, get_stocks, json_dumps


@bp.route('/products', methods=['GET'])
@login_required
def products():
    return render_template('stock/products.html')


@bp.route('/products_load', methods=['GET'])
@login_required
def products_load():
    category_id = request.args.get('category_id', 0, type=int)

    categories = (Category.query.where(Category.parent_id == category_id)
                  .join(Category.products).where(Product.stocks != None)).all()

    products = Product.query.where(Product.stocks != None)
    if category_id:
        products = (products.join(Product.categories)
                    .where(Category.category_id == category_id))

    products_cost = 0
    for product in products.all():
        for stock in product.stocks:
            products_cost += product.cost * stock.quantity

    products = products.paginate(page=request.args.get('page', 1, type=int),
                                 per_page=20, error_out=False)

    return render_template('stock/products_load.html',
                           categories=categories,
                           products=products,
                           category=get_category(category_id),
                           stocks=tuple(get_stocks()),
                           products_cost=products_cost)


@bp.route('/movements/<string:movement_type>', methods=['GET'])
@login_required
def movements(movement_type):
    movements = (StockMovement.query.filter_by(movement_type=movement_type)
                 # .order_by(StockMovement.date.desc())
                 .order_by(StockMovement.movement_id.desc())
                 .paginate(page=request.args.get('page', 1, type=int),
                           per_page=10, error_out=False))
    return render_template('stock/movements.html',
                           not_movements=not list(movements),
                           movements=movements, movement_type=movement_type)


@bp.route('/movements/action', methods=['POST'])
@login_required
def movements_action():
    actions_in(request.data, get_movement)
    db.session.commit()
    return ''


@bp.route('/movements/<string:movement_type>/info', methods=['GET', 'POST'])
@login_required
def movement_info(movement_type):
    movement = get_movement(request.args.get('movement_id'))
    if not movement:
        movement = StockMovement(movement_type=movement_type)

    if request.method == 'POST':
        if not movement.movement_id:
            db.session.add(movement)

        data = json.loads(request.data) if request.data else {}
        action = data.get('action', '')
        if 'save' in action:
            movement.save(data)
            db.session.commit()
        if 'posting' in action:
            movement.posting()
            if movement.posted:
                db.session.commit()
        if 'unposting' in action:
            movement.unposting()
            if not movement.posted:
                db.session.commit()
        return {'redirect': str(url_for('.movement_info',
                                        movement_type=movement_type,
                                        movement_id=movement.movement_id))}

    return render_template('stock/movement/main.html',
                           movement=movement, movement_type=movement_type)


@bp.route('/stocks', methods=['GET'])
@login_required
def stocks():
    stocks = (Stock.query.order_by(Stock.sort.asc())
              .paginate(page=request.args.get('page', 1, type=int),
                        per_page=10, error_out=False))
    return render_template('stock/stocks.html', stocks=stocks)


@bp.route('/stocks_action', methods=['POST'])
@login_required
def stocks_action():
    actions_in(request.data, get_stock)
    db.session.commit()
    return ''


@bp.route('/stocks/stock_settings', methods=['GET', 'POST'])
@login_required
def stock_settings():
    stock = get_stock(request.args.get('stock_id'))

    if request.method == 'POST':
        if not stock:
            stock = Stock()
            db.session.add(stock)

        stock.edit(request.form)
        db.session.commit()
        return redirect(url_for('.stocks'))

    return render_template('stock/stock_settings.html', stock=stock)


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    menu = [{'name': 'Расходные материалы',
             'url': url_for('.settings_consumables')}]
    return render_template('stock/settings/settings.html', menu=menu)


@bp.route('/settings/consumables', methods=['GET', 'POST'])
@login_required
def settings_consumables():
    key = 'consumables_categories_ids'
    if request.method == 'POST':
        StockSettings.set({key: request.form.getlist(key)})
        return ''

    ids = StockSettings.get_item(key)
    categories = db.session.execute(
        db.select(Category).filter(Category.category_id.in_(ids))).scalars()
    options = db.session.execute(db.select(Option)).scalars()
    return render_template('stock/settings/consumables.html', options=options,
                           categories=categories)


@bp.route('/settings/consumables_in_option', methods=['GET', 'POST'])
@login_required
def consumables_in_option():
    value_id = request.args.get('value_id')
    value = db.session.execute(
        db.select(OptionValue).filter_by(option_value_id=value_id)).scalar()

    if request.method == 'POST':
        if not value.settings:
            value.settings = OptionValueSetting()

        data = json.loads(request.data) if request.data else {}
        value.settings.consumables = json_dumps(data.get('products'))
        db.session.commit()
        return ''

    settings = attribute = None
    if value.settings and value.settings.settings:
        settings = json.loads(value.settings.settings)
        attribute = db.session.execute(
            db.select(Attribute)
            .filter_by(attribute_id=settings.get('attribute_id'))).scalar()

    consumables = None
    if value.settings and value.settings.consumables:
        consumables = json.loads(value.settings.consumables)
        for consumable in consumables:
            product = get_product(consumable['product_id'])
            consumable['cost'] = product.cost or 0
            consumable['name'] = product.description.name
    return render_template('stock/settings/consumables_option.html',
                           option_id=request.args.get('option_id'),
                           value=value,
                           settings=settings,
                           option_value_consumables=consumables,
                           attribute=attribute)


# Не нашел где применяется
# @bp.route('/json/products_in_stocks', methods=['GET'])
# @login_required
# def json_products_in_stocks(product_id=None):
#     products = {}
#     products_in_stocks = tuple(db.session.execute(db.select(StockProduct)).scalars())
#     for product in products_in_stocks:
#         if not products.get(product.product_id):
#             products[product.product_id] = []
#
#         products[product.product_id].append(
#             {'stock_id': product.stock_id,
#              'stock_name': product.stock.name,
#              # 'cost': product.main_product.cost,
#              # 'unit': product.main_product.unit_class.description.unit,
#              'quantity': product.quantity}
#         )
#
#     return json.dumps(products)


@bp.route('/json/consumables_in_option', methods=['GET'])
@bp.route('/json/consumables_in_option/<int:option_value_id>', methods=['GET'])
@login_required
def json_consumables_in_option(option_value_id=None):
    option_value = db.session.execute(
        db.select(OptionValueSetting)
        .filter_by(option_value_id=option_value_id)
    ).scalar()
    if option_value and option_value.consumables:
        consumables = json.loads(option_value.consumables)
        for consumable in consumables:
            product = get_product(consumable['product_id'])
            consumable['price'] = product.cost or 0
            consumable['name'] = product.description.name
            consumable['unit'] = product.unit
        return consumables

    return []


# не нашел где применяется/
# @bp.route('/json/consumables', methods=['GET'])
# @login_required
# def json_consumables():
#     result = []
#     for c in get_consumables():
#         result.append({'name': c.description.name, 'id': c.product_id})
#
#     return json.dumps(result)


# не нашел где применяется/
# @bp.route('/json/all_products', methods=['GET'])
# @login_required
# def json_all_products():
#     result = []
#     for product in get_products():
#         result.append({'id': product.product_id,
#                        'name': product.description.name,
#                        'cost': product.cost,
#                        'unit': product.unit})
#
#     return json.dumps(result)


@bp.route('/product/', methods=['GET'])
@bp.route('/product/<int:product_id>', methods=['GET'])
@login_required
def product_info(product_id=None):
    product = get_product(product_id)
    unit_classes = db.session.execute(db.select(WeightClass)).scalars()
    main_category = get_main_category(product_id)

    return render_template('stock/product_info.html',
                           product=product,
                           main_category=main_category,
                           unit_classes=unit_classes)


@bp.route('/product/add_new', methods=['POST'])
@bp.route('/product/<int:product_id>/update', methods=['POST'])
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

    return str(product.product_id)


@bp.route('/ajax_products', methods=['GET'])
@login_required
def ajax_products():
    per_page = 20
    search = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    result = {'results': []}

    request_products = Product.query
    if search:
        request_products = (request_products.join(Product.description)
                            .where(ProductDescription.name.contains(search)))

    products = request_products.paginate(page=page, per_page=per_page,
                                         error_out=False)

    for product in products:
        result['results'].append({'id': str(product.product_id),
                                  'text': product.description.name,
                                  'price': product.cost,
                                  'unit': product.unit})

    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}

    return json.dumps(result)


@bp.route('/ajax_products_one', methods=['GET'])
@login_required
def ajax_products_one():
    product = get_product(request.args.get('product_id'))

    return json.dumps({'id': str(product.product_id),
                       'text': product.description.name,
                       'price': product.cost,
                       'unit': product.unit}) if product else ''


@bp.route('/ajax_stocks_first', methods=['GET'])
@login_required
def ajax_stocks_first():
    product_id = request.args.get('product_id', 0, type=int) or abort(404)
    stock_id = request.args.get('stock_id')

    request_stock = Stock.query

    if stock_id:
        request_stock = request_stock.filter(Stock.stock_id == stock_id)

    stock = db.session.execute(request_stock).scalar()

    quantity = 0
    unit = ''
    for product in stock.products:
        if product.product_id == product_id:
            quantity = smart_int(product.quantity)
            unit = product.main_product.unit
            break
    unit = unit or get_product(product_id).unit

    return json.dumps({'id': stock.stock_id,
                       'text': stock.name,
                       'subtext': f'{quantity} {unit}'}) if stock else ''


@bp.route('/ajax_stocks', methods=['GET'])
@login_required
def ajax_stocks():
    search = request.args.get('search')
    product_id = request.args.get('product_id', 0, type=int)
    per_page = 20
    result = {'results': []}

    request_stocks = Stock.query
                      
    if search:
        request_stocks = (request_stocks.where(Stock.name.contains(search)))

    stocks = request_stocks.paginate(page=request.args.get('page', 1, type=int),
                                     per_page=per_page, error_out=False)

    unit = ''
    for stock in stocks:
        quantity = ''
        if product_id:
            quantity = 0
            for product in stock.products:
                if product.product_id == product_id:
                    quantity = smart_int(product.quantity)
                    unit = product.main_product.unit
                    break
            unit = unit or get_product(product_id).unit
            quantity = f'{quantity} {unit}'
        result['results'].append({'id': str(stock.stock_id),
                                  'text': stock.name,
                                  'subtext': quantity})

    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}
    return json.dumps(result)


@bp.route('/rename_products', methods=['GET'])
@login_required
def rename_products():
    products = tuple(db.session.execute(db.select(Product)).scalars())
    for product in products:
        product.description.name = product.mpn
        product.mpn = ''
    db.session.commit()

    return 'OK'


@bp.route('/set_products_page', methods=['GET'])
@login_required
def set_products_page():
    return render_template('stock/set_products_page.html')


@bp.route('/set_products', methods=['GET'])
@login_required
def set_products():
    search = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category_id')
    parent_id = category_id if category_id else 0

    categories = Category.query.where(Category.parent_id == parent_id)
    products = Product.query

    if search:
        search = search.replace('_', ' ')

        categories = (categories.join(Category.description)
                      .where(CategoryDescription.name.contains(search)))
        if category_id:
            products = (products.join(Product.categories)
                        .where(Category.category_id == category_id))

        products = (products.join(Product.description)
                    .where(ProductDescription.name.contains(search)))

    else:
        products = (products.join(Product.categories)
                    .where(Category.category_id == category_id))

    categories = categories.all()
    products = products.paginate(page=page, per_page=20, error_out=False)
    category = db.session.execute(db.select(Category)
                                  .filter_by(category_id=category_id)).scalar()

    return render_template('stock/set_products.html',
                           categories=categories,
                           products=products,
                           category=category)
