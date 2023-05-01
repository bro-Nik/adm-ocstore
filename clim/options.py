import json
from flask import render_template, redirect, url_for, request
from flask_login import login_required

from clim.app import app, db
from clim.models import Attribute, AttributeDescription, Manufacturer, Option,\
    OptionDescription, OptionSetting, OptionValueSetting, OptionValue, \
    OptionValueDescription, ProductAttribute, ProductOption,\
    ProductOptionValue, Product, CategoryDescription
from clim.routes import get_discount_products, get_products, get_categories,\
    get_product


def get_option(option_id):
    return db.session.execute(
        db.select(Option).filter_by(option_id=option_id)).scalar()


def get_option_value(value_id):
    return db.session.execute(
        db.select(OptionValue).filter_by(option_value_id=value_id)).scalar()


@app.route('/adm/options', methods=['GET'])
@login_required
def options():
    """ Страница опций """
    options = db.session.execute(db.select(Option)).scalars()
    return render_template('options/options.html', options=options)


@app.route('/adm/options/add', methods=['GET'])
@app.route('/adm/options/<int:option_id>/settings', methods=['GET'])
@login_required
def option_settings(option_id=None):
    """ Добавить или изменить опцию """
    option = settings = None
    if option_id:
        option = get_option(option_id)
        if option.settings:
            settings = json.loads(option.settings.text)

    return render_template('options/settings.html',
                           option=option,
                           option_id=option_id,
                           settings=settings)


@app.route('/adm/options/add_option', methods=['POST'])
@app.route('/adm/options/<int:option_id>/update', methods=['POST'])
@login_required
def option_add(option_id=None):
    """ Отправка данных на добавление или изменение опции """
    name = request.form.get('name')
    sort = request.form.get('sort')
    type = request.form.get('type')

    settings_dict = {
        'quantity': request.form.get('quantity'),
        'subtract': int(request.form.get('subtract')),
        'price_prefix': request.form.get('price-prefix')
        }

    settings = None
    for item in settings_dict:
        if settings_dict[item]:
            settings = json.dumps(settings_dict)
            break

    if option_id:
        option = get_option(option_id)

        option.description.name = name
        option.sort_order = sort
        option.type = type
        if option.settings:
            option.settings.text = settings
        else:
            option.settings = OptionSetting(text=settings)

    else:
        option = Option(sort_order=sort, type=type, opt_image=0)
        option.description = OptionDescription(name=name, language_id=1)
        db.session.add(option)
    db.session.commit()
    return redirect(url_for('options'))


@app.route('/adm/options/delete', methods=['POST'])
@login_required
def options_delete():
    """ Удаление опций """
    options_count = request.form.get('options-count')
    if not options_count:
        return redirect(url_for('options'))

    counter = 1
    while counter <= int(options_count):
        option_id = request.form.get('option-' + str(counter))
        if not option_id:
            counter += 1
            continue
        option = get_option(option_id)

        if option.description:
            db.session.delete(option.description)
        db.session.delete(option)
        counter += 1
    db.session.commit()
    return redirect(url_for('options'))


@app.route('/adm/options/<int:option_id>/values', methods=['GET'])
@login_required
def option_values(option_id):
    """ Варианты опции """
    option = get_option(option_id)

    products_and_options = tuple(db.session.execute(
        db.select(ProductOption).filter_by(option_id=option_id)).scalars())

    count_list = {}
    other_prices = {}

    for item in tuple(products_and_options):
        if not count_list.get(item.product_option_value.option_value_id):
            count_list[item.product_option_value.option_value_id] = 0

        count_list[item.product_option_value.option_value_id] += 1

        if not item.product_option_value.product_option:
            continue

        if item.product_option_value.price == item.product_option_value.product_option.settings.price:
            continue

        other_prices[item.product.mpn] = {'name': item.product_option_value.product_option.description.name,
                                          'price': item.product_option_value.price}

    return render_template('options/values.html',
                           option=option,
                           option_id=option_id,
                           count_list=count_list,
                           other_prices=other_prices)


@app.route('/adm/options/<int:option_id>/new_value', methods=['GET'])
@app.route('/adm/options/<int:option_id>/value_<int:value_id>/settings', methods=['GET'])
@login_required
def option_value_settings(option_id, value_id=None):
    """ Добавить или изменить вариант опции """
    option = get_option(option_id)
    option_value = settings = None
    if value_id:
        option_value = get_option_value(value_id)
        if option_value.settings and option_value.settings.settings:
            settings = json.loads(option_value.settings.settings)

    attributes = db.session.execute(db.select(Attribute)).scalars()
    categories = get_categories()

    attribute_values = []

    if settings and settings.get('attribute_id'):
        request_base = ProductAttribute.query.filter_by(
            attribute_id=settings.get('attribute_id'))

        if settings.get('categories_ids'):
            request_base = (request_base.join(ProductAttribute.product)
                            .join(Product.categories)
                            .filter(CategoryDescription.category_id.in_(
                                settings.get('categories_ids'))))

        attribute_values_in_base = request_base.all()

        for attribute_value in attribute_values_in_base:
            if int(attribute_value.text) in attribute_values:
                continue

            attribute_values.append(int(attribute_value.text))

    return render_template('options/value_settings.html',
                           option_id=option_id,
                           option=option,
                           value=option_value,
                           value_id=value_id,
                           settings=settings,
                           categories=tuple(categories),
                           attributes=attributes,
                           attribute_values=attribute_values)


@app.route('/adm/options/<int:option_id>/add_value', methods=['POST'])
@app.route('/adm/options/<int:option_id>/value_<int:value_id>/update', methods=['POST'])
@login_required
def option_value_add(option_id, value_id=None):
    """ Отправка данных на добавление или изменение значения опции """
    name = request.form.get('name')
    price = request.form.get('price')
    sort = request.form.get('sort')
    settings_dict = {
        'categories_ids': request.form.getlist('categories_ids'),
        'attribute_id': request.form.get('attribute_id'),
        'attribute_values': request.form.getlist('attribute_values'),
        'stock': request.form.get('stock')
        }

    settings = None
    for item in settings_dict:
        if settings_dict[item]:
            settings = json.dumps(settings_dict)
            break

    if value_id:
        option_value = get_option_value(value_id)
        option_value.sort_order = sort
        option_value.description.name = name
        option_value.settings.price = price
        option_value.settings.settings = settings
    else:
        option_value = OptionValue(sort_order=sort, image=0,
                                   option_id=option_id)
        option_value.description = OptionValueDescription(name=name,
                                                          language_id=1,
                                                          option_id=option_id)

        option_value.settings = OptionValueSetting(price=price,
                                                   settings=settings)

        db.session.add(option_value)

    db.session.commit()

    if request.args.get('action') == 'apply':
        return redirect(url_for('option_value_settings',
                                option_id=option_id,
                                value_id=value_id))

    return redirect(url_for('option_value_products',
                            option_id=option_id,
                            value_id=value_id))


@app.route('/adm/options/<int:option_id>', methods=['POST'])
@app.route('/adm/options/<int:option_id>/<string:action>', methods=['POST'])
@login_required
def options_action(option_id, action=None):
    """ Действия над значениями опции """
    values_count = request.form.get('values-count')
    if not values_count:
        return redirect(url_for('option_values', option_id=option_id))

    counter = 1
    while counter <= int(values_count):
        next_chacked = request.form.get('value-' + str(counter))
        if not next_chacked:
            counter += 1
            continue

        value_id = request.form.get('value-id-' + str(counter))
        option_value = get_option_value(value_id)

        # Удалить
        if action == 'delete':

            if option_value.settings:
                db.session.delete(option_value.settings)
            if option_value.products_options:
                for product in option_value.products_options:
                    db.session.delete(product)
            if option_value.description:
                db.session.delete(option_value.description)
            db.session.commit()
            db.session.delete(option_value)

        # Авто привязка
        elif action == 'auto_compare':
            auto_option_to_products(option_value)

        # Отвязка
        elif action == 'clean_options':
            for product_option in option_value.products_options:
                product_clean_options(product_option.product_id)

        counter += 1
    db.session.commit()
    return redirect(url_for('option_values', option_id=option_id))


def other_products_in_option_value(option_value):
    """ Товары не подходящие по критерию выбора опции,
    но имеющие эту опцию"""
    filter = {}
    if option_value.settings and option_value.settings.settings:
        settings = json.loads(option_value.settings.settings)
        filter['categories_ids'] = settings.get('categories_ids')
        filter['attribute_id'] = settings.get('attribute_id')
        filter['attribute_values'] = settings.get('attribute_values')
        filter['stock'] = settings.get('stock')

    products = get_products(filter=filter, pagination=False)

    products_ids = []
    for product in products:
        products_ids.append(product.product_id)

    other_products = (Product.query
        .join(Product.options)
        .join(ProductOption.product_option_value)
        .filter((ProductOptionValue.option_value_id == option_value.option_value_id)
                & (ProductOptionValue.product_id.notin_(products_ids)))).all()
    return other_products


def auto_option_to_products(option_value):
    settings = json.loads(option_value.option.settings.text)
    products = get_products(filter=get_filter_options(option_value),
                            pagination=False)

    products_ids = []
    for product in products:
        products_ids.append(product.product_id)
        product_have_this_option = product_clean_other_options(product,
                                                               option_value)

        db.session.commit()

        if product_have_this_option:
            continue
        else:
            product_option = new_product_option(product.product_id,
                                                option_value,
                                                settings)

            product.options.append(product_option)
    db.session.commit()

    other_products_in_option = other_products_in_option_value(option_value)

    for product in other_products_in_option:
        for option in product.options:
            db.session.delete(option.product_option_value)
            db.session.delete(option)
    db.session.commit()


def new_product_option(product_id, option_value, settings):
    product_option = ProductOption(
        product_id=product_id,
        option_id=option_value.option.option_id,
        value='',
        required=0
    )

    product_option.product_option_value = ProductOptionValue(
        product_id=product_id,
        option_id=option_value.option.option_id,
        option_value_id=option_value.option_value_id,
        quantity=settings['quantity'],
        subtract=settings['subtract'],
        price=option_value.settings.price,
        price_prefix=settings['price_prefix'],
        points=0,
        points_prefix='=',
        weight=0,
        weight_prefix='=',
        model='',
        optsku=''
    )
    return product_option


def manual_option_to_products(product_id, option_value, settings):
    product_have_option = product_clean_other_options(get_product(product_id),
                                                      option_value)
    if not product_have_option:
        product_option = new_product_option(product_id,
                                            option_value,
                                            settings)
        db.session.add(product_option)
        db.session.commit()


def product_clean_other_options(product, option_value):
    product_have_this_option = False
    for option in product.options:
        if option.product_option_value.option_value_id == option_value.option_value_id:
            product_have_this_option = True
        else:
            if option.product_option_value:
                db.session.delete(option.product_option_value)
            db.session.delete(option)

    return product_have_this_option


def product_clean_options(product_id):
    product = get_product(product_id)

    for option in product.options:
        if option.product_option_value:
            db.session.delete(option.product_option_value)
        db.session.delete(option)
    db.session.commit()


@app.route('/adm/options/<int:option_id>/change', methods=['POST'])
@login_required
def change_options_value(option_id):
    values_count = request.form.get('values-count')
    counter = 1
    result = {}

    while counter <= int(values_count):
        value_id = request.form.get('value-id-' + str(counter))
        if value_id:
            value_id = int(value_id)
            if not result.get(value_id):
                result[value_id] = {}

            price = request.form.get('price-' + str(counter))
            result[value_id]['price'] = float(price) if price else 0.0

            name = request.form.get('name-' + str(counter))
            result[value_id]['name'] = name

            sort_order = request.form.get('sort-order-' + str(counter))
            result[value_id]['sort_order'] = sort_order
        counter += 1

    option = get_option(option_id)

    for value in option.values:

        if not value.settings:
            value.settings = OptionValueSetting()

        value.settings.price = result[value.option_value_id]['price']
        value.description.name = result[value.option_value_id]['name']
        value.sort_order = result[value.option_value_id]['sort_order']

    discount_products_ids = get_discount_products()

    value_to_product = db.session.execute(
        db.select(ProductOptionValue).filter_by(option_id=option_id)).scalars()

    for value in value_to_product:
        if value.product_id in discount_products_ids:
            continue

        if not result.get(value.option_value_id):
            continue

        value.price = result[value.option_value_id]['price']

    db.session.commit()
    return redirect(url_for('option_values', option_id=option_id))


def get_option_values():
    all_options = db.session.execute(
        db.select(OptionValueDescription)
        .order_by(OptionValueDescription.option_value_id)).scalars()
    return all_options


def get_filter_options(option_value):
    filter = {}
    if option_value.settings and option_value.settings.settings:
        settings = json.loads(option_value.settings.settings)
        filter['categories_ids'] = settings.get('categories_ids')
        filter['attribute_id'] = settings.get('attribute_id')
        filter['attribute_values'] = settings.get('attribute_values')
        filter['stock'] = settings.get('stock')
        filter['manufacturers_ids'] = request.form.getlist('manufacturers_ids')
        filter['options'] = request.form.get('options')
    return filter


@app.route('/adm/options/option_<int:option_id>/value_<string:value_id>', methods=['GET', 'POST'])
@login_required
def option_value_products(option_id, value_id):

    option_value = get_option_value(value_id)

    attributes = (Attribute.query
        .join(Attribute.description)
        .where(AttributeDescription.name != None)
        .order_by(Attribute.sort_order)).all()

    filter = get_filter_options(option_value)
    products = get_products(filter=filter)

    request_base = Manufacturer.query

    if filter.get('categories_ids'):
        categories_ids = filter.get('categories_ids')
        request_base = (request_base.join(Manufacturer.products)
                    .join(Product.categories)
                   .filter(CategoryDescription.category_id.in_(categories_ids)))
    manufacturers = request_base.order_by(Manufacturer.name).all()

    other_products = other_products_in_option_value(option_value)

    return render_template('options/products.html',
                           products=products,
                           option_id=option_id,
                           value=option_value,
                           value_id=value_id,
                           manufacturers=manufacturers,
                           filter=filter,
                           attributes=attributes,
                           other_products=other_products)


@app.route('/adm/options/option_<int:option_id>/value_<string:value_id>/action/<string:action>', methods=['GET', 'POST'])
@app.route('/adm/options/option_<int:option_id>/value_<string:value_id>/action', methods=['GET', 'POST'])
@login_required
def option_value_products_action(option_id, value_id, action=None):
    """ Действия над товараим в опции """
    products_count = request.form.get('products-count')
    if not products_count:
        return redirect(url_for('option_value_products',
                                option_id=option_id,
                                value_id=value_id))

    option_value = get_option_value(value_id)

    settings = json.loads(option_value.option.settings.text)

    counter = 1
    while counter <= int(products_count):
        product_id = request.form.get('product-id-' + str(counter))
        if not product_id:
            counter += 1
            continue

        # Удаление
        if (action == 'delete'):
            product_clean_options(product_id)

        # Принять изменения
        elif action == 'option_to_products':
            manual_option_to_products(product_id, option_value, settings)

        counter += 1
    db.session.commit()

    return redirect(url_for('option_value_products',
                            option_id=option_id,
                            value_id=value_id))


@app.route('/adm/options/delete_', methods=['GET'])
@login_required
def option_del():
    options = ProductOption.query.filter(ProductOption.product_option_value == None)
    values = ProductOptionValue.query.filter(ProductOptionValue.product_option_ == None)
    for product_option in options:
        db.session.delete(product_option)
    for product_option_value in values:
        db.session.delete(product_option_value)

    return 'ok'

