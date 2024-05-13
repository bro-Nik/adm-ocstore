from flask import render_template
from flask_login import login_required

from clim.models import db
from clim.utils import get_categories
from . import bp


def product_price_request(product):
    return product.price == 100001


def product_not_in_stock(product):
    return product.quantity < 1


def product_on_order(product):
    return product.quantity == 1


def product_in_stock(product):
    return product.quantity > 1


@bp.route('/categories', methods=['GET', 'POST'])
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

    return render_template('category/categories.html',
                           categories=categories,
                           result=result)


@bp.route('/category_<int:category_id>/settings', methods=['GET', 'POST'])
@login_required
def category_settings(category_id):
    category = db.session.execute(
        db.select(Category).filter(Category.category_id == category_id)).scalar()

    return render_template('category_settings.html', category=category)
