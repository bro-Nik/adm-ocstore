import json
import re

from flask import abort, render_template, url_for, request
from flask_login import login_required

from clim.utils import actions_in

from .tasks import get_other_products_task
from .utils import get_category, get_shop, get_other_shops
from .models import db, OtherCategory, OtherProduct, OtherShops
from . import bp


@bp.route('/shops', methods=['GET', 'POST'])
@login_required
def shops():
    """ Страница магазинов """
    if request.method == 'POST':
        # Действия
        actions_in(request.data, get_shop)
        db.session.commit()
        return ''

    return render_template('other_shops/shops.html', shops=get_other_shops())


@bp.route('/shop_settings', methods=['GET', 'POST'])
@login_required
def shop_settings():
    """ Добавить или изменить магазин """
    shop = get_shop(request.args.get('shop_id')) or OtherShops()

    if request.method == 'POST':
        if not shop.shop_id:
            db.session.add(shop)

        data = json.loads(request.data) if request.data else {}
        for key in ['name', 'domain', 'parsing']:
            setattr(shop, key, data.get(key, ''))
        db.session.commit()
        return {'redirect': url_for('.shop_settings', shop_id=shop.shop_id)}

    return render_template('other_shops/shop_settings.html', shop=shop)


@bp.route('/<int:shop_id>/categories', methods=['GET', 'POST'])
@login_required
def shop_categories(shop_id):
    """ Категории магазина """
    if request.method == 'POST':
        # Действия
        actions_in(request.data, get_category)
        db.session.commit()
        return ''

    shop = get_shop(shop_id)
    for cat in shop.categories:
        cat.new_price_count = len(cat.new_price.split(',')) if cat.new_price else 0
        cat.new_product_count = len(cat.new_product.split(',')) if cat.new_product else 0

    return render_template('other_shops/shop_categories.html', shop=shop)


@bp.route('/<int:shop_id>/category_settings', methods=['GET', 'POST'])
@login_required
def category_settings(shop_id):
    """ Настройки категории магазина """
    category_id = request.args.get('category_id')
    category = get_category(category_id) or OtherCategory(shop_id=shop_id)

    if request.method == 'POST':
        if not category.other_category_id:
            db.session.add(category)

        data = json.loads(request.data) if request.data else {}

        # Параметры парсинга
        keys = ['blocks_type', 'blocks_class', 'block_name_type',
                'block_name_class', 'block_name_inside', 'block_link_type',
                'block_link_class', 'block_price_type', 'block_price_class',
                'block_other_price_type', 'block_other_price_class']
        parsing = {'minus': re.sub(r'( ,|, )', ',', data.get('minus', ''))}
        for key in keys:
            parsing[key] = data.get(key, '')

        category.parsing = json.dumps(parsing)
        category.name = data.get('name')
        category.url = data.get('url')
        category.parent_id = data.get('parent_id') or 0
        category.sort = data.get('sort') or 0

        db.session.commit()
        return {'redirect': url_for('.category_settings', shop_id=shop_id,
                                    category_id=category.other_category_id)}

    return render_template('other_shops/category_settings.html',
                           category=category, shop=get_shop(shop_id))


@bp.route('/<int:shop_id>/category/products', methods=['GET', 'POST'])
@login_required
def category_products(shop_id):
    filter_items = request.form if request.method == 'POST' else request.args

    category_id = filter_items.get('category_id', '')
    changes = filter_items.get('changes', '')
    search = filter_items.get('search', '')

    shop = get_shop(shop_id)
    cat = get_category(category_id)
    products = OtherProduct.query.filter_by(shop_id=shop_id)

    if cat:
        cat.new_price_ids = cat.new_price.split(',') if cat.new_price else []
        cat.new_product_ids = cat.new_product.split(',') if cat.new_product else []

        products = products.filter_by(category_id=category_id)
        ids = getattr(cat, f'{changes}_ids', []) if changes else []
        if ids:
            products = products.where(OtherProduct.other_product_id.in_(ids))

    if search:
        products = products.where(OtherProduct.name.contains(search))

    products = products.paginate(page=request.args.get('page', 1, type=int),
                                 per_page=20, error_out=False)

    return render_template('other_shops/category_products.html', shop=shop,
                           products=products, category=cat,
                           changes=changes, search=search)


@bp.route('/get_products_test', methods=['GET'])
@login_required
def get_products_test():
    category_id = request.args.get('category_id')
    products = get_other_products_task(category_id, True)
    category = get_category(category_id) or abort(404)
    return render_template('other_shops/test_products.html',
                           products=products, category=category)


@bp.route('/get_products/<int:category_id>', methods=['GET'])
@login_required
def get_products(category_id):
    get_other_products_task.delay(category_id)
    return ''


@bp.route('/list_all_categories', methods=['GET'])
@login_required
def ajax_categories():
    search = request.args.get('search', '')
    shop_id = request.args.get('shop_id')
    results = []

    if not search:
        results.append({'id': '0', 'text': 'Все'})

    categories = db.session.execute(
        db.select(OtherCategory)
        .filter_by(shop_id=shop_id, parent_id=0)).scalars()

    def uppend(cat, prefix=''):
        if not search or search.lower() in cat.name.lower():
            results.append({'id': cat.other_category_id, 'text': f'{prefix}{cat.name}'})

    for category in categories:
        uppend(category)
        for subcategory in category.child_categories:
            uppend(subcategory, '-- ')

    return json.dumps({'results': results}, ensure_ascii=False)
