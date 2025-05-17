import json
from flask import session

from clim.models import db, ProductOption, ProductOptionValue, Product
from . import bp


def session_get(param):
    return session.get(f'{bp.name}_{param}')


def session_post(param, value):
    session[f'{bp.name}_{param}'] = value


# def get_products(pagination=True, filter={}):
#
#     request_base = Product.query
#
#     if filter.get('stock'):
#         stock = filter.get('stock')
#         if stock == 'not not in stock':
#             request_base = request_base.filter(Product.quantity > 0)
#         elif stock == 'in stock':
#             request_base = request_base.filter((Product.quantity == 10)
#                                                & (Product.price != 100001))
#         elif stock == 'on order':
#             request_base = request_base.filter(Product.quantity == 1)
#         elif stock == 'not in stock':
#             request_base = request_base.filter(Product.quantity == 0)
#         elif stock == 'price request':
#             request_base = request_base.filter(Product.price == 100001)
#
#     if filter.get('manufacturers_ids'):
#         manufacturers_ids = filter.get('manufacturers_ids')
#         request_base = request_base.where(Product.manufacturer_id.in_(manufacturers_ids))
#
#     if filter.get('categories_ids'):
#         categories_ids = filter.get('categories_ids')
#         request_base = (request_base.join(Product.categories)
#                    .filter(Category.category_id.in_(categories_ids)))
#
#     if filter.get('attribute_id'):
#         attribute_id = filter.get('attribute_id')
#         attribute_values = filter.get('attribute_values')
#         request_base = (request_base.join(Product.attributes)
#                     .where((ProductAttribute.attribute_id == attribute_id)
#                            & (ProductAttribute.text.in_(attribute_values)))
#                     .order_by(ProductAttribute.text))
#
#     if filter.get('options') == 'whith options':
#         request_base = (request_base.filter(Product.options != None))
#     elif filter.get('options') == 'whithout options':
#         request_base = (request_base.filter(Product.options == None))
#
#     #request_base = request_base.order_by(Product.mpn)
#
#     if not pagination:
#         return request_base.all()
#
#     return request_base.paginate(page=request.args.get('page', 1, type=int),
#                                  per_page=filter.get('per_page', 20, type=int),
#                                  error_out=False)


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

    products = Product.all_by_filter(filter=filter, pagination=False)

    products_ids = []
    for product in products:
        products_ids.append(product.product_id)

    other_products = (Product.query
        .join(Product.options)
        .join(ProductOption.product_option_value)
        .filter((ProductOptionValue.option_value_id == option_value.option_value_id)
                & (ProductOptionValue.product_id.notin_(products_ids)))).all()
    return other_products


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
    product_have_option = product_clean_other_options(Product.get(product_id),
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
                option.product_option_value.delete()
                # db.session.delete(option.product_option_value)
            # db.session.delete(option)
            option.delete()

    return product_have_this_option


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
