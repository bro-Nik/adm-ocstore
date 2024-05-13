import json
from datetime import datetime, time

from flask import abort, render_template, redirect, url_for, request, session
from flask_login import login_required

from clim.utils import actions_in
from clim.crm.booking.utils import get_event_booking

from ..stock.utils import get_consumables_categories_ids
from ..stock.models import Stock, StockProduct
from ..utils import smart_int
from ..models import Product, db, OptionValueDescription, ProductDescription, \
    Option, OptionValue, Category
from .models import Deal, DealStage
from .utils import employment_info, get_deal, get_stage, get_stages, sort_stage_deals
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
        actions_in(request.data, get_deal)
        db.session.commit()
        return ''

    if not view or view not in ['kanban', 'list']:
        view = session.get('crm_view', 'kanban')
        return redirect(url_for('.deals', view=view))

    session['crm_view'] = view
    stage_type = session.get('stage_type', 'in_work')
    return render_template(f'deal/deals_{view}.html', stage_type=stage_type,
                           stages=tuple(get_stages(stage_type)))


@bp.route('/ajax_products', methods=['GET'])
@login_required
def ajax_products():
    search = request.args.get('search')
    result_count = 0
    result = {'results': []}

    # Products
    select_p = Product.query

    # not Consumables
    consumables_cat_ids = get_consumables_categories_ids()
    select_p = (select_p.join(Product.categories)
                .where(Category.category_id.notin_(consumables_cat_ids)))

    if search:
        select_p = (select_p.join(Product.description)
                    .where(ProductDescription.name.contains(search)))
    else:
        select_p = select_p.filter(Product.stocks != None)

    products = select_p.paginate(page=request.args.get('page', 1, type=int),
                                 per_page=20, error_out=False)

    result_products = {'text': 'Товары', 'children': []}
    for product in products:
        result_products['children'].append({'id': str(product.product_id),
                                            'text': product.name,
                                            'price': product.price,
                                            'type': 'product',
                                            'unit': product.unit})
    if result_products['children']:
        result['results'].append(result_products)
        result_count += len(result_products['children'])

    # Options
    # options = db.session.execute(db.select(Option)).scalars()
    select_o = Option.query
    if search:
        select_o = (select_o.join(Option.values).join(OptionValue.description)
                    .where(OptionValueDescription.name.contains(search)))

    options = select_o.paginate(page=request.args.get('page', 1, type=int),
                                per_page=20, error_out=False)
    result_options = {'text': 'Услуги', 'children': []}
    for option in options:
        for value in option.values:
            price = smart_int(value.settings.price) if value.settings else 0
            result_options['children'].append(
                {'id': str(value.option_value_id),
                 'text': value.description.name,
                 'price': price,
                 'type': 'service'}
            )
    if result_options['children']:
        result['results'].append(result_options)
        result_count += len(result_options['children'])

    result['pagination'] = {'more': bool(result_count >= 20)}

    return json.dumps(result)


@bp.route('/ajax_consumables', methods=['GET'])
@login_required
def ajax_consumables():
    search = request.args.get('search')
    result = {'results': []}

    select = (Product.query.join(Product.categories)
              .where(Category.category_id.in_(get_consumables_categories_ids())))

    if search:
        select = (select.join(Product.description)
                  .where(ProductDescription.name.contains(search)))

    consumables = select.paginate(page=request.args.get('page', 1, type=int),
                                  per_page=20, error_out=False)

    for product in consumables:
        result['results'].append({'id': str(product.product_id),
                                  'text': product.description.name,
                                  'price': product.cost,
                                  'type': 'product',
                                  'unit': product.unit})
    result['pagination'] = {'more': bool(len(result['results']) >= 20)}

    return json.dumps(result)


@bp.route('/ajax_stocks_first', methods=['GET'])
@login_required
def ajax_stocks_first():
    product_id = request.args.get('product_id')
    stock_id = request.args.get('stock_id')

    select = (db.select(StockProduct).filter_by(product_id=product_id))
    if stock_id:
        select = select.filter(StockProduct.stock_id == stock_id)
    else:
        select = select.filter(StockProduct.quantity > 0)

    stock = db.session.execute(select).scalar()
    if not stock:
        return ''

    unit = stock.main_product.unit
    return json.dumps({'id': str(stock.stock_id),
                       'text': stock.stock.name,
                       'quantity': f'{smart_int(stock.quantity)} {unit}'})


@bp.route('/ajax_stocks', methods=['GET'])
@login_required
def ajax_stocks():
    search = request.args.get('search')
    product_id = request.args.get('product_id')
    per_page = 20

    select = StockProduct.query.where(StockProduct.product_id == product_id)
    if search:
        select = (select.join(StockProduct.stock)
                  .where(Stock.name.contains(search)))
    else:
        select = select.where(StockProduct.quantity > 0)

    stocks = select.paginate(page=request.args.get('page', 1, type=int),
                             per_page=per_page, error_out=False)

    result = {'results': []}
    for stock in stocks:
        unit = stock.main_product.unit
        result['results'].append(
            {'id': str(stock.stock_id),
             'text': stock.stock.name,
             'quantity': f'{smart_int(stock.quantity)} {unit}',
             'subtext': f'{smart_int(stock.quantity)} {unit}'}
        )

    result['pagination'] = {'more': bool(len(result['results']) >= per_page)}
    return json.dumps(result)


@bp.route('/update_stage', methods=['GET'])
@login_required
def update_stage():
    deal = get_deal(request.args.get('deal_id'))
    deal.stage_id = request.args.get('stage_id')
    deal.sort_order = request.args.get('stage_id', 0, type=int) + 1
    db.session.commit()

    sort_stage_deals(deal.stage_id, deal.deal_id, deal.previous_deal_sort)
    return redirect(url_for('.deals'))


@bp.route('/new_stage', methods=['GET'])
@login_required
def new_stage():
    before_new_stage = get_stage(request.args.get('stage_id'))
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


@bp.route('/stage_info/update', methods=['POST'])
@login_required
def stage_update():
    stage = get_stage(request.form.get('stage_id'))
    if stage:
        stage.name = request.form.get('name')
        stage.type = request.form.get('type')
        stage.color = request.form.get('color')
        db.session.commit()

    return redirect(url_for('deals'))


@bp.route('/close_deal', methods=['GET'])
@login_required
def deal_modal_close():
    return render_template('deal/deal/modal_close.html',
                           stages=get_stages('end'),
                           deal=get_deal(request.args.get('deal_id')))


@bp.route('/deal_info', methods=['GET', 'POST'])
@login_required
def deal_info():
    deal = get_deal(request.args.get('deal_id'))
    if not deal:
        deal = Deal(date_add=datetime.now(),
                    stage=get_stage(stage_type='start'))

    if request.method == 'POST':
        if not deal.deal_id:
            db.session.add(deal)

        deal.data = json.loads(request.data) if request.data else {}
        deal.save()

        # ToDo Проверка смены статуса после постинга
        new_stage = get_stage(deal.data['info']['stage_id']) or abort(404)
        unposting = deal.posted and deal.stage.type != new_stage.type
        posting = new_stage.type == 'end_good' and not deal.posted

        # Stage
        if deal.stage.stage_id != new_stage.stage_id:
            deal.sort_order = 1
            sort_stage_deals(new_stage.stage_id, deal.deal_id, 0)

        # Если не будет постинга применяем стадию
        if not (posting or unposting):
            deal.stage = new_stage

        # Сохранение перед постингом
        db.session.commit()

        # Posting or Unposting
        if unposting:
            deal.unposting()
            # Если прошло - сохраняемся
            if not deal.posted:
                deal.stage = new_stage
                db.session.commit()
        elif posting:
            deal.posting()
            # Если прошло - сохраняемся
            if deal.posted:
                deal.stage = new_stage
                db.session.commit()
        return {'redirect': str(url_for('.deal_info', deal_id=deal.deal_id))}

    return render_template('deal/deal/main.html', deal=deal,
                           stages=tuple(get_stages()))


@bp.route('/stage_settings', methods=['GET', 'POST'])
@login_required
def stage_settings():
    stage = get_stage(request.args.get('stage_id')) or DealStage(type='')
    if request.method == 'POST':
        if stage:
            stage.name = request.form.get('name')
            stage.type = request.form.get('type')
            stage.color = request.form.get('color')
            db.session.commit()
        data = json.loads(request.data) if request.data else {}
        info = data.get('info')

    return render_template('deal/deals_modal_stage.html', stage=stage)


@bp.route('/employment_info', methods=['GET'])
@login_required
def employment():
    event = f"deal_{request.args.get('deal_id')}"
    employments = get_event_booking(event)
    return render_template('deal/deal/employment_info.html',
                           employments=employment_info(employments))
