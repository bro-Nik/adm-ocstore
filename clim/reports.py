from flask import render_template, redirect, url_for, request, session, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from clim.app import app, db, login_manager
from clim.models import Product
from clim.routes import get_products


@app.route('/reports/viewed_products', methods=['GET'])
@app.route('/reports/viewed_products/<string:action>', methods=['GET'])
@login_required
def viewed_products(action=None):
    products = get_products(filter={'sort': 'viewed'})

    if action == 'clean':
        for product in products:
            product.viewed = 0
        db.session.commit()
        return redirect(url_for('viewed_products'))

    return render_template('reports/viewed_products.html', products=products)
