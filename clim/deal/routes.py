import json
from datetime import datetime, timedelta
import locale

from flask import render_template, redirect, url_for, request, session
from flask_login import login_required

from ..utils import actions_in, json_dumps, json_loads
from ..stock.utils import get_consumables_categories_ids
from ..stock.models import Stock, StockProduct, Product
from ..jinja_filters import smart_int
from ..models import OptionValueDescription, ProductDescription, db, \
    Option, OptionValue, Category
from .models import Contact, Deal, DealService, DealStage, Worker, \
    WorkerEmployment
from .utils import get_contact, get_deal, get_stage, get_stages, sort_stage_deals
from . import bp


@bp.route('/update_filter', methods=['POST'])
def update_filter():
    session['stage_type'] = request.form.get('stage_type')
    return ''


@bp.route('/<string:view>', methods=['GET'])
@bp.route('/', methods=['GET'])
@login_required
def deals(view=None):
    if not view:
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
        result_products['children'].append(
            {'id': str(product.product_id),
             'text': product.description.name,
             'price': product.price,
             'type': 'product',
             'unit': product.unit}
        )
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
             'quantity': f'{smart_int(stock.quantity)} {unit}'}
        )

    result['pagination'] = {'more': bool(len(result['results']) >= per_page)}
    return json.dumps(result)


@bp.route('/ajax_contacts', methods=['GET'])
@login_required
def ajax_contacts():
    per_page = 20
    search = request.args.get('search')

    select = Contact.query

    if search:
        select = (select.where(Contact.name.contains(search) |
                               Contact.phone.contains(search) |
                               Contact.email.contains(search)))

    contacts = select.paginate(page=request.args.get('page', 1, type=int),
                               per_page=per_page, error_out=False)

    result = {'results': []}
    for contact in contacts:
        result['results'].append({'id': str(contact.contact_id),
                                  'text': contact.name,
                                  'phone': contact.phone,
                                  'email': contact.email})
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


@bp.route('/action', methods=['POST'])
@login_required
def deals_action():
    actions_in(request.data, get_deal)
    db.session.commit()
    return ''


@bp.route('/close_deal', methods=['GET'])
@login_required
def deal_modal_close():
    return render_template('deal/deal/modal_close.html',
                           stages=get_stages('end'),
                           deal=get_deal(request.args.get('deal_id')))


@bp.route('/deal_info', methods=['GET', 'POST'])
@login_required
def deal_info():
    deal_id = request.args.get('deal_id')
    if deal_id == 'last':
        deal = db.session.execute(
            db.select(Deal).order_by(Deal.deal_id.desc())).scalar()
    else:
        deal = get_deal(deal_id)

    if not deal:
        deal = Deal(date_add=datetime.now(),
                    stage=get_stage(stage_type='start'))

    if request.method == 'POST':
        db.session.add(deal)

        data = json_loads(request.data, {})
        info = {i['name']: i['value'] for i in data.get('info', {})}

        # Name
        deal.name = info.get('deal_name') or f'Сделка #{Deal.query.count()}'
        # Date
        # deal.date_end = info.get('date_end') or None
        date_end = info.get('date_end2')
        if date_end:
            date_end = datetime.strptime(date_end, '%d.%m.%Y %H:%M')
        deal.date_end = date_end or None
        # Sum
        deal.sum = info.get('deal_sum') or 0

        # Contact
        contact_id = info.get('contact_id')
        if contact_id:
            deal.contact_id = contact_id
        else:
            contact_name = info.get('contact_name', '')
            contact_phone = info.get('contact_phone', '')
            contact_email = info.get('contact_email', '')

            if contact_name or contact_phone or contact_email:
                contact = Contact(name=contact_name,
                                  phone=contact_phone,
                                  email=contact_email)
                db.session.add(contact)
                # db.session.commit()
                db.session.flush()
                deal.contact_id = contact.contact_id

        # Details
        deal.details = json.dumps({'adress': info.get('adress', ''),
                                   'what_need': info.get('what_need', ''),
                                   'date_service': info.get('date_service', ''),
                                   'deal_comment': info.get('deal_comment', '')})

        if not deal.posted:
            deal.products = json_dumps(data.get('products'), '')
            deal.consumables = json_dumps(data.get('consumables'), '')
            deal.expenses = json_dumps(data.get('expenses'), '')

        # ToDo Проверка смены статуса после постинга
        new_stage = get_stage(info['stages'])
        unposting = deal.completed and new_stage and 'end' not in new_stage.type
        posting = info.get('posting')

        # Stage
        if new_stage:
            if deal.stage.stage_id != new_stage.stage_id:
                deal.sort_order = 1
                sort_stage_deals(new_stage.stage_id, deal.deal_id, 0)
            if not (posting and unposting):
                deal.stage = new_stage

        # Сохранение перед постингом
        db.session.commit()

        # Posting or Unposting
        if unposting:
            if deal.unposting():
                deal.stage = new_stage
                db.session.commit()
        elif not deal.posted and posting:
            if deal.posting():
                deal.stage = new_stage
                db.session.commit()
        db.session.commit()

    return render_template('deal/deal/main.html', deal=deal,
                           stages=tuple(get_stages()))


@bp.route('/<int:deal_id>/employments', methods=['GET'])
@login_required
def deal_employments(deal_id):
    def employment_time(employment):
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        date_start = employment.date_start
        date_end = employment.date_end
        time_start = employment.time_start
        time_end = employment.time_end

        if date_start == date_end:
            date = f'{date_start.strftime("%d ")}{date_start.strftime("%B")}'
            year = date_start.year
            year = f' {year}' if year != datetime.now().year else ''

            time_start = time_start.strftime('%H:%M')
            time_end = time_end.strftime('%H:%M')
            time = f', {time_start} - {time_end}'
            return date + year + time

        year_start = date_start.year
        date_start = f'{date_start.strftime("%d ")}{date_start.strftime("%B")}'
        year_start = f' {year_start}' if year_start != datetime.now().year else ''

        year_end = date_end.year
        date_end = f'{date_end.strftime("%d ")}{date_end.strftime("%B")}'
        year_end = f' {year_end}' if year_end != datetime.now().year else ''

        time_start = time_start.strftime('%H:%M')
        time_end = time_end.strftime('%H:%M')

        return f'{date_start}{year_start}{time_start} - {date_end}{year_end}{time_end}'

    event = 'deal_' + str(deal_id)
    employments = WorkerEmployment.get(event)

    if employments == ():
        return '<span class="deal-info-edit-link-booking">Забронировать время</span>'

    result = ''
    worker_id = 0
    for e in employments:
        if e.worker_id != worker_id:
            result = f'<span class="deal-info-edit-link-worker">{e.worker.name}</span>'
            worker_id = e.worker_id

        result += f'<span class="deal-info-edit-link-date">{employment_time(e)}</span>'

    return result


@bp.route('/booking', methods=['GET'])
@login_required
def deal_booking():
    services = tuple(db.session.execute(db.select(DealService)).scalars())
    deal_id = request.args.get('deal_id')

    start_date = request.args.get('start_date')
    if not start_date:
        start_date = datetime.now().date().strftime('%Y-%m-%d')

    return render_template('deal/deal/booking.html',
                           start_date=start_date,
                           services=services,
                           deal_id=deal_id)


@bp.route('/booking_post', methods=['POST'])
@login_required
def deal_booking_post():
    def str_date(str):
        return datetime.strptime(str, '%Y-%m-%d')

    # deal_id = request.args.get('deal_id')
    data = json.loads(request.data) if request.data else None

    for worker in data:
        if not worker.get('schedule'):
            continue

        for schedule in worker.get('schedule'):
            if schedule.get('employmentId'):
                employment = db.session.execute(
                    db.select(WorkerEmployment)
                    .filter(WorkerEmployment.employment_id == schedule.get('employmentId'))).scalar()
            else:
                employment = WorkerEmployment()
                db.session.add(employment)

            if schedule.get('delete'):
                db.session.delete(employment)
                continue

            employment.title = schedule.get('text')
            employment.worker_id = worker.get('worker_id')
            employment.event = schedule.get('event'),
            employment.time_start = schedule.get('start')
            employment.time_end = schedule.get('end')
            employment.date_start = str_date(schedule.get('startDate'))
            employment.date_end = str_date(schedule.get('endDate'))

    db.session.commit()

    return ''


@bp.route('/booking_data', methods=['GET'])
@login_required
def booking_data():
    def str_date(str):
        return datetime.strptime(str, '%Y-%m-%d').date()

    date = request.args.get('date')
    date_start = str_date(date) if date else datetime.now().date()
    date_end = date_start + timedelta(days=14)

    deal_id = request.args.get('deal_id')

    workers = db.session.execute(db.select(Worker)).scalars()
    rows = {}
    count = 0

    for worker in workers:
        schedule = []
        for employment in worker.employments:
            if ((employment.date_start < date_start and employment.date_end < date_start)
                    or (employment.date_start > date_end and employment.date_end > date_end) ):
                continue

            schedule.append({
                'employment_id': employment.employment_id,
                'event': employment.event,
                'start': str(employment.time_start),
                'end': str(employment.time_end),
                'date_start': employment.date_start,
                'date_end': employment.date_end,
                'text': str(employment.title),
                'data': {
                }
            })
        rows[count] = {
            'title': worker.name,
            'worker_id': worker.worker_id,
            'schedule': schedule
        }
        count += 1

    return rows


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


@bp.route('/clients', methods=['GET', 'POST'])
@login_required
def contacts():
    if request.method == 'POST':
        # Действия
        actions_in(request.data, get_contact)
        db.session.commit()
        return ''

    contacts = db.session.execute(db.select(Contact)).scalars()
    return render_template('deal/contacts.html', contacts=contacts)


@bp.route('/contact_info', methods=['GET', 'POST'])
@login_required
def contact_info():
    role = request.args.get('role', '')
    contact = get_contact(request.args.get('contact_id')) or Contact(role=role)

    if request.method == 'POST':
        if not contact.contact_id:
            db.session.add(contact)

        contact.name = request.form.get('name', '')
        contact.phone = request.form.get('phone', '')
        contact.email = request.form.get('email', '')
        contact.role = request.form.get('role', '')
        db.session.commit()
        return ''

    return render_template('deal/contact/main.html', contact=contact)
