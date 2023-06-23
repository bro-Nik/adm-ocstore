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
from thefuzz import fuzz as f
from datetime import datetime, timedelta
from transliterate import slugify
from werkzeug.utils import secure_filename

from clim.app import app, db, redis, celery, login_manager
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


def get_consumables():
    """ Получить с расходные материалы """

    request_base = Product.query

    request_base = (request_base.join(Product.categories)
               .filter(Category.category_id == 11900348))

    request_base = request_base.order_by(Product.mpn)

    return request_base.all()


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
                   .filter(Category.category_id.in_(categories_ids)))

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

    if filter.get('products_ids'):
        ids = filter.get('products_ids')
        request_base = request_base.filter(Product.product_id.in_(ids))

    if filter.get('new_products'):
        request_base = request_base.filter(Product.date_added == 0)

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


def get_stock_statuses():
    return db.session.execute(
        db.select(StockStatus).filter_by(language_id=1)).scalars()


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


def get_filter(method=None, path=None):
    if method == 'POST':
        session['categories_ids'] = request.form.getlist('categories_ids')
        session['manufacturers_ids'] = request.form.getlist('manufacturers_ids')
        session['stock'] = request.form.get('stock')
        session['field'] = request.form.get('field')
        session['new_products'] = request.form.get('new_products')
        if path:
            session[path + '_other_filter'] = request.form.get('other_filter')

        session['results_per_page'] = request.form.get('results_per_page')
        session['group_attribute'] = request.form.get('group_attribute')

    filter = {
        'categories_ids': session.get('categories_ids'),
        'manufacturers_ids': session.get('manufacturers_ids'),
        'stock': session.get('stock'),
        'field': session.get('field'),
        'group_attribute': session.get('group_attribute'),
        'new_products': session['new_products']
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
    stock_statuses = get_stock_statuses()

    products = get_products(filter=filter)

    attributes_in_products = []
    for product in products:
        for attribute in product.attributes:
            if attribute.main_attribute.description.name not in attributes_in_products:
                attributes_in_products.append(attribute.main_attribute.description.name)


    page = ('products/' + path + '.html') if path else 'products/products.html'

    return render_template(page,
                           products=products,
                           manufacturers=tuple(manufacturers),
                           categories=tuple(categories),
                           stock_statuses=stock_statuses,
                           other_shops=tuple(other_shops),
                           attributes=tuple(attributes),
                           attributes_in_products=attributes_in_products)


@app.route('/products/action', methods=['POST'])
@login_required
def products_action():
    action = str(request.form.get('action'))
    other = request.form.get('other')

    count = 1
    products_count = int(request.form.get('products-count'))
    while count <= products_count:
        product_id = request.form.get('product-id-' + str(count))
        if product_id:
            product_id = int(product_id)

            if 'delete_' in action:
                product_delete(product_id, action.replace('delete_', ''), other)
            elif 'clean_field_' in action:
                clean_field(product_id, action.replace('clean_field_', ''))
            elif 'stock_status_' in action:
                update_stock_status(product_id, action.replace('stock_status_', ''))
            elif action == 'prodvar_update':
                try:
                    ids
                except NameError:
                    ids = []

                if product_id not in ids:
                    ids = update_product_variants(product_id)

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

    if status == 'price_request':
        product.price = 100001
        product.quantity = 1
    else:
        settings_in_base = db.session.execute(
            db.select(Module).filter_by(name='stock_statuses')).scalar()

        settings = {}
        if settings_in_base:
            settings = json.loads(settings_in_base.value)

        status_type = settings.get(str(status))

        product.stock_status_id = int(status)

        if status_type == 'В наличии':
            product.quantity = 10
        elif status_type == 'Под заказ':
            product.quantity = 1
        elif status_type == 'Нет в наличии':
            product.quantity = 0

    db.session.commit()


def product_delete(product_id: int, action: str, redirect_to):
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
    if action == 'redirect_to_category':

        main_category = db.session.execute(
            db.select(product_to_category)
            .filter_by(product_id=product_id, main_category=1)).one()

        main_category_url = get_url(category_id=main_category.category_id)

        if main_category_url:
            new_url = app.config['CATALOG_DOMAIN'] + main_category_url.keyword

    elif action == 'redirect_to':
        new_url = redirect_to

    if 'redirect_to' in action:
        if old_url and new_url:
            redirect = RedirectManager(
                active=1,
                from_url=old_url,
                to_url=new_url,
                response_code=301,
                date_start=datetime.now().date(),
                date_end=0,
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


def update_product_variants(product_id):
    product = get_product(product_id)

    main_category = db.session.execute(
        db.select(product_to_category)
        .filter_by(product_id=product_id, main_category=1)).one()

    series = ''
    for attribute in product.attributes:
        if attribute.attribute_id == 134:
            series = attribute.text
            break

    request_base = Product.query
    request_base = (request_base.join(Product.categories)
                    .filter(Category.category_id == main_category.category_id))

    request_base = (request_base.join(Product.attributes)
                    .where((ProductAttribute.attribute_id == 134)
                           & (ProductAttribute.text == series)))
    products = request_base.all()

    for product in products:
        for attribute in product.attributes:
            if attribute.attribute_id == 55:
                product.upc = round(float(attribute.text) / 500) * 5
                break

    title = '{"1":"Модельный ряд:"}'

    product_ids_in_series = {}
    for product in products:
        for attribute in product.attributes:
            if attribute.attribute_id != 134:
                continue

            product_ids_in_series[int(product.upc)] = product.product_id
            break

    product_ids_in_series = dict(sorted(product_ids_in_series.items()))
    product_ids_in_series = list(product_ids_in_series.values())

    for product_id in product_ids_in_series:

        variants_in_base = db.session.execute(
            db.select(ProductVariant)
            .filter(ProductVariant.product_id == product_id)).scalar()
        if variants_in_base:
            variants_in_base.prodvar_title = title
            variants_in_base.prodvar_product_str_id = ','.join(map(str, product_ids_in_series))
        else:
            new_variant = ProductVariant(
                product_id=product_id,
                prodvar_title=title,
                prodvar_product_str_id=','.join(map(str, product_ids_in_series))
            )
            db.session.add(new_variant)

    for product in products:
        for attribute in product.attributes:
            if attribute.attribute_id == 55:
                product.upc = 'до ' + str(product.upc) + ' м²'
                break

    db.session.commit()
    return product_ids_in_series


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
        # .filter(OtherProduct.link_confirmed is None)).scalars())

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
            if 'Dahatsu GR-07H' in other_product.name:
                print(other_product_name, ' - - ', matching)

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


@app.route('/products/prices/settings', methods=['GET'])
@login_required
def products_prices_settings():
    settings_in_base, settings = get_products_prices_settings()

    special_offers = db.session.execute(db.select(SpecialOffer)).scalars()

    options = db.session.execute(db.select(Option)).scalars()
    categories = get_categories()

    return render_template('products/prices_settings.html',
                           settings=settings,
                           special_offers=special_offers,
                           options=options,
                           categories=categories)


def get_products_prices_settings():
    settings_in_base = db.session.execute(
        db.select(Module).filter_by(name='products_prices')).scalar()

    settings = {}
    if settings_in_base:
        settings = json.loads(settings_in_base.value)

    return settings_in_base, settings


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


@app.route('/products/prices/action', methods=['POST'])
@login_required
def products_prices_action():
    page = request.args.get('page')
    action = str(request.form.get('action'))

    settings_in_base, settings = get_products_prices_settings()
    if not settings.get('special_offer_id'):
        flash('Настройки специального предложения не заданны')
        return redirect(url_for('products', path='prices', page=page))

    if 'all_products_' in action:
        change_prices.delay(price_type=action.replace('all_products_', ''),
                            settings=settings)

    elif 'this_products_' in action:
        filter = get_filter(path='prices')
        change_prices.delay(filter=filter,
                            price_type=action.replace('this_products_', ''),
                            settings=settings)

    elif 'manual_' in action:
        manual_confirm_prices(action.replace('manual_', ''),
                              settings=settings)

    return redirect(url_for('products', path='prices', page=page))


def manual_confirm_prices(price_type, settings):
    """ Ручное применение цен """
    count = 1
    products_count = request.form.get('products-count')
    products_count = int(products_count) if products_count else 0

    discount_products = get_discount_products()

    while count <= products_count:
        product_id = request.form.get('product-id-' + str(count))
        new_price = request.form.get('price-' + str(count))
        if not product_id or not new_price:
            count += 1
            continue

        new_price = float(new_price)
        product = get_product(int(product_id))
        new_product_stiker(product, new_price, discount_products, settings)
        product_new_price(product, new_price, price_type, settings)

        count += 1
    db.session.commit()

    page = request.args.get('page')
    return redirect(url_for('products', path='prices', page=page))


def new_product_stiker(product, new_price, discount_products, settings):
    if product.product_id in discount_products:
        options_ids = settings.get('options_ids')
        options_ids = options_ids if options_ids else []

        for option in product.options:
            if str(option.option_id) in options_ids:
                price = option.product_option_value.price + new_price
                text = settings.get('stiker_text')
                if text:
                    product.ean = text.replace('price', str(int(price)))


def product_new_price(product, new_price, price_type, settings):
    """ Записывает цену товара и удоляет лишние """
    special_offer_id = settings.get('special_offer_id')

    def get_product_special_offer():
        if product.special_offers:
            for special_offer in product.special_offers:
                if special_offer.special_offer_id == int(special_offer_id):
                    return special_offer
        return None

    product_special_offer = get_product_special_offer()

    if price_type == 'normal_price':
        product.price = new_price

        if product_special_offer:
            db.session.delete(product_special_offer)

    elif price_type == 'special_price':

        if product.price <= new_price:
            product.price = new_price
            if product_special_offer:
                db.session.delete(product_special_offer)

        elif product_special_offer:
            product_special_offer.price = new_price
            product_special_offer.date_start = datetime.now().date()
            product_special_offer.date_end = 0

        elif not product_special_offer:
            special_offer = ProductSpecial(
                customer_group_id=1,
                priority=0,
                price=float(new_price),
                date_start=datetime.now().date(),
                date_end=0,
                special_offer_id=special_offer_id
            )
            product.special_offers.append(special_offer)


@celery.task()
def change_prices(filter={}, price_type='', settings={}):
    delta = settings.get('price_delta')
    delta = float(delta)/100 if delta else 0

    special_offer_id = settings.get('special_offer_id')

    products = tuple(get_products(pagination=False, filter=filter))

    def convert_price(price):
        try:
            price = float(price)
        except:
            price = 0
        return price

    for product in products:
        if not product.other_shop:
            continue

        def replace_price():
            if abs(product.price - other_price) <= product.price * delta:
                new_product_stiker(product, other_price,
                                   get_discount_products(), settings)
                product_new_price(product, other_price, price_type, settings)
                return True
            return False

        # Одна цена конкурента
        if len(product.other_shop) < 2:
            other_price = convert_price(product.other_shop[0].price)
            if not other_price:
                continue

            replace_price()
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
            if replace_price():
                break

    db.session.commit()
    print('End')


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


@app.route('/work_plan', methods=['GET', 'POST'])
@login_required
def work_plan():
    global work_plan_fields
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
    if not work_plan:
        work_plan = {}

    manufacturers = []
    all_manufacturers = []

    for product in category.products:
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
                           all_manufacturers=all_manufacturers,
                           work_plan_fields=work_plan_fields)


work_plan_fields = ['models', 'prices', 'stock', 'variants']

def get_module(name):
    return db.session.execute(
        db.select(Module).filter_by(name=name)).scalar()

@app.route('/work_plan_<int:category_id>_update', methods=['POST'])
@login_required
def work_plan_update(category_id):
    global work_plan_fields
    category_id = str(category_id)

    plan_in_base = db.session.execute(
        db.select(Module).filter_by(name='work_plan')).scalar()

    all_plans = {}

    if plan_in_base:
        all_plans = json.loads(plan_in_base.value)

    manufacturers_count = request.form.get('manufacturers-count')
    count = 1

    while count <= int(manufacturers_count):
        new_plan = {}
        manufacturer = request.form.get('manufacturer-' + str(count))

        for field in work_plan_fields:
            new_plan[field] = request.form.get(field + '-' + str(count))

        if not all_plans.get(category_id):
            all_plans[category_id] = {}

        all_plans[category_id][manufacturer] = new_plan

        count += 1

    if plan_in_base:
        plan_in_base.value = json.dumps(all_plans)
    else:
        new_plan = Module(name='work_plan',
                          value=json.dumps(all_plans))
        db.session.add(new_plan)

    db.session.commit()
    return redirect(url_for('work_plan'))


@app.route('/work_plan_<int:category_id>_clean', methods=['GET'])
@login_required
def work_plan_clean(category_id):
    plan_in_base = db.session.execute(
        db.select(Module).filter_by(name='work_plan')).scalar()

    if plan_in_base:
        plan = json.loads(plan_in_base.value)
        plan.pop(str(category_id), None)
        plan_in_base.value = json.dumps(plan)
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




