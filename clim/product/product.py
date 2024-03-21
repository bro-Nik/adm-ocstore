import json
import os
from thefuzz import fuzz as f
from datetime import datetime
from flask import current_app, render_template, redirect, url_for, request, session, flash,\
    Blueprint
from flask_login import login_required
from clim.app import celery
from clim.general_functions import get_categories, get_discount_products, get_main_category, get_other_product, get_product
from clim.models import Category, Module, Option, OtherProduct, OtherShops, Product, ProductAttribute, ProductImage, ProductOptionValue, ProductSpecial, ProductToCategory, ProductVariant, RedirectManager, Review, SeoUrl, SpecialOffer, StockStatus, db
from . import bp


def get_url(category_id=None, product_id=None):
    if category_id:
        param = f'category_id={category_id}'
    elif product_id:
        param = f'product_id={product_id}'
    else:
        return None

    return db.session.execute(db.select(SeoUrl).filter_by(query=param)).scalar()


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
        'new_products': session.get('new_products')
    }

    if path:
        filter['other_filter'] = session.get(path + '_other_filter')
    return filter


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


def get_stock_statuses():
    return db.session.execute(
        db.select(StockStatus).filter_by(language_id=1)).scalars()


@bp.route('/products', methods=['GET', 'POST'])
@bp.route('/products/<string:path>', methods=['GET', 'POST'])
@login_required
def products(path=''):
    other_shops = db.session.execute(db.select(OtherShops)).scalars()

    # attributes = (Attribute.query
    #     .join(Attribute.description)
    #     .where(AttributeDescription.name is not None)
    #     .order_by(Attribute.sort_order)).all()

    filter = get_filter(request.method, path)

    stock_statuses = get_stock_statuses()

    products = get_products(filter=filter)

    attributes_in_products = []
    for product in products:
        for attribute in product.attributes:
            if attribute.main_attribute.description.name not in attributes_in_products:
                attributes_in_products.append(attribute.main_attribute.description.name)

    page = ('product/' + path + '.html') if path else 'product/products.html'

    return render_template(page,
                           products=products,
                           stock_statuses=stock_statuses,
                           other_shops=tuple(other_shops),
                           # attributes=tuple(attributes),
                           attributes_in_products=attributes_in_products)


@bp.route('/products/action', methods=['POST'])
@login_required
def products_action():
    data = json.loads(request.data) if request.data else {}
    ids = data.get('ids')

    info_list = data.get('info') if data.get('info') else {}
    info = {}
    if info_list:
        for item in info_list:
            info[item['name']] = item['value']

    action = str(info.get('action'))
    other = info.get('other')

    for product_id in ids:
        if 'delete_' in action:
            product_delete(product_id, action.replace('delete_', ''), other)
        elif 'clean_field_' in action:
            field = action.replace('clean_field_', '')
            change_field(product_id, field, other)
        elif 'stock_status_' in action:
            update_stock_status(product_id, action.replace('stock_status_', ''))
        elif action == 'prodvar_update':
            try:
                ids_list
            except NameError:
                ids_list = []

            if product_id not in ids_list:
                ids_list = update_product_variants(product_id)

    page = request.args.get('page')
    return redirect(url_for('.products', page=page))


def product_delete(product_id: int, action: str, redirect_to):
    """ Удаление товара и все, что с ним связано """
    image_path = current_app.config['IMAGE_PATH']
    download_path = current_app.config['DOWNLOAD_PATH']

    old_url = new_url = None

    product = get_product(product_id)

    # Seo url
    product_url = get_url(product_id=product_id)
    if product_url:
        old_url = current_app.config['CATALOG_DOMAIN'] + product_url.keyword
        db.session.delete(product_url)

    # Добавляем редирект
    if action == 'redirect_to_category':

        main_category = get_main_category(product_id)
        main_category_url = get_url(category_id=main_category.category_id)

        if main_category_url:
            new_url = current_app.config['CATALOG_DOMAIN'] + main_category_url.keyword

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


def change_field(product_id: int, field: str, data=''):
    product = get_product(product_id)

    if field == 'ean':
        product.ean = data
    elif field == 'isbn':
        product.isbn = data
    elif field == 'jan':
        product.jan = data
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


def update_product_variants(product_id):
    product = get_product(product_id)
    main_category = get_main_category(product_id)

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


@bp.route('/comparison_products', methods=['POST'])
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
    # products = get_products(pagination=False, filter=filter)
    products = {}

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

        product_name = product.description.name.lower()

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


@bp.route('/confirm_product_to_product', methods=['POST'])
@login_required
def confirm_product_to_product():
    """ Привязка или отвязка товара конкурента """
    data = json.loads(request.data) if request.data else {}
    ids = data.get('ids')
    action = data.get('action')

    for id in ids:
        other_product = get_other_product(id)

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

    db.session.commit()

    page = request.args.get('page')
    return redirect(url_for('.products', path='comparison', page=page))


@bp.route('/prices/action', methods=['POST'])
@login_required
def products_prices_action():
    page = request.args.get('page')
    data = json.loads(request.data) if request.data else {}
    data_list = data.get('ids')
    info_list = data.get('info') if data.get('info') else {}
    info = {}
    if info_list:
        for item in info_list:
            info[item['name']] = item['value']

    action = str(info.get('action'))

    settings_in_base, settings = get_products_prices_settings()
    if not settings.get('special_offer_id'):
        flash('Настройки специального предложения не заданны')
        return redirect(url_for('.products', path='prices', page=page))

    if 'all_products_' in action:
        price_type = action.replace('all_products_', '')
        change_prices.delay(price_type=price_type, settings=settings)

    elif 'this_products_' in action:
        price_type = action.replace('this_products_', '')
        filter = get_filter(path='prices')
        change_prices.delay(filter=filter, price_type=price_type, settings=settings)

    elif 'manual_' in action:
        price_type = action.replace('manual_', '')
        manual_confirm_prices(data_list, price_type, settings=settings)

    return redirect(url_for('.products', path='prices', page=page))


@celery.task()
def change_prices(filter={}, price_type='', settings={}):
    delta = settings.get('price_delta')
    delta = float(delta)/100 if delta else 0

    special_offer_id = settings.get('special_offer_id')

    # products = tuple(get_products(pagination=False, filter=filter))
    products = {}

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


def manual_confirm_prices(data_list, price_type, settings):
    """ Ручное применение цен """
    discount_products = get_discount_products()

    for data in data_list:
        data = data.split('-')
        product_id = data[0]
        new_price = float(data[1])

        product = get_product(product_id)
        new_product_stiker(product, new_price, discount_products, settings)
        product_new_price(product, new_price, price_type, settings)

    db.session.commit()

    page = request.args.get('page')
    return redirect(url_for('.products', path='prices', page=page))


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
                price=float(new_price),
                date_start=datetime.now().date(),
                special_offer_id=special_offer_id
            )
            product.special_offers.append(special_offer)


def get_products_prices_settings():
    settings_in_base = db.session.execute(
        db.select(Module).filter_by(name='products_prices')).scalar()

    settings = {}
    if settings_in_base:
        settings = json.loads(settings_in_base.value)

    return settings_in_base, settings


@bp.route('/prices/settings', methods=['GET'])
@login_required
def products_prices_settings():
    settings_in_base, settings = get_products_prices_settings()

    special_offers = db.session.execute(db.select(SpecialOffer)).scalars()

    options = db.session.execute(db.select(Option)).scalars()
    categories = get_categories()

    return render_template('product/prices_settings.html',
                           settings=settings,
                           special_offers=special_offers,
                           options=options,
                           categories=categories)
