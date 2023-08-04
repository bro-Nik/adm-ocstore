from flask import render_template, redirect, url_for, request, session, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from clim.app import app, db, login_manager
from clim.general_functions import dict_get_or_other
from clim.models import Product
# from clim.routes import get_products


@app.route('/reports/viewed_products', methods=['GET'])
@login_required
def viewed_products(action=None):
    products = (Product.query.order_by(Product.viewed.desc())
        .paginate(page=dict_get_or_other(request.args, 'page', 1),
                                         per_page=20,
                                         error_out=False))

    if request.args.get('action') == 'clean':
        for product in products:
            product.viewed = 0
        db.session.commit()
        return redirect(url_for('viewed_products'))

    return render_template('reports/viewed_products.html', products=products)
