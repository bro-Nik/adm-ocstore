import json
# import os
# from alembic.op import f
from flask import render_template, redirect, url_for, request, session, flash,\
    Blueprint
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import locale
from clim.jinja_filters import smart_int

from clim.models import OptionValueDescription, ProductDescription, db, Contact, Deal, DealService, DealStage, Option,\
    OptionValue, Stock, StockProduct, User, Worker, WorkerEmployment, Product,\
    Module, Category


deal = Blueprint('deal', __name__, template_folder='templates', static_folder='static')


def get_products():
    return db.session.execute(db.select(Product)).scalars()


def get_stocks():
    return db.session.execute(db.select(Stock)).scalars()


def get_stages():
    return db.session.execute(
        db.select(DealStage).order_by(DealStage.sort_order)).scalars()


def get_consumables():
    """ Получить расходные материалы """
    settings = {}
    settings_in_base = db.session.execute(
        db.select(Module).filter_by(name='crm_stock')).scalar()

    if settings_in_base.value:
        settings = json.loads(settings_in_base.value)

    ids = settings.get('consumables_categories_ids')

    request_base = Product.query
    request_base = (request_base.join(Product.categories)
                   .where(Category.category_id.in_(ids)))
    request_base = request_base.order_by(Product.mpn)

    return request_base.all()


def get_deal(deal_id):
    return db.session.execute(
        db.select(Deal).filter(Deal.deal_id == deal_id)).scalar()


def get_option_value(id):
    return db.session.execute(
        db.select(OptionValue).filter_by(option_value_id=id)).scalar()


def json_dumps_or_other(data, default=None):
    return json.dumps(data, ensure_ascii=False) if data else default


def json_loads_or_other(data, default=None):
    return json.loads(data) if data else default


@deal.route('/update_filter', methods=['POST'])
def update_filter():
    session['stage_type'] = request.form.get('stage_type')
    return ''


@deal.route('/<string:view>', methods=['GET'])
@deal.route('/', methods=['GET'])
@login_required
def deals(view=None):
    if not view:
        view = session.get('crm_view')
        return redirect (url_for('.deals', view=view if view else 'kanban'))

    session['crm_view'] = view
    stage_type = session.get('stage_type')
    stage_type = stage_type if stage_type else 'in_work'

    if 'in_work' in stage_type and 'end' in stage_type or stage_type == '[]':
        request = db.select(DealStage)
    elif 'in_work' in stage_type:
        request = db.select(DealStage).filter(DealStage.type != 'end_good',
                                             DealStage.type != 'end_bad')
    elif 'end' in stage_type:
        request = db.select(DealStage).filter((DealStage.type == 'end_good')
                                            | (DealStage.type == 'end_bad'))

    stages = db.session.execute(request.order_by(DealStage.sort_order)).scalars()

    page = 'deal/deals_' + view + '.html'
    return render_template(page,
                           stages=tuple(stages),
                           stage_type=stage_type)


@deal.route('/ajax_products', methods=['GET'])
@login_required
def ajax_products():
    per_page = 20
    search = request.args.get('search')
    result_count = 0
    result = {'results': []}

    # Products
    request_products = Product.query
    if search:
        request_products = (request_products.join(Product.description)
                   .where(ProductDescription.name.contains(search)))
    else:
        request_products = request_products.filter(Product.stocks != None)

    products = request_products.paginate(page=int(request.args.get('page')),
                                 per_page=per_page,
                                 error_out=False)


    result_products = {'text': 'Товары', 'children': []}
    for product in products:
        result_products['children'].append(
            {
                'id': str(product.product_id),
                'text': product.description.name,
                'price': product.price,
                'type': 'product',
                'unit': product.unit_class.description.unit
            }
        )
    if len(result_products['children']):
        result['results'].append(result_products)
        result_count += len(result_products['children'])


    # Options
    # options = db.session.execute(db.select(Option)).scalars()
    request_options = Option.query
    if search:
        request_options = (request_options.join(Option.values)
                           .join(OptionValue.description)
                           .where(OptionValueDescription.name.contains(search)))

    options = request_options.paginate(page=int(request.args.get('page')),
                                                 per_page=per_page,
                                                 error_out=False)
    result_options = {'text': 'Услуги', 'children': []}
    for option in options:
        for value in option.values:
            price = smart_int(value.settings.price) if value.settings else 0
            result_options['children'].append(
                {
                    'id': str(value.option_value_id),
                    'text': value.description.name,
                    'price': price,
                    'type': 'service'
                }
            )
    if len(result_options['children']):
        result['results'].append(result_options)
        result_count += len(result_options['children'])

    more = result_count >= per_page
    result['pagination'] = {'more': more}

    return json.dumps(result)


@deal.route('/ajax_consumables', methods=['GET'])
@login_required
def ajax_consumables():
    per_page = 20
    search = request.args.get('search')
    result = {'results': []}

    settings = {}
    settings_in_base = db.session.execute(
        db.select(Module).filter_by(name='crm_stock')).scalar()

    if settings_in_base.value:
        settings = json.loads(settings_in_base.value)

    ids = settings.get('consumables_categories_ids')

    request_base = Product.query
    request_base = (request_base.join(Product.categories)
                   .where(Category.category_id.in_(ids)))

    if search:
        request_base = (request_base.join(Product.description)
                   .where(ProductDescription.name.contains(search)))

    consumables = request_base.paginate(page=int(request.args.get('page')),
                                 per_page=per_page,
                                 error_out=False)

    for product in consumables:
        result['results'].append(
            {
                'id': str(product.product_id),
                'text': product.description.name,
                'price': product.price,
                'type': 'product',
                'unit': product.unit_class.description.unit
            }
        )
    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}

    return json.dumps(result)


@deal.route('/ajax_stocks_first', methods=['GET'])
@login_required
def ajax_stocks_first():
    product_id = request.args.get('product_id')
    stock_id = request.args.get('stock_id')

    request_base = (db.select(StockProduct)
        .filter(StockProduct.product_id == product_id))

    if stock_id:
        request_base = request_base.filter(StockProduct.stock_id == stock_id)
    else:
        request_base = request_base.filter(StockProduct.quantity > 0)

    stock = db.session.execute(request_base).scalar()

    result = {}
    if not stock:
        return ''

    result['id'] = str(stock.stock_id) if stock else ''
    result['text'] = stock.stock.name if stock else ''
    result['quantity'] = (str(smart_int(stock.quantity)) + ' '
                            + stock.main_product.unit_class.description.unit) if stock else ''
    return json.dumps(result)


@deal.route('/ajax_stocks', methods=['GET'])
@login_required
def ajax_stocks():
    search = request.args.get('search')
    product_id = request.args.get('product_id')
    per_page = 20
    result = {'results': []}

    request_stocks = (StockProduct.query
                      .where(StockProduct.product_id == product_id))
    if search:
        request_stocks = (request_stocks.join(StockProduct.stock)
            .where(Stock.name.contains(search)))
    else:
        request_stocks = (request_stocks
                       .where(StockProduct.quantity > 0))

    stocks = request_stocks.paginate(page=int(request.args.get('page')),
                                     per_page=per_page,
                                     error_out=False)

    for stock in stocks:
        result['results'].append(
            {
                'id': str(stock.stock_id),
                'text': stock.stock.name,
                'quantity': (str(smart_int(stock.quantity)) + ' '
                            + stock.main_product.unit_class.description.unit) if stock else ''
            }
        )

    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}
    return json.dumps(result)


@deal.route('/ajax_contacts', methods=['GET'])
@login_required
def ajax_contacts():
    per_page = 20
    search = request.args.get('search')
    result = {'results': []}

    request_base = Contact.query

    if search:
        request_base = (request_base
                       .where(Contact.name.contains(search)
                              | Contact.phone.contains(search)
                              | Contact.email.contains(search)))

    contacts = request_base.paginate(page=int(request.args.get('page')),
                                 per_page=per_page,
                                 error_out=False)

    for contact in contacts:
        result['results'].append(
            {
                'id': str(contact.contact_id),
                'text': contact.name,
                'phone': contact.phone,
                'email': contact.email
            }
        )
    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}

    return json.dumps(result)


@deal.route('/update_stage', methods=['GET'])
@deal.route('/update_stage/<int:stage_id>/<int:deal_id>/<int:previous_deal_sort>', methods=['GET'])
@login_required
def update_stage(stage_id=None, deal_id=None, previous_deal_sort=0):
    deal = get_deal(deal_id)
    deal.stage_id = stage_id
    deal.sort_order = previous_deal_sort + 1
    db.session.commit()

    sort_stage_deals(stage_id, deal_id, previous_deal_sort)

    return redirect(url_for('.deals', view=session.get('crm_view')))


def sort_stage_deals(stage_id, deal_id, previous_deal_sort):
    def number(number):
        try:
            return int(number)
        except:
            return 0

    previous_deal_sort = number(previous_deal_sort)

    stage = get_stage(stage_id)

    for deal_in_stage in stage.deals:
        deal_in_stage.sort_order = number(deal_in_stage.sort_order)

        if (deal_in_stage.sort_order > previous_deal_sort
            and deal_in_stage.deal_id != deal_id):
            deal_in_stage.sort_order += 1
    db.session.commit()

    count = 1
    for deal_in_stage in stage.deals:
        deal_in_stage.sort_order = count
        count += 1
    db.session.commit()


def get_stage(stage_id):
    return db.session.execute(
        db.select(DealStage).filter(DealStage.stage_id == stage_id)).scalar()


@deal.route('/new_stage', methods=['GET'])
@deal.route('/new_stage/<int:stage_id>', methods=['GET'])
@login_required
def new_stage(stage_id=None):
    before_new_stage = db.session.execute(
        db.select(DealStage).filter(DealStage.stage_id == stage_id)).scalar()

    stages = get_stages()

    new_stage = DealStage(name='Новая стадия',
                          type='',
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


@deal.route('/stage_info/update', methods=['POST'])
@login_required
def stage_update():
    stage_id = request.form.get('stage_id')

    stage = get_stage(stage_id)
    stage.name = request.form.get('name')
    stage.type = request.form.get('type')
    stage.color = request.form.get('color')

    db.session.commit()
    return redirect(url_for('deals2'))


@deal.route('/action', methods=['POST'])
@login_required
def deals_action():
    data = json.loads(request.data) if request.data else {}

    action = data.get('action')
    ids = data.get('ids')

    if action == 'delete_column':
        stage = get_stage(ids)
        if stage:
            db.session.delete(stage)

    elif action == 'delete_deals':
        for id in ids:
            deal = get_deal(id)
            db.session.delete(deal)

    db.session.commit()
    return redirect(url_for('.deals'))


@deal.route('/deal_info_placeholder', methods=['GET'])
@login_required
def deal_info_placeholder():
    return render_template('deal/deal_placeholder.html')


@deal.route('/deal_info', methods=['GET'])
@login_required
def deal_info():
    deal = get_deal(request.args.get('deal_id'))
    contacts = db.session.execute(db.select(Contact)).scalars()

    return render_template('deal/deal.html',
                           deal=deal,
                           stages=tuple(get_stages())
                           )


@deal.route('/deal_info', methods=['POST'])
@login_required
def deal_info_update():
    deal = get_deal(request.args.get('deal_id'))
    if not deal:
        deal = Deal(date_add=datetime.now())
        db.session.add(deal)

    data = json_loads_or_other(request.data, {}) 

    action = data.get('action')

    info_list = data.get('info') if data.get('info') else {}
    info = {}
    if info_list:
        for item in info_list:
            info[item['name']] = item['value']

    # Name
    deal_name = info.get('deal_name')
    if not deal_name:
        deal_name = 'Сделка #' + str(Deal.query.count())
    deal.name = deal_name

    # Date
    date_end = info.get('date_end')
    if date_end:
        deal.date_end = date_end

    # Sum
    deal_sum = info.get('deal_sum')
    deal.sum = deal_sum if deal_sum else 0

    # Contact
    contact_id = info.get('contact_id')
    if contact_id:
        deal.contact_id = contact_id
    else:
        contact_name = info.get('contact_name')
        contact_phone = info.get('contact_phone')
        contact_email = info.get('contact_email')

        if contact_name or contact_phone or contact_email:
            contact = Contact(
                name=contact_name if contact_name else '',
                phone=contact_phone if contact_phone else '',
                email=contact_email if contact_email else ''
            )
            db.session.add(contact)
            db.session.commit()
            deal.contact_id = contact.contact_id

    # Details
    details = {}
    if info.get('adress'):
        details['adress'] = info.get('adress')
    if info.get('what_need'):
        details['what_need'] = info.get('what_need')
    if info.get('date_service'):
        details['date_service'] = info.get('date_service')
    if info.get('deal_comment'):
        details['deal_comment'] = info.get('deal_comment')
    
    deal.details = json.dumps(details)

    # Products
    deal.products = json_dumps_or_other(data.get('products'))

    # Consumables
    deal.consumables = json_dumps_or_other(data.get('consumables'))

    # Expenses
    deal.expenses = json_dumps_or_other(data.get('expenses'))

    # Stage
    old_stage_id = info.get('old_stage')
    new_stage_id = info.get('stages')

    posting = info.get('posting')
    if posting:
        deal.stage_id = old_stage_id
    db.session.commit()
    deal.stage_id = new_stage_id

    if old_stage_id != new_stage_id:
        deal.sort_order = 1
        sort_stage_deals(new_stage_id, deal.deal_id, 0)

    # Posting
    if not deal.posted and info.get('posting'):
        error = deal_posting(deal)
        if error:
            return redirect(url_for('deal_info', deal_id=deal.deal_id))

    db.session.commit()

    return redirect(url_for('.deal_info', deal_id=deal.deal_id))


def deal_posting(deal):
    def change_quantity(products):
        nonlocal not_stock_id
        cost_price = 0
        for product in products:
            if product.get('type') == 'service':
                service = get_option_value(product['product_id'])
                product['product_name'] = service.description.name

            else:
                if not product.get('stock_id'):
                    not_stock_id = True
                    break

                quantity = product.get('quantity')
                
                product_in_stock = get_product_in_stock(product['product_id'],
                                                        product['stock_id'])
                product_in_stock.quantity -= quantity

                product['stock_name'] = product_in_stock.stock.name
                product['product_name'] = product_in_stock.main_product.description.meta_h1
                product['unit'] = product_in_stock.main_product.unit_class.description.unit

                # to analytics
                cost_price += product_in_stock.main_product.cost * quantity

                # delete product if quantity 0
                if product_in_stock.quantity == 0:
                    db.session.delete(product_in_stock)

        return json.dumps(products), cost_price

    not_stock_id = False
    cost_price_products = 0
    if deal.products:
        deal.products, cost_price_products = change_quantity(json.loads(deal.products))

    cost_price_consumables = 0
    if deal.consumables:
        deal.consumables, cost_price_consumables = change_quantity(json.loads(deal.consumables))

    if not_stock_id:
        return 'Заполните склады списания'

    # Date
    if not deal.date_end:
        deal.date_end = datetime.now().date()

    # Employments
    details = json.loads(deal.details) if deal.details else {}
    
    event = 'deal_' + str(deal.deal_id)
    employments = get_employments(event)
    details['employments'] = []
    for employment in employments:
        details['employments'].append(employment.worker.name)
        db.session.delete(employment)
    deal.details = json.dumps(details)


    # Analytics
    cost_price_expenses = 0
    if deal.expenses:
        for expense in json.loads(deal.expenses):
            cost_price_expenses += expense.get('sum')

    all_cost_price = (cost_price_products + cost_price_consumables
                      + cost_price_expenses)
    deal.profit = deal.sum - all_cost_price

    analytics = {
        'Товары': cost_price_products,
        'Расходные материалы': cost_price_consumables,
        'Прочие расходы': cost_price_expenses
    }

    analytics = json.dumps(analytics)
    deal.analytics = analytics

    deal.posted = True
    return ''

def get_employments(event):
    return db.session.execute(
            db.select(WorkerEmployment)
            .filter(WorkerEmployment.event == event)).scalars()


@deal.route('/<int:deal_id>/employments', methods=['GET'])
@login_required
def deal_employments(deal_id):
    def employment_time(employment):
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        date_start = employment.date_start
        date_end = employment.date_end    
        time_start = employment.time_start
        time_end = employment.time_end

        if date_start == date_end:
            date = str(date_start.strftime('%d ')) + date_start.strftime('%B')
            year = date_start.year
            year = ' ' + str(year) if year != datetime.now().year else ''

            time_start = str(time_start.strftime('%H:%M'))
            time_end = str(time_end.strftime('%H:%M'))
            time = ', ' + time_start + ' - ' + time_end

            return date + year + time
        else:
            year_start = date_start.year
            date_start = str(date_start.strftime('%d ')) + date_start.strftime('%B')
            year_start = ' ' + str(year_start) if year_start != datetime.now().year else ''

            year_end = date_end.year
            date_end = str(date_end.strftime('%d ')) + date_end.strftime('%B')
            year_end = ' ' + str(year_end) if year_end != datetime.now().year else ''

            time_start = str(time_start.strftime('%H:%M'))
            time_end = str(time_end.strftime('%H:%M'))

            return date_start + year_start + time_start + ' - ' + date_end + year_end + time_end


    event = 'deal_' + str(deal_id)
    employments = tuple(get_employments(event))

    if employments == ():
        return '<span class="deal-info-edit-link-booking">Забронировать время</span>'
    else:
        result = ''
        worker_id = 0
        for employment in employments:
            if employment.worker_id != worker_id:
                result += '<span class="deal-info-edit-link-worker">'
                result += employment.worker.name
                result += '</span>'
                worker_id = employment.worker_id

            result += '<span class="deal-info-edit-link-date">'
            result += employment_time(employment)
            result += '</span>'

    return result


@deal.route('/booking', methods=['GET'])
@login_required
def deal_booking():
    services = db.session.execute(db.select(DealService)).scalars()
    deal_id = request.args.get('deal_id')

    start_date = request.args.get('start_date')
    if not start_date:
        start_date = datetime.now().date().strftime('%Y-%m-%d')

    return render_template('deal/deal_booking.html',
                           start_date=start_date,
                           services=services,
                           deal_id=deal_id)


@deal.route('/booking_post', methods=['POST'])
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


@deal.route('/booking_data', methods=['GET'])
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


def get_product_in_stock(product_id, stock_id):
    return db.session.execute(
        db.select(StockProduct)
        .filter_by(product_id=product_id, stock_id=stock_id)).scalar()
