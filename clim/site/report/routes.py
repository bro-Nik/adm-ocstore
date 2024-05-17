from flask import render_template, request, session
from flask_login import login_required

from clim.models import db, Product
from . import bp


@bp.route('/viewed_products', methods=['GET'])
@login_required
def viewed_products():
    products = db.paginate(db.select(Product),
                       page=request.args.get('page', 1, type=int),
                       per_page=session.get('results_per_page', 20),
                       error_out=False)

    if request.args.get('action') == 'clean':
        for product in products:
            product.viewed = 0
        db.session.commit()
        return ''

    return render_template('report/viewed_products.html', products=products)
