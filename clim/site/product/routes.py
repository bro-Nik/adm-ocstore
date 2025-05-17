import json
# import tempfile
from clim.site.product.services.upload_price_lists import upload_prices
# from fuzzywuzzy import fuzz
from flask import render_template, url_for, request, flash, redirect, session
from flask_login import login_required

from clim.site.other_shops.models import OtherShops
from clim.models import Category, Option, SpecialOffer, db, Product
from .tasks import change_prices, comparison_products
from .utils import get_stock_statuses, get_filter, \
    manual_confirm_prices, products_prices_module, manual_comparison
from . import bp


@bp.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    path = request.args.get('path') or 'products'

    other_shops = OtherShops.get_all()
    products = Product.all_by_filter(filter=get_filter(request.method, path))

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
    path = request.args.get('path') or 'products'
    ids_list = []

    for product_id in data.get('ids', []):
        product = Product.get(product_id)
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
    # return ''
    page = request.args.get('page', 1, type=int)
    return {'redirect': url_for('.products', path=path, page=page)}


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

        db.session.commit()
        return {'redirect': url_for('.products_prices_settings')}

    special_offers = db.session.execute(db.select(SpecialOffer)).scalars()
    options = db.session.execute(db.select(Option)).scalars()

    return render_template('product/prices_settings.html',
                           settings=products_prices_module.get_settings(),
                           # settings=json.loads(module.value),
                           special_offers=special_offers,
                           options=options,
                           categories=Category.get_all())

UPDATED_PRODUCTS_IDS = 'unique_matched'
UPDATED_PRODUCTS = 'unique_matched_prods'


@bp.route('/apply-prices', methods=['POST'])
def products_apply_prices():
    session[UPDATED_PRODUCTS] = {}
    session[UPDATED_PRODUCTS_IDS] = []
    try:
        price_type = request.form.get('price_type', 'normal_price')
        update_only_lower = request.form.get('update_only_lower') == 'on'
        applied_count = 0

        for item in request.form.getlist('apply_price'):
            product_id, new_price = item.split('_')
            product = Product.query.get(product_id)
            new_price = float(new_price)

            if not product:
                continue
            session[UPDATED_PRODUCTS_IDS].append(product_id)
            session[UPDATED_PRODUCTS][product.product_id] = new_price

            if update_only_lower and new_price >= product.price:
                continue

            product.new_price(new_price, price_type)
            applied_count += 1

        db.session.commit()
        flash(f'Успешно обновлено {applied_count} цен', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении цен: {str(e)}', 'error')

    return redirect(url_for('.products_upload_prices'))


@bp.route('/upload-prices', methods=['GET', 'POST'])
def products_upload_prices():
    unique_matched = []

    if request.method == 'POST':
        price_list = request.files.get('price_file')
        if price_list:
            result, message = upload_prices(price_list)
            if message:
                flash(message['text'], message['type'])
            if result:
                unique_matched = result
                session[UPDATED_PRODUCTS_IDS] = []

    updated_ids = session.get(UPDATED_PRODUCTS_IDS, [])
    updated_products = []

    if updated_ids:
        # Получаем полную информацию об обновленных товарах
        products = Product.query.filter(Product.product_id.in_(updated_ids)).all()

        # Формируем данные для отображения
        updated_products = [{
            'product_id': p.product_id,
            'product_name': p.name,
            'current_price': p.price,
            'date_updated_price': p.date_updated_price,
            'new_price': session[UPDATED_PRODUCTS].get(str(p.product_id))
        } for p in products]

    return render_template(
        'product/upload.html',
        matched_products=unique_matched,
        updated_products=updated_products
    )
