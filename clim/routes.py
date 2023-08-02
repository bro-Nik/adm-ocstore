import json
import os
from copy import copy
from flask import render_template, redirect, url_for, request, session, flash,\
    send_from_directory
from flask_login import login_required, current_user
from flask_migrate import catch_errors
from flask_sqlalchemy import query
from requests import delete
from sqlalchemy.sql.operators import filter_op
from datetime import datetime, timedelta
from transliterate import slugify
from werkzeug.utils import secure_filename

from clim.app import app, db, redis, celery, login_manager
from clim.general_functions import dict_get_or_other, get_categories, get_module, json_dumps_or_other, json_loads_or_other
from clim.models import Module, OtherShops, ProductImage, ProductSpecial, ProductVariant, RedirectManager, Review, SeoUrl, AttributeDescription, Category, \
    CategoryDescription, Manufacturer, OptionValueDescription, \
    Product, ProductAttribute, ProductOptionValue, Option, OptionValue,\
    OtherProduct, Attribute, SpecialOffer, StockStatus


def product_price_request(product):
    return product.price == 100001


def product_not_in_stock(product):
    return product.quantity < 1


def product_on_order(product):
    return product.quantity == 1


def product_in_stock(product):
    return product.quantity > 1


@app.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    categories = tuple(get_categories())

    result = {}
    # not_in_stock = {}
    # price_request = {}

    for category in tuple(categories):
        if not category.products:
            continue

        result[category.category_id] = {'in_stock': 0,
                                        'on_order': 0,
                                        'price_request': 0,
                                        'not_in_stock': 0}

        for product in category.products:

            if product_in_stock(product):
                result[category.category_id]['in_stock'] += 1
            if product_on_order(product):
                result[category.category_id]['on_order'] += 1
            if product_price_request(product):
                result[category.category_id]['price_request'] += 1
            if product_not_in_stock(product):
                result[category.category_id]['not_in_stock'] += 1

    return render_template('categories.html',
                           categories=categories,
                           result=result
                           )


@app.route('/category_<int:category_id>/settings', methods=['GET', 'POST'])
@login_required
def category_settings(category_id):
    category = db.session.execute(
        db.select(Category).filter(Category.category_id == category_id)).scalar()

    return render_template('category_settings.html', category=category)





def get_consumables():
    """ Получить с расходные материалы """
    settings_in_base = get_module('crm_stock')
    settings = {}
    if settings_in_base.value:
        settings = json.loads(settings_in_base.value)
    ids = settings.get('consumables_categories_ids')

    request_base = Product.query

    request_base = (request_base.join(Product.categories)
                   .where(Category.category_id.in_(ids)))

    request_base = request_base.order_by(Product.mpn)

    return request_base.all()




def get_manufacturers(filter={}):
    request_base = Manufacturer.query.order_by(Manufacturer.name)

    if filter.get('stock'):
        stock = filter.get('stock')
        if stock == 'in stock on order':
            request_base = (request_base
                .join(Manufacturer.products).filter(Product.quantity > 0))
        elif stock == 'in stock':
            request_base = (request_base
                .join(Manufacturer.products).filter((Product.quantity > 0)
                                               & (Product.price != 100001)))
        elif stock == 'not in stock':
            request_base = (request_base
                .join(Manufacturer.products).filter(Product.quantity == 0))
        elif stock == 'on order':
            request_base = (request_base
                .join(Manufacturer.products).filter(Product.price == 100001))

    if filter.get('categories_ids'):
        categories_ids = filter.get('categories_ids')
        request_base = (request_base.join(Manufacturer.products)
                .join(Product.categories)
                .filter(Category.category_id.in_(categories_ids)))

    return request_base.all()










@app.route('/products/prices/settings_apply', methods=['POST'])
@login_required
def products_prices_settings_apply():
    settings_in_base, settings = get_products_prices_settings()

    fields = ['special_offer_id',
              'stiker_text',
              'price_delta']
    for field in fields:
        if request.form.get(field):
            settings[field] = request.form.get(field)

    if request.form.getlist('options_ids'):
        settings['options_ids'] = request.form.getlist('options_ids')

    if settings:
        if settings_in_base:
            settings_in_base.value = json.dumps(settings)
        else:
            products_prices_settings = Module(
                name='products_prices',
                value=json.dumps(settings)
            )
            db.session.add(products_prices_settings)

        db.session.commit()

    return redirect(url_for('products_prices_settings'))


@app.route('/del_not_confirm_products', methods=['GET', 'POST'])
@login_required
def del_not_confirm_products():

    other_products = tuple(db.session.execute(db.select(OtherProduct)).scalars())
    for other_product in other_products:
        if not other_product.link_confirmed and other_product.product_id:
            other_product.product_id = 0
    db.session.commit()

    page = request.args.get('page')
    return redirect(url_for('products', path='comparison', page=page))



# @app.route('/settings', methods=['GET', 'POST'])
# @login_required
# def settings():
#     settings_in_base = db.session.execute(db.select(Setting)).scalars()
#
#     def get_setting(name):
#         for setting in settings_in_base:
#             if setting.name == name:
#                 return setting
#         else:
#             return None
#
#     if request.method == 'POST':
#
#         new_settings = {}
#
#         new_settings['catalog'] = None
#         settings_list = {
#             'image_path': request.form.get('image_path'),
#             'download_path': request.form.get('download_path')
#             }
#         for setting in settings_list:
#             if settings_list[setting]:
#                 new_settings['catalog'] = json.dumps(settings_list)
#                 break
#
#         for new_setting_name in new_settings:
#             setting_in_base = get_setting(new_setting_name)
#             if setting_in_base:
#                 setting_in_base.value = new_settings.get(new_setting_name)
#             else:
#                 new_setting = Setting(name=new_setting_name,
#                                       value=new_settings.get(new_setting_name))
#                 db.session.add(new_setting)
#         db.session.commit()
#
#
#
#     return render_template('settings.html', settings=settings_in_base)

@app.route('/work_plan_fields', methods=['POST'])
@login_required
def work_plan_fields():
    data = json_loads_or_other(request.data, {})

    module = get_module('work_plan')
    if not module:
        module = Module(name='work_plan')
        db.session.add(module)

    module_data = json_loads_or_other(module.value, {})
    fields = dict_get_or_other(module_data, 'fields', [])

    def new_id():
        id = 1
        for field in fields:
            if field['id'] >= id:
                id = field['id'] + 1
        return id

    for item in data:
        if not item.get('name'):
            continue

        # delete
        if item['name'] == 'Удалить':
            for field in fields:
                if field['id'] == item['id']:
                    fields.remove(field)
                    break
            for category in module_data:
                if category == 'fields':
                    continue
                for manufacturer in module_data[category]:
                    id = str(item['id'])
                    if not id in module_data[category][manufacturer]:
                        continue
                    module_data[category][manufacturer].remove(id)

        # new
        if not item.get('id'):
            fields.append(
                {'id': new_id(),
                 'name': item['name']}
            )

        # update
        else:
            for field in fields:
                if field['id'] == item['id']:
                    field['name'] = item['name']
                    break

    module_data['fields'] = fields
    module.value = json_dumps_or_other(module_data)
    db.session.commit()
    return redirect(url_for('work_plan'))

@app.route('/work_plan', methods=['GET', 'POST'])
@login_required
def work_plan():
    manufacturers_ids = request.form.getlist('manufacturers_ids')

    category_id = request.form.get('category_id')
    category = db.select(Category)
    if category_id:
        category = category.filter_by(category_id=category_id)
    category = db.session.execute(category).scalar()

    module = get_module('work_plan')
    module_data = json_loads_or_other(module.value, {}) if module else {}
    fields = dict_get_or_other(module_data, 'fields', {})
    work_plan = dict_get_or_other(module_data, str(category.category_id), {})

    request_base = (Manufacturer.query.join(Manufacturer.products)
        .join(Product.categories)
        .where(Category.category_id == category.category_id))
    manufacturers = request_base.order_by(Manufacturer.name).all()

    return render_template('work_plan.html',
                           work_plan=work_plan,
                           category=category,
                           manufacturers_ids=manufacturers_ids,
                           manufacturers=tuple(manufacturers),
                           fields=fields)


@app.route('/work_plan_<string:category_id>_update', methods=['POST'])
@login_required
def work_plan_update(category_id):
    module = get_module('work_plan')
    if not module:
        module = Module(name='work_plan')
        db.session.add(module)

    module_data = json_loads_or_other(module.value, {})

    if not module_data.get(category_id):
        module_data[category_id] = {}

    data = json_loads_or_other(request.data, {})
    action = data.get('action')

    if action == 'save':
        fields = data.get('ids')
        for field_list in fields:
            field_list = field_list.split('--')
            manufacturer = field_list[0]
            field = field_list[1]

            if not module_data[category_id].get(manufacturer):
                module_data[category_id][manufacturer] = []

            module_data[category_id][manufacturer].append(field)

    elif action == 'clean':
        module_data.pop(category_id, None)

    module.value = json_dumps_or_other(module_data)
    db.session.commit()

    return redirect(url_for('work_plan'))


@app.route('/new_stock', methods=['GET'])
@login_required
def new_stock():
    products = db.session.execute(db.select(Product)).scalars()

    for product in products:
        if product.quantity == 1:
            product.stock_status_id = 8

        if product.quantity > 1:
            product.stock_status_id = 7

    db.session.commit()

    return redirect(url_for('work_plan'))


@app.route('/stock_statuses', methods=['GET'])
@login_required
def stock_statuses():
    stock_statuses = db.session.execute(db.select(StockStatus)).scalars()

    settings_in_base = db.session.execute(
        db.select(Module).filter_by(name='stock_statuses')).scalar()
    settings = {}
    if settings_in_base:
        settings = json.loads(settings_in_base.value)

    return render_template('stock_statuses.html',
                           stock_statuses=stock_statuses,
                           settings=settings)


@app.route('/stock_statuses_action', methods=['POST'])
@login_required
def stock_statuses_action():
    settings_in_base = db.session.execute(
        db.select(Module).filter_by(name='stock_statuses')).scalar()

    settings = {}
    if settings_in_base:
        settings = json.loads(settings_in_base.value)

    statuses_count = request.form.get('statuses-count')

    count = 1

    while count <= int(statuses_count):
        status_id = request.form.get('status-' + str(count))
        action = request.form.get('action-' + str(count))
        if not action:
            count += 1
            continue

        if action == 'delete':
            stock_status = db.session.execute(
                db.select(StockStatus)
                .filter_by(stock_status_id=int(status_id))).scalar()
            db.session.delete(stock_status)

        else:
            settings[status_id] = action

        count += 1

    if settings:
        if settings_in_base:
            settings_in_base.value = json.dumps(settings)
        else:
            new_status = Module(name='stock_statuses',
                                value=json.dumps(settings))
            db.session.add(new_status)
    db.session.commit()

    return redirect(url_for('stock_statuses'))


@app.route('/new_products', methods=['GET'])
@login_required
def new_products():
    other_shops = tuple(db.session.execute(db.select(OtherShops)).scalars())

    products = db.session.execute(
        db.select(Product).filter_by(date_added=0)).scalars()

    return render_template('products/new.html', products=products,
                           other_shops=other_shops)


@app.route('/new_products_comp', methods=['GET'])
@login_required
def new_products_comp():
    products = db.session.execute(
        db.select(Product).filter_by(date_added=0)).scalars()
    filter = {'products_ids': []}
    for product in products:
        filter['products_ids'].append(product.product_id)

    print(filter)
    comparison_products.delay(filter)
    return redirect(url_for('new_products'))


@app.route('/new_products', methods=['POST'])
@login_required
def new_products_post():
    products_count = request.form.get('products-count')

    count = 1

    while count <= int(products_count):
        name = request.form.get('name-' + str(count))
        if not name:
            count += 1
            continue

        new_product = Product(
            mpn=name,
            model='',
            sku='',
            upc='',
            location='',
            ean='',
            price=0,
            tax_class_id=0,
            manufacturer_id=0,
            isbn='',
            jan='',
            quantity=0,
            viewed=0,
            date_added=0,
            date_modified=0,
            cost=0,
            suppler_code=1,
            suppler_type=0,
            stock_status_id=0

        )
        db.session.add(new_product)

        count += 1
    db.session.commit()
    return 'OK'




