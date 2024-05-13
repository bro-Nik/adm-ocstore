import json
from flask import render_template, url_for, request, flash
from flask_login import login_required

from clim.site.other_shops.utils import get_other_shops
from clim.utils import get_categories, get_product
from clim.models import Option, SpecialOffer, db
from .tasks import change_prices, comparison_products
from .utils import get_stock_statuses, get_products, get_filter, \
    manual_confirm_prices, products_prices_module, manual_comparison
from . import bp


@bp.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    path = request.args.get('path') or 'products'

    other_shops = get_other_shops()
    products = get_products(filter=get_filter(request.method, path))

    # attributes_in_products = []
    # for product in products:
    #     for attribute in product.attributes:
    #         if attribute.main_attribute.description.name not in attributes_in_products:
    #             attributes_in_products.append(attribute.main_attribute.description.name)

    return render_template(f'product/{path}.html',
                           products=products,
                           stock_statuses=get_stock_statuses(),
                           other_shops=tuple(other_shops),
                           # attributes_in_products=attributes_in_products
                           )


@bp.route('/products/action', methods=['POST'])
@login_required
def products_action():
    data = json.loads(request.data) if request.data else {}
    action = data.get('action', '')
    other = data.get('other', '')
    ids_list = []

    for product_id in data.get('ids', []):
        product = get_product(product_id)
        if not product:
            continue

        error = False
        if 'redirect_to' in action and error is False:
            error = product.redirect(action, other)
        if 'delete' in action and not error:
            error = product.delete()
        elif 'clean_field_' in action and error is False:
            field = action.replace('clean_field_', '')
            setattr(product, field, other)
        elif 'stock_status_' in action and error is False:
            status = action.replace('stock_status_', '')
            error = product.update_stock_status(status)
        elif action == 'prodvar_update' and error is False:
            if product.product_id not in ids_list:
                ids_list = product.update_variants()

        if not error:
            db.session.commit()
    return ''


@bp.route('/comparison_products', methods=['POST'])
@login_required
def products_action_comparison():
    """ Запуск подбира похожих товаров """
    data = json.loads(request.data) if request.data else {}

    if data.get('all_products'):
        comparison_products.delay({})
        flash('Запущено сопоставление всех товаров')

    elif data.get('by_filter'):
        filter_by = get_filter(request.method, path='comparison')
        comparison_products.delay(filter_by)
        flash('Запущено сопоставление отфильтрованных товаров')

    elif data.get('manual'):
        action = data.get('manual')
        manual_comparison(data.get('ids'), action)
        db.session.commit()
        mess = 'привязаны' if action == 'bind' else 'отвязаны'
        flash(f'Выбранные товары {mess}')

    page = request.args.get('page', 1, type=int)
    return {'redirect': url_for('.products', path='comparison', page=page)}


@bp.route('/prices/action', methods=['POST'])
@login_required
def products_action_prices():
    data = json.loads(request.data) if request.data else {}

    settings = products_prices_module.get_settings()
    if not settings.get('special_offer_id'):
        flash('Настройки специального предложения не заданны', 'warning')
        return ''

    if data.get('all_products'):
        price_type = data.get('all_products')
        change_prices.delay({}, price_type)
        flash('Запущен авто подбор цен всех товаров')

    elif data.get('by_filter'):
        price_type = data.get('by_filter')
        filter_by = get_filter(path='prices')
        change_prices.delay(filter_by, price_type)
        flash('Запущен авто подбор цен отфильтрованных товаров')

    elif data.get('manual'):
        price_type = data.get('manual')
        manual_confirm_prices(data.get('ids'), price_type)
        db.session.commit()
        flash('Применены цены для выбранных товаров')

    page = request.args.get('page', 1, type=int)
    return {'redirect': url_for('.products', path='prices', page=page)}


@bp.route('/prices/settings', methods=['GET', 'POST'])
@login_required
def products_prices_settings():
    if request.method == 'POST':
        data = json.loads(request.data) if request.data else {}
        settings = {
            'special_offer_id': data.get('special_offer_id', ''),
            'options_ids': data.get('options_ids', ''),
            'stiker_text': data.get('stiker_text', ''),
            'price_delta': data.get('price_delta', '')
        }
        products_prices_module.set_settings(settings)
        module = products_prices_module.module
        print(module.value)

        db.session.commit()
        return {'redirect': url_for('.products_prices_settings')}

    special_offers = db.session.execute(db.select(SpecialOffer)).scalars()
    options = db.session.execute(db.select(Option)).scalars()

    return render_template('product/prices_settings.html',
                           settings=products_prices_module.get_settings(),
                           # settings=json.loads(module.value),
                           special_offers=special_offers,
                           options=options,
                           categories=get_categories())
