import json
from flask import render_template, redirect, url_for, request
from flask_login import login_required
from clim.main.routes import get_list_all_categories

from clim.models import db, Attribute, AttributeDescription, Manufacturer, \
    Option, OptionDescription, OptionSetting, OptionValueSetting, OptionValue, \
    OptionValueDescription, ProductAttribute, ProductOption, \
    ProductOptionValue, Product, CategoryDescription, Category
from .utils import float_or_other, get_filter_options, get_option, \
    get_products, get_value, int_or_other, \
    other_products_in_option_value
from clim.utils import DiscountProducts, actions_in, json_dumps
from . import bp


@bp.route('/options', methods=['GET', 'POST'])
@login_required
def options():
    """ Страница опций """
    if request.method == 'POST':
        # Действия
        actions_in(request.data, get_option)
        db.session.commit()
        return ''

    options = db.session.execute(db.select(Option)).scalars()
    return render_template('option/options.html', options=options)


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def option_settings():
    """ Добавить или изменить опцию """
    option = get_option(request.args.get('option_id'))

    if request.method == 'POST':
        if not option:
            option = Option(opt_image=0)
            option.description = OptionDescription(language_id=1)
            db.session.add(option)

        data = json.loads(request.data) if request.data else {}
        option.description.name = data.get('name') or 'Без имени'
        option.sort_order = data.get('sort') or 0
        option.type = data.get('type')

        settings = {'quantity': data.get('quantity', ''),
                    'subtract': data.get('subtract', ''),
                    'price_prefix': data.get('price-prefix', '')}

        if not option.settings:
            option.settings = OptionSetting()
        option.settings.text = json.dumps(settings)

        db.session.commit()
        return {'redirect': url_for('.option_settings', option_id=option.option_id)}

    return render_template('option/option_settings.html', option=option)


@bp.route('/<int:option_id>/values', methods=['GET', 'POST'])
@login_required
def option_values(option_id):
    """ Варианты опции """
    if request.method == 'POST':
        # Действия
        actions_in(request.data, get_value)
        db.session.commit()
        return ''

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


@bp.route('/<int:option_id>/option_value_settings', methods=['GET', 'POST'])
@login_required
def value_settings(option_id):
    """ Добавить или изменить вариант опции """
    value = get_value(request.args.get('value_id'))
    settings = attribute = {}

    if value and value.settings and value.settings.settings:
        settings = json.loads(value.settings.settings)
        attribute = db.session.execute(
            db.select(Attribute)
            .filter_by(attribute_id=settings.get('attribute_id'))).scalar()

    if request.method == 'POST':
        if not value:
            value = OptionValue(option_id=option_id)
            db.session.add(value)

        if not value.description:
            value.description = OptionValueDescription(language_id=1,
                                                       option_id=option_id)
        if not value.settings:
            value.settings = OptionValueSetting()

        data = json.loads(request.data) if request.data else {}

        settings = {'categories_ids': data.get('categories_ids') or [],
                    'attribute_id': data.get('attribute_id'),
                    'attribute_values': data.get('attribute_values') or [],
                    'stock': data.get('stock')}

        value.sort_order = int_or_other(data.get('sort'))
        value.description.name = data.get('name', '')
        value.settings.price = float_or_other(data.get('price'))
        value.settings.settings = json.dumps(settings)

        # Consumables
        value.settings.consumables = json_dumps(data.get('products'))

        db.session.commit()
        return {'redirect': url_for('.value_settings', option_id=option_id,
                                    value_id=value.option_value_id)}

    return render_template('option/value_settings.html',
                           option_id=option_id,
                           value=value,
                           settings=settings,
                           categories=get_list_all_categories(),
                           attribute=attribute)


@bp.route('/<int:option_id>/value_products', methods=['GET', 'POST'])
@login_required
def value_products(option_id):
    value = get_value(request.args.get('value_id'))
    filter_by = get_filter_options(value, request)
    products = get_products(filter=filter_by)

    attributes = db.session.execute(
        db.select(Attribute)
        .join(Attribute.description).filter(AttributeDescription.name != None)
        .order_by(Attribute.sort_order)
    ).scalars()

    manufacturers = db.select(Manufacturer)

    if filter_by.get('categories_ids'):
        categories_ids = filter_by.get('categories_ids')
        manufacturers = (manufacturers.join(Manufacturer.products)
                         .join(Product.categories)
                         .filter(CategoryDescription.category_id.in_(categories_ids)))
    manufacturers = db.session.execute(
        manufacturers.order_by(Manufacturer.name)).scalars()

    other_products = other_products_in_option_value(value)

    return render_template('option/value_products.html',
                           products=products,
                           option_id=option_id,
                           value=value,
                           manufacturers=manufacturers,
                           filter=filter_by,
                           attributes=attributes,
                           other_products=other_products)


@bp.route('/<int:option_id>/value_<string:value_id>/products_action', methods=['POST'])
@login_required
def products_action(option_id, value_id):
    """ Действия над товараим в опции """
    value = get_value(value_id)
    settings = json.loads(value.option.settings.text)

    data = json.loads(request.data) if request.data else {}
    action = data.get('action')
    ids = data.get('ids')

    for product_id in ids:
        pass

        # # Удаление
        # if (action == 'delete'):
        #     product_clean_options(product_id)
        #
        # # Принять изменения
        # elif action == 'option_to_products':
        #     manual_option_to_products(product_id, value, settings)

    db.session.commit()

    return redirect(url_for('.value_products',
                            option_id=option_id,
                            value_id=value_id))


@bp.route('/ajax_attribute_values', methods=['GET'])
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


@bp.route('/<int:option_id>/change', methods=['POST'])
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

    discount_products_ids = DiscountProducts().get()

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
