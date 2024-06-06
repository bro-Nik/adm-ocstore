import json
from datetime import datetime

from flask import render_template, redirect, url_for, request, session
from flask_login import login_required

from clim.utils import actions_in
from clim.crm.booking.utils import get_event_booking

from ..stock.utils import get_consumables_categories_ids
from ..stock.models import Stock, StockProduct
from ..utils import smart_int
from ..models import Product, db, OptionValueDescription, ProductDescription, \
    OptionValue, Category
from .models import Deal, DealStage
from .utils import employment_info, get_stages, sort_stage_deals, sort_stages
from . import bp


@bp.route('/update_filter', methods=['POST'])
def update_filter():
    session['stage_type'] = request.form.get('stage_type')
    return ''


@bp.route('/<string:view>', methods=['GET', 'POST'])
@bp.route('/', methods=['GET', 'POST'])
@login_required
def deals(view=None):
    if request.method == 'POST':
        return actions_in(Deal.get)

    if view not in ['kanban', 'list']:
        view = session.get('crm_view', 'kanban')
        return redirect(url_for('.deals', view=view))

    session['crm_view'] = view
    stage_type = session.get('stage_type', 'in_work')
    return render_template(f'deal/deals_{view}.html', stage_type=stage_type,
                           stages=tuple(get_stages(stage_type)),
                           deals=Deal.get_all())


@bp.route('/deal_info', methods=['GET', 'POST'])
@login_required
def deal_info():
    deal = Deal.get(request.args.get('deal_id'))
    if not deal:
        deal = Deal(date_add=datetime.now(),
                    stage=DealStage.get(type='start'))

    if request.method == 'POST':
        return actions_in(deal)

    return render_template('deal/deal/main.html', deal=deal,
                           stages=tuple(get_stages()))


@bp.route('/ajax_products', methods=['GET'])
@login_required
def ajax_products():
    # Исключем расходные материалы
    ids = get_consumables_categories_ids()
    products = (db.select(Product).join(Product.categories)
                .filter(Category.category_id.notin_(ids)))

    services = db.select(OptionValue)

    # Разделяем на пробелы и ищем совпадения
    search = request.args.get('search', '').lower()
    for word in search.split(' '):
        if word:
            products = (products.join(Product.description)
                        .filter(ProductDescription.name.contains(word)))
            services = (services.join(OptionValue.description)
                        .filter(OptionValueDescription.name.contains(word)))

    per_page = 10
    page = request.args.get('page', 1, type=int)
    result = []

    # Товары
    for product in db.paginate(products, page=page, per_page=per_page, error_out=False):
        result.append({'id': product.product_id,
                       'text': product.name,
                       'price': product.price,
                       'type': 'product',
                       'unit': product.unit})

    # Услуги
    for service in db.paginate(services, page=page, per_page=per_page, error_out=False):
        result.append({'id': service.option_value_id,
                       'text': service.name,
                       'price': service.price,
                       'type': 'service'})

    return json.dumps({'results': result, 'pagination': {'more': bool(result)}})


@bp.route('/ajax_consumables', methods=['GET'])
@login_required
def ajax_consumables():
    # Включаем только расходные материалы
    ids = get_consumables_categories_ids()
    products = (db.select(Product).join(Product.categories)
                .filter(Category.category_id.in_(ids)))

    # Разделяем на пробелы и ищем совпадения
    search = request.args.get('search', '').lower()
    for word in search.split(' '):
        if word:
            products = (products.join(Product.description)
                        .filter(ProductDescription.name.contains(word)))

    per_page = 10
    page = request.args.get('page', 1, type=int)
    result = []

    for product in db.paginate(products, page=page, per_page=per_page, error_out=False):
        result.append({'id': product.product_id,
                       'text': product.name,
                       'price': product.cost,
                       'type': 'product',
                       'unit': product.unit})

    return json.dumps({'results': result, 'pagination': {'more': bool(result)}})


@bp.route('/ajax_stocks_first', methods=['GET'])
@login_required
def ajax_stocks_first():
    product_id = request.args.get('product_id')
    stock_id = request.args.get('stock_id')

    select = db.select(StockProduct).filter_by(product_id=product_id)
    if stock_id:
        select = select.filter(StockProduct.stock_id == stock_id)
    else:
        select = select.filter(StockProduct.quantity > 0)

    stock = db.session.execute(select).scalar()
    if not stock:
        return ''

    unit = stock.main_product.unit
    return json.dumps({'id': stock.stock_id,
                       'text': stock.stock.name,
                       'quantity': f'{smart_int(stock.quantity)} {unit}'})


@bp.route('/ajax_stocks', methods=['GET'])
@login_required
def ajax_stocks():
    product_id = request.args.get('product_id')
    stocks = (db.select(StockProduct)
              .filter(StockProduct.product_id == product_id))

    search = request.args.get('search', '').lower()
    # Разделяем на пробелы и ищем совпадения
    for word in search.split(' '):
        if word:
            stocks = (stocks.join(StockProduct.stock)
                      .filter(Stock.name.contains(word)))

    per_page = 10
    page = request.args.get('page', 1, type=int)
    result = []
    ids = []

    for stock in db.paginate(stocks, page=page, per_page=per_page, error_out=False):
        unit = stock.main_product.unit
        ids.append(stock.stock_id)
        result.append({'id': stock.stock_id,
                       'text': stock.stock.name,
                       'quantity': f'{smart_int(stock.quantity)} {unit}',
                       'subtext': f'{smart_int(stock.quantity)} {unit}'})

    # Дабавление пустых складов
    if not search and len(result) < per_page:
        stocks = db.select(Stock).filter(Stock.stock_id.notin_(ids))
        for stock in db.paginate(stocks, page=page, per_page=per_page, error_out=False):
            result.append({'id': stock.stock_id,
                           'text': stock.name,
                           'quantity': '',
                           'subtext': ''})

    return json.dumps({'results': result, 'pagination': {'more': bool(result)}})


@bp.route('/update_stage', methods=['GET'])
@login_required
def update_stage():
    deal = Deal.get(request.args.get('deal_id'))
    deal.stage_id = request.args.get('stage_id')
    previous_deal_sort = request.args.get('previous_deal_sort')
    deal.sort_order = request.args.get('stage_id', 0, type=int) + 1
    db.session.commit()

    sort_stage_deals(deal.stage_id, deal.deal_id, previous_deal_sort)
    return redirect(url_for('.deals'))


@bp.route('/stage_move', methods=['GET'])
@login_required
def stage_move():
    stage_id = request.args.get('stage_id', 0, type=int)
    sort_order = request.args.get('sort_order', 0, type=int)
    print(sort_order)
    sort_stages(stage_id, sort_order)
    db.session.commit()

    return redirect(url_for('.deals'))


@bp.route('/new_stage', methods=['GET'])
@login_required
def new_stage():
    before_new_stage = DealStage.get(request.args.get('stage_id'))
    stages = get_stages()

    new_stage = DealStage(name='Новая стадия', type='',
                          color=before_new_stage.color)
    db.session.add(new_stage)

    count = 1
    for stage in stages:
        if stage.sort_order < before_new_stage.sort_order:
            stage.sort_order = count
            count += 1
        elif stage.sort_order == before_new_stage.sort_order:
            stage.sort_order = count
            new_stage.sort_order = count + 1
            count += 2
        elif stage.sort_order > before_new_stage.sort_order:
            stage.sort_order = count
            count += 1

    db.session.commit()
    return str(new_stage.stage_id)


@bp.route('/close_deal', methods=['GET'])
@login_required
def deal_modal_close():
    return render_template('deal/deal/modal_close.html',
                           stages=get_stages('end'),
                           deal=Deal.get(request.args.get('deal_id')))


@bp.route('/stage_settings', methods=['GET', 'POST'])
@login_required
def stage_settings():
    stage = DealStage.get(request.args.get('stage_id')) or DealStage(type='')

    if request.method == 'POST':
        return actions_in(stage)

    return render_template('deal/deals_modal_stage.html', stage=stage)


@bp.route('/employment_info', methods=['GET'])
@login_required
def employment():
    event = f"deal_{request.args.get('deal_id')}"
    employments = get_event_booking(event)
    return render_template('deal/deal/employment_info.html',
                           employments=employment_info(employments))
