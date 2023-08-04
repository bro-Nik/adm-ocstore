import json
import re
from flask import render_template, redirect, url_for, request, Blueprint, session
from flask_login import login_required

from clim.models import db, Attribute, AttributeDescription, Manufacturer, Option,\
    OptionDescription, OptionSetting, OptionValueSetting, OptionValue, \
    OptionValueDescription, ProductAttribute, ProductOption,\
    ProductOptionValue, Product, CategoryDescription, Category, WeightClass, ProductToCategory
from clim.general_functions import dict_from_serialize_array,\
    dict_get_or_other, get_product, get_categories, json_dumps_or_other,\
    json_loads_or_other, get_list_all_categories
from clim.stock.stock import get_consumables


option = Blueprint('option', __name__, template_folder='templates', static_folder='static')


def session_get(param):
    prefix = option.name + '_'
    return session.get(prefix + param)


def session_post(param, value):
    prefix = option.name + '_'
    session[prefix + param] = value


def int_or_other(number, default=0):
    return int(number) if number else default

def float_or_other(number, default=0):
    return float(number) if number else default


def get_option(option_id):
    return db.session.execute(
        db.select(Option).filter_by(option_id=option_id)).scalar()


def get_values():
    return db.session.execute(
        db.select(OptionValueDescription)
        .order_by(OptionValueDescription.option_value_id)).scalars()


def get_value(value_id):
    return db.session.execute(
        db.select(OptionValue).filter_by(option_value_id=value_id)).scalar()


def get_products(pagination=True, filter={}):

    request_base = Product.query

    if filter.get('stock'):
        stock = filter.get('stock')
        if stock == 'not not in stock':
            request_base = request_base.filter(Product.quantity > 0)
        elif stock == 'in stock':
            request_base = request_base.filter((Product.quantity == 10)
                                               & (Product.price != 100001))
        elif stock == 'on order':
            request_base = request_base.filter(Product.quantity == 1)
        elif stock == 'not in stock':
            request_base = request_base.filter(Product.quantity == 0)
        elif stock == 'price request':
            request_base = request_base.filter(Product.price == 100001)

    if filter.get('manufacturers_ids'):
        manufacturers_ids = filter.get('manufacturers_ids')
        request_base = request_base.where(Product.manufacturer_id.in_(manufacturers_ids))

    if filter.get('categories_ids'):
        categories_ids = filter.get('categories_ids')
        request_base = (request_base.join(Product.categories)
                   .filter(Category.category_id.in_(categories_ids)))

    if filter.get('attribute_id'):
        attribute_id = filter.get('attribute_id')
        attribute_values = filter.get('attribute_values')
        request_base = (request_base.join(Product.attributes)
                    .where((ProductAttribute.attribute_id == attribute_id)
                           & (ProductAttribute.text.in_(attribute_values)))
                    .order_by(ProductAttribute.text))

    if filter.get('options') == 'whith options':
        request_base = (request_base.filter(Product.options != None))
    elif filter.get('options') == 'whithout options':
        request_base = (request_base.filter(Product.options == None))

    #request_base = request_base.order_by(Product.mpn)

    if not pagination:
        return request_base.all()

    return request_base.paginate(page=int_or_other(request.args.get('page'), 1),
                                 per_page=int_or_other(filter.get('per_page'), 20),
                                 error_out=False)



@option.route('/options', methods=['GET'])
@login_required
def options():
    """ Страница опций """
    options = db.session.execute(db.select(Option)).scalars()
    return render_template('option/options.html', options=options)


@option.route('/delete', methods=['POST'])
@login_required
def options_action():
    """ Действия над опциями """
    data = json.loads(request.data) if request.data else {}

    action = data.get('action')
    ids = data.get('ids')

    for id in ids:
        option = get_option(id)
        if option.description:
            db.session.delete(option.description)
        db.session.delete(option)
    db.session.commit()

    return ''


@option.route('/settings', methods=['GET'])
@login_required
def option_settings():
    """ Добавить или изменить опцию """
    option_id = request.args.get('option_id')

    return render_template('option/option_settings.html',
                           option=get_option(option_id))


@option.route('/settings_update', methods=['POST'])
@login_required
def option_update():
    """ Отправка настроек опции """
    option_id = request.args.get('option_id')
    option = get_option(option_id)
    if not option:
        option = Option(opt_image=0)
        option.description = OptionDescription(language_id=1)
        db.session.add(option)

    option.description.name = dict_get_or_other(request.form, 'name', 'Без имени')
    option.sort_order = dict_get_or_other(request.form, 'sort', 0)
    option.type = request.form.get('type')

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

        if not option.settings:
            option.settings = OptionSetting()
        option.settings.text = settings

    db.session.commit()
    return redirect(url_for('.options'))


@option.route('/<int:option_id>/values', methods=['GET'])
@login_required
def option_values(option_id):
    """ Варианты опции """
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

        if not item.product_option_value.product_option.settings:
            continue

        if item.product_option_value.price == item.product_option_value.product_option.settings.price:
            continue

        other_prices[item.product.mpn] = {'name': item.product_option_value.product_option.description.name,
                                          'price': item.product_option_value.price}

    return render_template('option/option_values.html',
                           option=get_option(option_id),
                           count_list=count_list,
                           other_prices=other_prices)


@option.route('/<int:option_id>/option_value_settings', methods=['GET'])
@login_required
def value_settings(option_id):
    """ Добавить или изменить вариант опции """
    value = settings = attribute = {}

    value_id = request.args.get('value_id')
    if value_id:
        value = get_value(value_id)
        if value.settings and value.settings.settings:
            settings = json.loads(value.settings.settings)
            attribute = db.session.execute(
                db.select(Attribute)
                .filter_by(attribute_id=settings.get('attribute_id'))).scalar()
    
    return render_template('option/value_settings.html',
                           option_id=option_id,
                           value=value,
                           settings=settings,
                           categories=get_list_all_categories(),
                           attribute=attribute,
                           )


@option.route('/ajax_all_attributes', methods=['GET'])
@login_required
def ajax_all_attributes():
    per_page = 20
    search = request.args.get('search')
    result = {'results': []}

    request_base = Attribute.query.where(Attribute.description)

    if search:
        request_base = (request_base.join(Attribute.description)
                   .where(AttributeDescription.name.contains(search)))

    attributes = request_base.paginate(page=int(request.args.get('page')),
                                       per_page=per_page,
                                       error_out=False)


    for attribute in attributes:
        result['results'].append(
            {
                'id': str(attribute.attribute_id),
                'text': attribute.description.name
            }
        )

    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}

    return json.dumps(result)


@option.route('/ajax_attribute_values', methods=['GET'])
@login_required
def ajax_attribute_values():
    # Other values
    option_id = request.args.get('option_id')
    value_id = request.args.get('value_id')
    option = db.session.execute(db.select(Option).filter_by(option_id=option_id)).scalar()
    other_list = []
    for value in option.values:
        if value.option_value_id == int(value_id):
            continue

        if value.settings and value.settings.settings:
            settings = json.loads(value.settings.settings)
            other_list += settings.get('attribute_values')

    # This value
    per_page = 20
    search = request.args.get('search')

    attribute_id = request.args.get('attribute_id')
    request_base = ProductAttribute.query.filter_by(attribute_id=attribute_id).group_by(ProductAttribute.text)

    categories_ids = request.args.get('categories_ids').split(',')

    request_base = (request_base.join(ProductAttribute.product)
                    .join(Product.categories)
                    .filter(Category.category_id.in_(categories_ids)))

    if search:
        request_base = (request_base.join(Attribute.description)
                   .where(AttributeDescription.name.contains(search)))

    request_base = request_base.order_by(ProductAttribute.text)
    values = request_base.paginate(page=int(request.args.get('page')),
                                       per_page=per_page,
                                       error_out=False)


    result = {'results': []}
    for value in values:
        item = {
            'id': value.text,
            'text': value.text
        }
        if item['id'] in other_list:
            item['disabled'] = True
        result['results'].append(item)

    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}

    return json.dumps(result)


@option.route('/<int:option_id>/value_settings_update', methods=['POST'])
@login_required
def value_settings_update(option_id):
    """ Отправка настроек значения опции """
    value_id = request.args.get('value_id')

    data = json_loads_or_other(request.data, {}) 
    info_list = dict_get_or_other(data, 'info', {})
    info = dict_from_serialize_array(info_list)

    settings_dict = {
        'categories_ids': dict_get_or_other(info, 'categories_ids', []),
        'attribute_id': dict_get_or_other(info, 'attribute_id'),
        'attribute_values': dict_get_or_other(info, 'attribute_values', []),
        'stock': dict_get_or_other(info, 'stock')
        }

    settings = None
    for item in settings_dict:
        if settings_dict[item]:
            settings = json.dumps(settings_dict)
            break

    value = get_value(value_id)
    if not value:
        value = OptionValue(option_id=option_id)
        db.session.add(value)
    if not value.description:
        value.description = OptionValueDescription(language_id=1,
                                                   option_id=option_id)
    if not value.settings:
        value.settings = OptionValueSetting()

    value.sort_order = int_or_other(info.get('sort'))
    value.description.name = info.get('name')
    value.settings.price = float_or_other(info.get('price'))
    value.settings.settings = settings

    db.session.commit()

    # Consumables
    value.settings.consumables = json_dumps_or_other(data.get('products'))

    db.session.commit()

    return ''


@option.route('/<int:option_id>', methods=['POST'])
@login_required
def values_action(option_id):
    """ Действия над значениями опции """
    data = json.loads(request.data) if request.data else {}
    action = data.get('action')
    ids = data.get('ids')

    for value_id in ids:
        value = get_value(value_id)

        # Удалить
        if action == 'delete':

            if value.settings:
                db.session.delete(value.settings)
            if value.products_options:
                for product in value.products_options:
                    db.session.delete(product)
            if value.description:
                db.session.delete(value.description)
            db.session.commit()
            db.session.delete(value)

        # Авто привязка
        elif action == 'auto_compare':
            auto_option_to_products(value)

        # Отвязка
        elif action == 'clean_options':
            for product_option in value.products_options:
                product_clean_options(product_option.product_id)

    db.session.commit()
    return redirect(url_for('.option_values', option_id=option_id))


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


@option.route('/<int:option_id>/change', methods=['POST'])
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


def get_filter_options(value, request):
    filter = {}
    if value.settings and value.settings.settings:
        settings = json.loads(value.settings.settings)
        filter['categories_ids'] = settings.get('categories_ids')
        filter['attribute_id'] = settings.get('attribute_id')
        filter['attribute_values'] = settings.get('attribute_values')
        filter['stock'] = settings.get('stock')

    if request.method == 'POST':
        session_post('manufacturers_ids', request.form.getlist('manufacturers_ids')) 
        session_post('options', request.form.get('options')) 
        session_post('per_page', request.form.get('per_page')) 

    filter['manufacturers_ids'] = session_get('manufacturers_ids')
    filter['options'] = session_get('options')
    filter['per_page'] = session_get('per_page')
    return filter


@option.route('/<int:option_id>/value_products', methods=['GET', 'POST'])
@login_required
def value_products(option_id):
    value_id = request.args.get('value_id')

    value = get_value(value_id)
    filter = get_filter_options(value, request)
    products = get_products(filter=filter)

    attributes = (Attribute.query
        .join(Attribute.description)
        .where(AttributeDescription.name != None)
        .order_by(Attribute.sort_order)).all()

    request_base = Manufacturer.query

    if filter.get('categories_ids'):
        categories_ids = filter.get('categories_ids')
        request_base = (request_base.join(Manufacturer.products)
                    .join(Product.categories)
                   .filter(CategoryDescription.category_id.in_(categories_ids)))
    manufacturers = request_base.order_by(Manufacturer.name).all()

    other_products = other_products_in_option_value(value)

    return render_template('option/value_products.html',
                           products=products,
                           option_id=option_id,
                           value=value,
                           manufacturers=manufacturers,
                           filter=filter,
                           attributes=attributes,
                           other_products=other_products)


@option.route('/<int:option_id>/value_<string:value_id>/products_action', methods=['POST'])
@login_required
def products_action(option_id, value_id):
    """ Действия над товараим в опции """
    value = get_value(value_id)
    settings = json.loads(value.option.settings.text)

    data = json.loads(request.data) if request.data else {}
    action = data.get('action')
    ids = data.get('ids')

    for product_id in ids:

        # Удаление
        if (action == 'delete'):
            product_clean_options(product_id)

        # Принять изменения
        elif action == 'option_to_products':
            manual_option_to_products(product_id, value, settings)

    db.session.commit()

    return redirect(url_for('.value_products',
                            option_id=option_id,
                            value_id=value_id))


@option.route('/options/delete_', methods=['GET'])
@login_required
def option_del():
    options = ProductOption.query.filter(ProductOption.product_option_value == None)
    values = ProductOptionValue.query.filter(ProductOptionValue.product_option_ == None)
    for product_option in options:
        db.session.delete(product_option)
    for product_option_value in values:
        db.session.delete(product_option_value)

    return 'ok'
