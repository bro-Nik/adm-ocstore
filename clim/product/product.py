import json
import os
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, request, session, flash,\
    Blueprint
from flask_login import login_required, current_user
from clim.app import redis, app
from clim.general_functions import get_product
from clim.models import Attribute, AttributeDescription, Category, Module, OtherProduct, OtherShops, Product, ProductAttribute, ProductImage, ProductOptionValue, ProductToCategory, ProductVariant, RedirectManager, Review, SeoUrl, StockStatus, db


product = Blueprint('product', __name__, template_folder='templates', static_folder='static')


def get_main_category(product_id):
    return db.session.execute(
        db.select(ProductToCategory)
        .filter_by(product_id=product_id, main_category=1)).one()


def get_url(category_id=None, product_id=None):
    if category_id:
        filter = 'category_id='+str(category_id)
    elif product_id:
        filter = 'product_id='+str(product_id)
    else:
        return None

    return db.session.execute(db.select(SeoUrl).filter_by(query=filter)).scalar()


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


@product.route('/products', methods=['GET', 'POST'])
@product.route('/products/<string:path>', methods=['GET', 'POST'])
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


@product.route('/products/action', methods=['POST'])
@login_required
def products_action():
    data = json.loads(request.data) if request.data else {}
    print('#' * 50)
    print(data)
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

        main_category = get_main_category(product_id)
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
