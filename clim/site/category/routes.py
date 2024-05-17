from flask import render_template
from flask_login import login_required

from clim.models import Category
from . import bp


@bp.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    categories = tuple(Category.get_all())

    result = {}

    for category in tuple(categories):
        if not category.products:
            continue

        result[category.category_id] = {'in_stock': 0,
                                        'on_order': 0,
                                        'price_request': 0,
                                        'not_in_stock': 0}

        for product in category.products:

            if product.in_stock:
                result[category.category_id]['in_stock'] += 1
            if product.on_order:
                result[category.category_id]['on_order'] += 1
            if product.price_request:
                result[category.category_id]['price_request'] += 1
            if not product.in_stock:
                result[category.category_id]['not_in_stock'] += 1

    return render_template('category/categories.html',
                           categories=categories, result=result)


@bp.route('/category_<int:category_id>/settings', methods=['GET', 'POST'])
@login_required
def category_settings(category_id):
    category = Category.get(category_id)
    return render_template('category_settings.html', category=category)
