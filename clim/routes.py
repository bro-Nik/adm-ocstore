import json
import os
from copy import copy
from flask import render_template, redirect, url_for, request, session, flash
from flask_login import login_required, current_user
from flask_migrate import catch_errors
from flask_sqlalchemy import query
from requests import delete
from thefuzz import fuzz as f
from datetime import datetime, timedelta
from transliterate import slugify

from clim.app import app, db, redis, celery, login_manager
from clim.models import Module, OtherShops, ProductImage, ProductVariant, RedirectManager, Review, SeoUrl, AttributeDescription, Category, \
    CategoryDescription, Manufacturer, OptionValueDescription, \
    Product, ProductAttribute, ProductOptionValue, Option, OptionValue,\
    OtherProduct, Attribute, product_to_category


@app.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    categories = tuple(db.session.execute(
        db.select(Category).order_by(Category.sort_order)).scalars())

    not_in_stock = {}
    price_request = {}

    for category in tuple(categories):
        if not category.description.products:
            continue

        not_in_stock[category.category_id] = []
        price_request[category.category_id] = []

        for product in category.description.products:
            if product.quantity == 0:
                not_in_stock[category.category_id].append(product.product_id)
            if product.price == 100001:
                price_request[category.category_id].append(product.product_id)

    return render_template('categories.html',
                           categories=tuple(categories),
                           price_request=price_request,
                           not_in_stock=not_in_stock
                           )


def get_discount_products():
    # Получем метки
    label = db.session.execute(
        db.select(AttributeDescription).filter_by(name='Метка')).scalar()
    attributes = db.session.execute(
            db.select(ProductAttribute)
            .filter_by(attribute_id=label.attribute_id)).scalars()

    # Отделяем акционные товары
    discount_product_ids = []
    for attribute in attributes:
        if 'Спецпредложение' in attribute.text:
            discount_product_ids.append(attribute.product_id)
    return discount_product_ids


def get_product(product_id: int):
    return db.session.execute(
        db.select(Product).filter_by(product_id=product_id)).scalar()


def get_other_product(product_id: int):
    return db.session.execute(
        db.select(OtherProduct).filter_by(other_product_id=product_id)).scalar()


def get_products(pagination=True, filter={}):
    """ Получить с фильром """

    request_base = Product.query

    if filter.get('group_attribute'):
        group_attribute = int(filter.get('group_attribute'))
        request_base = (request_base.join(Product.attributes)
            .where(ProductAttribute.attribute_id == group_attribute)
            .order_by(ProductAttribute.text))

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

    if filter.get('field'):
        field = filter.get('field')
        if field == 'ean':
            request_base = request_base.filter(Product.ean != '')
        elif field == 'jan':
            request_base = request_base.filter(Product.jan != '')
        elif field == 'isbn':
            request_base = request_base.filter(Product.isbn != '')

    if filter.get('manufacturers_ids'):
        manufacturers_ids = filter.get('manufacturers_ids')
        request_base = request_base.where(Product.manufacturer_id.in_(manufacturers_ids))

    if filter.get('categories_ids'):
        categories_ids = filter.get('categories_ids')
        request_base = (request_base.join(Product.categories)
                   .filter(CategoryDescription.category_id.in_(categories_ids)))

    if filter.get('attribute_id'):
        attribute_id = filter.get('attribute_id')
        attribute_values = filter.get('attribute_values')
        request_base = (request_base.join(Product.attributes)
                    .where((ProductAttribute.attribute_id == attribute_id)
                           & (ProductAttribute.text.in_(attribute_values)))
                    .order_by(ProductAttribute.text))

    if filter.get('option_value_id'):
        request_base = (request_base.join(Product.options)
                   .filter(ProductOptionValue.option_value_id == filter.get('option_value_id')))

    if filter.get('options') == 'whith options':
        request_base = (request_base.filter(Product.options is not None))
    elif filter.get('options') == 'whithout options':
        request_base = (request_base.filter(Product.options is None))

    if filter.get('other_filter') == 'not_confirmed':
        request_base = (request_base.join(Product.other_shop)
                        .filter((OtherProduct.product_id is not None)
                                & (OtherProduct.link_confirmed is None)))

    if filter.get('other_filter') == 'not_matched':
        request_base = (request_base.filter(Product.other_shop is None))

    elif filter.get('other_filter') == 'different_price':
        request_base = (request_base.join(Product.other_shop)
                        .filter((OtherProduct.price != Product.price)
                                & (OtherProduct.link_confirmed is not None)
                                & (OtherProduct.price is not None)))

    elif filter.get('other_filter') == 'no_options':
        request_base = request_base.filter(Product.options is None)

    if filter.get('sort') == 'viewed':
        request_base = request_base.order_by(Product.viewed.desc())
    else:
        request_base = request_base.order_by(Product.mpn)

    if pagination:
        results_per_page = session.get('results_per_page')
        if results_per_page:
            results_per_page = int(results_per_page)
        page = request.args.get('page')
        page = int(page) if page else 1
        return request_base.paginate(page=page,
                                     per_page=results_per_page,
                                     error_out=False)

    return request_base.all()


def get_categories():
    return db.session.execute(
        db.select(Category).order_by(Category.sort_order)).scalars()


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
                .filter(CategoryDescription.category_id.in_(categories_ids)))

    return request_base.all()


def get_filter(method, path=None):
    if method == 'POST':
        session['categories_ids'] = request.form.getlist('categories_ids')
        session['manufacturers_ids'] = request.form.getlist('manufacturers_ids')
        session['stock'] = request.form.get('stock')
        session['field'] = request.form.get('field')
        if path:
            session[path + '_other_filter'] = request.form.get('other_filter')

        session['results_per_page'] = request.form.get('results_per_page')
        session['group_attribute'] = request.form.get('group_attribute')

    filter = {
        'categories_ids': session.get('categories_ids'),
        'manufacturers_ids': session.get('manufacturers_ids'),
        'stock': session.get('stock'),
        'field': session.get('field'),
        'group_attribute': session.get('group_attribute')
    }

    if path:
        filter['other_filter'] = session.get(path + '_other_filter')
    return filter


@app.route('/products', methods=['GET', 'POST'])
@app.route('/products/<string:path>', methods=['GET', 'POST'])
@login_required
def products(path=None):
    other_shops = db.session.execute(db.select(OtherShops)).scalars()

    attributes = (Attribute.query
        .join(Attribute.description)
        .where(AttributeDescription.name is not None)
        .order_by(Attribute.sort_order)).all()

    filter = get_filter(request.method, path)

    categories = get_categories()
    manufacturers = get_manufacturers(filter)

    products = get_products(filter=filter)

    page = ('products/' + path + '.html') if path else 'products/products.html'

    return render_template(page,
                           products=products,
                           manufacturers=tuple(manufacturers),
                           categories=tuple(categories),
                           other_shops=tuple(other_shops),
                           attributes=attributes)


@app.route('/products/action', methods=['POST'])
@login_required
def products_action():
    action = str(request.form.get('action'))

    count = 1
    products_count = int(request.form.get('products-count'))
    while count <= products_count:
        product_id = request.form.get('product-id-' + str(count))
        if product_id:
            product_id = int(product_id)

            if 'delete_' in action:
                product_delete(product_id, action.replace('delete_', ''))
            elif 'clean_field_' in action:
                clean_field(product_id, action.replace('clean_field_', ''))
            elif 'stock_status_' in action:
                update_stock_status(product_id, action.replace('stock_status_', ''))

        count += 1

    page = request.args.get('page')
    return redirect(url_for('products', page=page))


def get_url(category_id=None, product_id=None):
    if category_id:
        filter = 'category_id='+str(category_id)

    elif product_id:
        filter = 'product_id='+str(product_id)

    else:
        return None

    return db.session.execute(db.select(SeoUrl).filter_by(query=filter)).scalar()


def clean_field(product_id: int, whan_clean: str):
    product = get_product(product_id)

    if whan_clean == 'ean':
        product.ean = ''
    elif whan_clean == 'isbn':
        product.isbn = ''
    elif whan_clean == 'jan':
        product.jan = ''
    db.session.commit()


def update_stock_status(product_id: int, status: str):
    product = get_product(product_id)

    if status == 'in_stock':
        product.quantity = 10
    elif status == 'on_order':
        product.quantity = 1
    elif status == 'price_request':
        product.price = 100001
    elif status == 'not_in_stock':
        product.quantity = 0

    db.session.commit()


def product_delete(product_id: int, action: str):
    """ Удаление товара и все, что с ним связано """
    image_path = app.config['IMAGE_PATH']
    download_path = app.config['DOWNLOAD_PATH']

    old_url = new_url = None

    product = get_product(product_id)

    # Seo url
    product_url = get_url(product_id=product_id)
    if product_url:
        old_url = app.config['CATALOG_DOMAIN'] + product_url.keyword
        db.session.delete(product_url)

    # Добавляем редирект
    if action == 'redirect':

        main_category = db.session.execute(
            db.select(product_to_category)
            .filter_by(product_id=product_id, main_category=1)).one()

        main_category_url = get_url(category_id=main_category.category_id)

        if main_category_url:
            new_url = app.config['CATALOG_DOMAIN'] + main_category_url.keyword

        if old_url and new_url:
            redirect = RedirectManager(
                active=1,
                from_url=old_url,
                to_url=new_url,
                response_code=301,
                date_start=datetime.now().date(),
                date_end=datetime.now().date() + timedelta(days=3652),
                times_used=0
            )
            db.session.add(redirect)
            db.session.commit()

    if product.description:
        db.session.delete(product.description)

    if product.image and os.path.isfile(image_path + product.image):
        os.remove(image_path + product.image)
    if product.images:
        for image in product.images:
            other_images = db.session.execute(
                db.select(ProductImage).filter(
                    (ProductImage.product_id != product.product_id)
                    & (ProductImage.image == image.image))).scalar()
            if not other_images and os.path.isfile(image_path + image.image):
                os.remove(image_path + image.image)

            db.session.delete(image)

    if product.categories:
        for category in product.categories:
            category.products.remove(product)
            db.session.commit()

    if product.related_products:
        for related_product in product.related_products:
            db.session.delete(related_product)

    if product.attributes:
        for attribute in product.attributes:
            db.session.delete(attribute)
        db.session.commit()

    if product.options:
        for option in product.options:
            if option.product_option_value:
                db.session.delete(option.product_option_value)
            db.session.delete(option)

    if product.other_shop:
        for other_product in product.other_shop:
            other_product.link_confirmed = None
            other_product.product_id = 0

    product_variants = (ProductVariant.query
                        .filter_by(product_id=product.product_id)).all()
    if product_variants:
        for variant in product_variants:
            db.session.delete(variant)
    variants_in_products = ProductVariant.query.all()
    if variants_in_products:
        for variant in variants_in_products:
            ids = variant.prodvar_product_str_id.split(',')
            id = str(product.product_id)
            if id in ids:
                ids.remove(id)
                variant.prodvar_product_str_id = ','.join(ids)

    reviews = Review.query.filter(Review.product_id == product.product_id).all()
    if reviews:
        for review in reviews:
            db.session.delete(review)

    if product.downloads:
        for download in product.downloads:

            if len(download.products) == 1:
                if os.path.isfile(download_path + download.filename):
                    os.remove(download_path + download.filename)

                if download.description:
                    db.session.delete(download.description)

                db.session.delete(download)
            else:
                download.products.remove(product)

    db.session.delete(product)
    db.session.commit()



@app.route('/comparison_products', methods=['POST'])
@login_required
def start_comparison_products():
    """ Запуск подбира похожих товаров """
    all_products = request.form.get('all_products')

    if all_products:
        filter = {}
    else:
        filter = get_filter(request.method, path='comparison')

    comparison_products.delay(filter)

    return redirect(url_for('products', path='comparison'))


@celery.task()
def comparison_products(filter):
    """ Подбирает похожие товары """
    products = get_products(pagination=False, filter=filter)

    other_products = tuple(db.session.execute(
        db.select(OtherProduct)
        .filter(OtherProduct.link_confirmed is None)).scalars())

    def matching_set(matching, product, other_product):
        id = other_product.other_product_id
        matching_list[id] = {'product_id': product.product_id,
                             'matching': matching,
                             'shop_id': other_product.shop_id}

    matching_list = {}

    for product in products:
        shops_ids = []
        if product.other_shop:
            for comp_product in product.other_shop:
                if comp_product.link_confirmed:
                    shops_ids.append(comp_product.shop_id)

        product_name = product.mpn.lower()

        for other_product in other_products:

            if other_product.shop_id in shops_ids:
                continue

            other_product_name = other_product.name.lower()

            matching = f.ratio(product_name, other_product_name)
            if matching < 60:
                continue

            if not matching_list.get(other_product.other_product_id):
                matching_set(matching, product, other_product)

            elif (matching
                  > matching_list[other_product.other_product_id]['matching']):
                matching_set(matching, product, other_product)

    for x_id in list(matching_list.items()):
        for y_id in list(matching_list.items()):
            if x_id[0] == y_id[0]:
                continue

            if (x_id[1]['product_id'] == y_id[1]['product_id']
                    and x_id[1]['matching'] > y_id[1]['matching']
                    and x_id[1]['shop_id'] == y_id[1]['shop_id']):
                matching_list.pop(y_id[0])

    for other_product in other_products:
        if matching_list.get(other_product.other_product_id):
            other_product.product_id = \
                matching_list[other_product.other_product_id]['product_id']

    db.session.commit()
    print('End')


@app.route('/confirm_product_to_product', methods=['POST'])
@login_required
def confirm_product_to_product():
    """ Привязка или отвязка товара конкурента """
    action = request.form.get('action')

    count = 1
    products_count = int(request.form.get('products-count'))
    while count <= products_count:
        product_id = request.form.get('other-product-id-' + str(count))

        if not product_id:
            count += 1
            continue

        other_product = get_other_product(int(product_id))

        if action == 'bind':
            other_product.link_confirmed = True

            other_compared = (db.session.execute(
                db.select(OtherProduct)
                .filter_by(product_id=other_product.product_id)
                .filter(OtherProduct.shop_id == other_product.shop_id)
                .filter(OtherProduct.other_product_id != other_product.other_product_id))
                .scalars())
            for product in other_compared:
                product.product_id = None

        elif action == 'unbind':
            other_product.link_confirmed = None
            other_product.product_id = 0

        count += 1
    db.session.commit()

    page = request.args.get('page')
    return redirect(url_for('products', path='comparison', page=page))


@app.route('/confirm_prices', methods=['POST'])
@login_required
def confirm_prices():
    count = 1
    products_count = request.form.get('products-count')
    products_count = int(products_count)

    discount_products = get_discount_products()

    while count <= products_count:
        next_checked = request.form.get('product-id-' + str(count))
        if next_checked:
            product = get_product(int(next_checked))

            price = request.form.get('price-' + str(count))
            if not price:
                count += 1
                continue

            product.price = float(price)
            product.quantity = 10
            if product.product_id in discount_products:
                for option in product.options:
                    if option.option_id == 24:
                        price = option.product_option_value.price + product.price
                        product.ean = 'С устаовкой ' + str(price) + ' р.'

        count += 1
    db.session.commit()

    page = request.args.get('page')
    return redirect(url_for('products', path='prices', page=page))


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


@app.route('/products/change_prices', methods=['GET'])
@login_required
def start_change_prices():
    change_prices.delay()
    page = request.args.get('page')
    return redirect(url_for('products', path='prices', page=page))


@celery.task()
def change_prices():
    delta = 0.3
    products = tuple(db.session.execute(db.select(Product)).scalars())

    def convert_price(price):
        try:
            price = float(price)
        except:
            price = 0
        return price

    for product in products:
        if not product.other_shop:
            continue

        # Одна цена конкурента
        if len(product.other_shop) < 2:
            other_price = convert_price(product.other_shop[0].price)
            if not other_price:
                continue

            if (other_price > product.price
                    or other_price >= product.price - (product.price * delta)):
                product.price = other_price
                product.quantity = 10

            continue

        # Несколько цен конкурентов
        prices = []
        for other_product in product.other_shop:
            other_price = convert_price(other_product.price)
            if other_price:
                prices.append(other_price)

        if product.price in prices:
            continue

        for other_price in sorted(prices):
            if abs(product.price - other_price) <= product.price * delta:
                product.price = other_price
                product.quantity = 10
                break

    db.session.commit()
    print('End')


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


@app.route('/work_plan', methods=['GET', 'POST'])
@login_required
def work_plan():
    categories = get_categories()

    manufacturers_ids = request.form.getlist('manufacturers_ids')

    category_id = request.form.get('category_id')
    category_id = int(category_id) if category_id else 11900283

    category = db.session.execute(
        db.select(Category).filter_by(category_id=category_id)).scalar()

    work_plan = db.session.execute(
        db.select(Module).filter_by(name='work_plan')).scalar()

    if work_plan:
        work_plan = json.loads(work_plan.value)
        work_plan = work_plan.get(str(category_id))
    else:
        work_plan = {}

    manufacturers = []
    all_manufacturers = []

    for product in category.description.products:
        if not product.manufacturer:
            continue

        if not product.manufacturer.name in all_manufacturers:
            all_manufacturers.append(product.manufacturer.name)

    if manufacturers_ids:
        manufacturers = manufacturers_ids
    else:
        manufacturers = all_manufacturers

    return render_template('work_plan.html',
                           work_plan=work_plan,
                           categories=tuple(categories),
                           category_id=category_id,
                           manufacturers_ids=manufacturers_ids,
                           manufacturers=manufacturers,
                           all_manufacturers=all_manufacturers)


@app.route('/work_plan_<int:category_id>_update', methods=['POST'])
@login_required
def work_plan_update(category_id):
    plan_in_base = db.session.execute(
        db.select(Module).filter_by(name='work_plan')).scalar()

    all_plans = {}
    new_plan = {}

    if plan_in_base:
        all_plans = json.loads(plan_in_base.value)

    manufacturers_count = request.form.get('manufacturers-count')
    count = 1

    while count <= int(manufacturers_count):
        manufacturer = request.form.get('manufacturer-' + str(count))

        if not new_plan.get(manufacturer):
            new_plan[manufacturer] = {}

        new_plan[manufacturer]['models'] = request.form.get('models-' + str(count))
        new_plan[manufacturer]['prices'] = request.form.get('prices-' + str(count))
        new_plan[manufacturer]['stock'] = request.form.get('stock-' + str(count))

        count += 1

    all_plans[category_id] = new_plan

    if plan_in_base:
        plan_in_base.value = json.dumps(all_plans)
    else:
        new_plan = Module(name='work_plan',
                          value=json.dumps(all_plans))
        db.session.add(new_plan)

    db.session.commit()
    return redirect(url_for('work_plan'))
