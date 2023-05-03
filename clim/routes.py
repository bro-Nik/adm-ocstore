import json
import os
from copy import copy
from flask import render_template, redirect, url_for, request, session, flash
from flask_login import login_required, current_user
from flask_sqlalchemy import query
from requests import delete
from thefuzz import fuzz as f
from datetime import datetime

from clim.app import app, db, redis, celery, login_manager
from clim.models import OtherShops, ProductImage, ProductVariant, RedirectManager, Review, SeoUrl, AttributeDescription, Category, \
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
        if stock == 'in stock on order':
            request_base = request_base.filter(Product.quantity > 0)
        elif stock == 'in stock':
            request_base = request_base.filter((Product.quantity > 0)
                                               & (Product.price != 100001))
        elif stock == 'not in stock':
            request_base = request_base.filter(Product.quantity == 0)
        elif stock == 'on order':
            request_base = request_base.filter(Product.price == 100001)

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
        request_base = (request_base.filter(Product.options != None))
    elif filter.get('options') == 'whithout options':
        request_base = (request_base.filter(Product.options == None))

    if filter.get('other_filter') == 'not_confirmed':
        request_base = (request_base.join(Product.other_shop)
                   .filter((OtherProduct.product_id != None)
                          & (OtherProduct.link_confirmed == None)))

    if filter.get('other_filter') == 'not_matched':
        request_base = (request_base.filter(Product.other_shop == None))

    elif filter.get('other_filter') == 'different_price':
        request_base = (request_base.join(Product.other_shop)
                   .filter((OtherProduct.price != Product.price)
                          & (OtherProduct.link_confirmed != None)
                          & (OtherProduct.price != None)))

    elif filter.get('other_filter') == 'no_options':
        request_base = request_base.filter(Product.options == None)

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


def get_manufacturers():
    return db.session.execute(
        db.select(Manufacturer).order_by(Manufacturer.name)).scalars()


def get_filter(method, path=None):
    if method == 'POST':
        session['categories_ids'] = request.form.getlist('categories_ids')
        session['manufacturers_ids'] = request.form.getlist('manufacturers_ids')
        session['stock'] = request.form.get('stock')
        if path:
            session[path + '_other_filter'] = request.form.get('other_filter')

        session['results_per_page'] = request.form.get('results_per_page')
        session['group_attribute'] = request.form.get('group_attribute')

    filter = {
        'categories_ids': session.get('categories_ids'),
        'manufacturers_ids': session.get('manufacturers_ids'),
        'stock': session.get('stock'),
        'group_attribute': session.get('group_attribute')}

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
        .where(AttributeDescription.name != None)
        .order_by(Attribute.sort_order)).all()

    categories = get_categories()
    manufacturers = get_manufacturers()

    filter = get_filter(request.method, path)
    products = get_products(filter=filter)

    page = ('products/' + path + '.html') if path else 'products/products.html'

    print('group: ', session.get('group_attribute'))
    return render_template(page,
                           products=products,
                           manufacturers=tuple(manufacturers),
                           categories=tuple(categories),
                           other_shops=tuple(other_shops),
                           attributes=attributes)


@app.route('/products/action', methods=['POST'])
@login_required
def products_action():
    action = request.form.get('action')

    count = 1
    products_count = int(request.form.get('products-count'))
    while count <= products_count:
        product_id = request.form.get('product-id-' + str(count))
        if product_id:
            product_id = int(product_id)

            if action == 'delete':
                product_delete(product_id)

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


def product_delete(product_id: int):
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
            date_end=0000-00-00,
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
        .filter(OtherProduct.link_confirmed == None)).scalars())

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
    count = 1
    products_count = int(request.form.get('products-count'))
    while count <= products_count:
        next_checked = request.form.get('other-product-id-' + str(count))
        if next_checked:
            other_product = db.session.execute(
                db.select(OtherProduct)
                .filter_by(other_product_id=int(next_checked))).scalar()
            other_product.link_confirmed = True

            other_compared = (db.session.execute(
                db.select(OtherProduct)
                .filter_by(product_id=other_product.product_id)
                .filter(OtherProduct.shop_id == other_product.shop_id)
                .filter(OtherProduct.other_product_id != other_product.other_product_id))
                .scalars())
            for product in other_compared:
                product.product_id = None
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
            other_product_price = convert_price(product.other_shop[0].price)
            if not other_product_price:
                continue

            if other_product_price > product.price:
                product.price = other_product_price

            elif other_product_price < product.price:
                if product.price / (product.price - other_product_price) > 30:
                    product.price = other_product_price
            continue

        # Несколько цен конкурентов
        prices = {}
        for other_product in product.other_shop:
            other_product_price = convert_price(other_product.price)
            if not other_product_price:
                continue

            if prices.get(other_product_price):
                prices[other_product_price].append(other_product.shop_id)
            else:
                prices[other_product_price] = [other_product.shop_id]
            for price in prices:
                if len(prices[price]) > 1:
                    product.price = price

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
