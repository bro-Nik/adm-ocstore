import json

from flask import abort, render_template, request
from flask_login import login_required

from clim.site.other_shops.utils import Log
from clim.utils import actions_in

from .tasks import get_other_products_task
from .models import db, OtherCategory, OtherProduct, OtherShops
from . import bp


@bp.route('/shops', methods=['GET', 'POST'])
@login_required
def shops():
    """ Страница магазинов """
    page = request.args.get('page', 1, type=int)

    if request.method == 'POST':
        return actions_in(OtherShops.get)

    shops = db.paginate(db.select(OtherShops),
                        per_page=10, error_out=False, page=page)
    return render_template('other_shops/shops.html',
                           shops=shops, child_obj=OtherShops(shop_id=0))


@bp.route('/shop_settings', methods=['GET', 'POST'])
@login_required
def shop_settings():
    """ Добавить или изменить магазин """
    shop = OtherShops.get(request.args.get('shop_id')) or OtherShops()

    if request.method == 'POST':
        return actions_in(shop)

    return render_template('other_shops/shop_settings.html', shop=shop)


@bp.route('/<int:shop_id>/categories', methods=['GET', 'POST'])
@login_required
def shop_categories(shop_id):
    """ Категории магазина """
    if request.method == 'POST':
        return actions_in(OtherCategory.get)

    shop = OtherShops.get(shop_id)
    for cat in shop.categories:
        cat.new_price_count = len(cat.new_price.split(',')) if cat.new_price else 0
        cat.new_product_count = len(cat.new_product.split(',')) if cat.new_product else 0

    return render_template('other_shops/shop_categories.html', shop=shop,
                           child_obj=OtherCategory(other_category_id=0,
                                                   shop_id=shop_id))


@bp.route('/<int:shop_id>/logs', methods=['GET'])
@login_required
def shop_logs(shop_id):
    """ Настройки категории магазина """

    return render_template('other_shops/logs.html',
                           shop=OtherShops.get(shop_id))


@bp.route('/<int:shop_id>/category/settings', methods=['GET', 'POST'])
@login_required
def category_settings(shop_id):
    """ Настройки категории магазина """
    category_id = request.args.get('category_id')
    category = OtherCategory.get(category_id) or OtherCategory(shop_id=shop_id)

    if request.method == 'POST':
        return actions_in(category)

    return render_template('other_shops/category_settings.html',
                           category=category, shop=OtherShops.get(shop_id))


@bp.route('/<int:shop_id>/category/products', methods=['GET', 'POST'])
@login_required
def category_products(shop_id):
    filter_items = request.form if request.method == 'POST' else request.args

    category_id = filter_items.get('category_id', '')
    changes = filter_items.get('changes', '')
    search = filter_items.get('search', '')

    shop = OtherShops.get(shop_id)
    cat = OtherCategory.get(category_id)
    products = db.select(OtherProduct).filter_by(shop_id=shop_id)

    if cat:
        cat.new_price_ids = cat.new_price.split(',') if cat.new_price else []
        cat.new_product_ids = cat.new_product.split(',') if cat.new_product else []

        products = products.filter_by(category_id=category_id)
        ids = getattr(cat, f'{changes}_ids', []) if changes else []
        if ids:
            products = products.where(OtherProduct.other_product_id.in_(ids))

    if search:
        products = products.where(OtherProduct.name.contains(search))

    products = db.paginate(products, page=request.args.get('page', 1, type=int),
                                 per_page=20, error_out=False)

    return render_template('other_shops/category_products.html', shop=shop,
                           products=products, category=cat,
                           changes=changes, search=search)


@bp.route('/<int:shop_id>/category/logs', methods=['GET'])
@login_required
def category_logs(shop_id):
    """ Настройки категории магазина """
    category = OtherCategory.get(request.args.get('category_id'))

    return render_template('other_shops/logs.html',
                           category=category, shop=OtherShops.get(shop_id))


@bp.route('category/logs', methods=['GET'])
@login_required
def json_module_logs():
    timestamp = request.args.get('timestamp', 0.0, type=float)
    shop_id = request.args.get('shop_id')
    category_id = request.args.get('category_id')
    logs = []

    # Для итерации по модулям
    if category_id:
        ids_list = [category_id]
    else:
        shop = OtherShops.get(request.args.get('shop_id'))
        ids_list = [cat._id for cat in shop.categories]

    for cat_id in ids_list:
        module_logs = Log(cat_id)
        logs += module_logs.get(timestamp)

    if logs:
        logs = sorted(logs, key=lambda log: log.get('timestamp'))
    return logs


@bp.route('/get_products_test', methods=['GET'])
@login_required
def get_products_test():
    category_id = request.args.get('category_id')
    products = get_other_products_task(category_id, True)
    category = OtherCategory.get(category_id) or abort(404)
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
            uppend(subcategory)

    return json.dumps({'results': results}, ensure_ascii=False)


@bp.route('/logs_delete', methods=['POST'])
@login_required
def logs_delete():
    return ''
