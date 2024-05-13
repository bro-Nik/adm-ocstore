import json
import pickle
from flask import redirect, render_template, request, url_for
from flask_login import login_required

from clim.utils import get_module
from clim.models import Attribute, AttributeDescription, Category, Manufacturer, Module, Product

from ..app import db, redis
from . import bp


# @bp.route('/', methods=['GET'])
# def main_redirect():
#     return redirect(url_for('crm.stock.products'))


@bp.route('/ajax/list_all_categories', methods=['GET'])
@login_required
def get_list_all_categories():
    search = request.args.get('search')

    result = {'results': []}

    query_redis = redis.get('all_categories')
    if query_redis:
        result = pickle.loads(query_redis)
        results = result['results']

    else:
        results = []
        line = -1

        def next(parent_id=0, line=0):
            line += 1
            categories = db.session.execute(
                db.select(Category).filter_by(parent_id=int(parent_id))).scalars()

            for category in categories:
                results.append(
                    {
                        'id': str(category.category_id),
                        'text': ' - ' * line + category.description.name
                    }
                )
                next(parent_id=category.category_id,
                     line=line)

        next(line=line)

        result['results'] = results
        redis.set('all_categories', pickle.dumps(result))

    if search:
        result['results'] = []
        for category in results:
            if search.lower() in category['text'].lower():
                result['results'].append(category)

    return json.dumps(result, ensure_ascii=False)


@bp.route('/ajax/list_all_manufacturers', methods=['GET'])
@login_required
def get_list_all_manufacturers():
    per_page = 20
    search = request.args.get('search')
    result = {'results': []}

    request_base = Manufacturer.query

    if search:
        request_base = (request_base
                        .where(Manufacturer.name.contains(search)))

    manufacturers = request_base.paginate(page=request.args.get('page', 1, type=int),
                                          per_page=per_page, error_out=False)

    for manufacturer in manufacturers:
        result['results'].append({'id': str(manufacturer.manufacturer_id),
                                  'text': manufacturer.name})

    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}

    return json.dumps(result)


@bp.route('/ajax/list_all_attributes', methods=['GET'])
@login_required
def get_list_all_attributes():
    per_page = 20
    search = request.args.get('search')
    result = {'results': []}
    result['results'].append({'id': '0',
                              'text': 'Нет'})

    request_base = Attribute.query.where(Attribute.description)

    if search:
        request_base = (request_base.join(Attribute.description)
                        .where(AttributeDescription.name.contains(search)))

    attributes = request_base.paginate(page=request.args.get('page', 1, type=int),
                                       per_page=per_page,
                                       error_out=False)

    for attribute in attributes:
        result['results'].append({'id': str(attribute.attribute_id),
                                  'text': attribute.description.name})

    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}

    return json.dumps(result)


def get_consumables():
    """ Получить с расходные материалы """
    settings_in_base = get_module('crm_stock')
    settings = {}
    if settings_in_base.value:
        settings = json.loads(settings_in_base.value)
    ids = settings.get('consumables_categories_ids')

    request_base = Product.query

    request_base = (request_base.join(Product.categories)
                   .where(Category.category_id.in_(ids)))

    request_base = request_base.order_by(Product.mpn)

    return request_base.all()


def get_manufacturers(filter={}):
    request_base = Manufacturer.query.order_by(Manufacturer.name)

    if filter.get('stock'):
        stock = filter.get('stock')
        if stock == 'in stock on order':
            request_base = (request_base
                .join(Manufacturer.products).filter(Product.quantity > 0))
        elif stock == 'in stock':
            request_base = (request_base
                .join(Manufacturer.products).filter((Product.quantity > 0)
                                               & (Product.price != 100001)))
        elif stock == 'not in stock':
            request_base = (request_base
                .join(Manufacturer.products).filter(Product.quantity == 0))
        elif stock == 'on order':
            request_base = (request_base
                .join(Manufacturer.products).filter(Product.price == 100001))

    if filter.get('categories_ids'):
        categories_ids = filter.get('categories_ids')
        request_base = (request_base.join(Manufacturer.products)
                .join(Product.categories)
                .filter(Category.category_id.in_(categories_ids)))

    return request_base.all()




@bp.route('/del_not_confirm_products', methods=['GET', 'POST'])
@login_required
def del_not_confirm_products():

    other_products = tuple(db.session.execute(db.select(OtherProduct)).scalars())
    for other_product in other_products:
        if not other_product.link_confirmed and other_product.product_id:
            other_product.product_id = 0
    db.session.commit()

    page = request.args.get('page')
    return redirect(url_for('products', path='comparison', page=page))


@bp.route('/work_plan_fields', methods=['POST'])
@login_required
def work_plan_fields():
    data = json_loads_or_other(request.data, {})

    module = get_module('work_plan')
    if not module:
        module = Module(name='work_plan')
        db.session.add(module)

    module_data = json_loads_or_other(module.value, {})
    fields = module_data.get('fields', [])

    def new_id():
        id = 1
        for field in fields:
            if field['id'] >= id:
                id = field['id'] + 1
        return id

    for item in data:
        if not item.get('name'):
            continue

        # delete
        if item['name'] == 'Удалить':
            for field in fields:
                if field['id'] == item['id']:
                    fields.remove(field)
                    break
            for category in module_data:
                if category == 'fields':
                    continue
                for manufacturer in module_data[category]:
                    id = str(item['id'])
                    if not id in module_data[category][manufacturer]:
                        continue
                    module_data[category][manufacturer].remove(id)

        # new
        if not item.get('id'):
            fields.append(
                {'id': new_id(),
                 'name': item['name']}
            )

        # update
        else:
            for field in fields:
                if field['id'] == item['id']:
                    field['name'] = item['name']
                    break

    module_data['fields'] = fields
    module.value = json.dumps(module_data)
    db.session.commit()
    return redirect(url_for('work_plan'))

@bp.route('/site/work_plan', methods=['GET', 'POST'])
@login_required
def work_plan():
    manufacturers_ids = request.form.getlist('manufacturers_ids')

    category_id = request.form.get('category_id')
    category = db.select(Category)
    if category_id:
        category = category.filter_by(category_id=category_id)
    category = db.session.execute(category).scalar()

    module = get_module('work_plan')
    module_data = json.loads(module.value) if module and module.value else {}
    fields = module_data.get('fields', {})
    if not module_data.get(category_id):
        module_data[category_id] = {}

    request_base = (Manufacturer.query.join(Manufacturer.products)
        .join(Product.categories)
        .where(Category.category_id == category.category_id))
    manufacturers = request_base.order_by(Manufacturer.name).all()

    if request.method == 'POST':
        if not module:
            module = Module(name='work_plan')
            db.session.add(module)

        data = json.loads(request.data) if request.data else {}
        action = data.get('action')
        if action == 'save':
            fields = data.get('ids')
            for field_list in fields:
                field_list = field_list.split('--')
                manufacturer = field_list[0]
                field = field_list[1]

                if not module_data[category_id].get(manufacturer):
                    module_data[category_id][manufacturer] = []

                module_data[category_id][manufacturer].append(field)

        elif action == 'clean':
            module_data.pop(category_id, None)

        module.value = json.dumps(module_data)
        db.session.commit()
        return ''

    return render_template('work_plan.html',
                           work_plan=work_plan,
                           category=category,
                           manufacturers_ids=manufacturers_ids,
                           manufacturers=tuple(manufacturers),
                           fields=fields)


@bp.route('/stock_statuses', methods=['GET'])
@login_required
def stock_statuses():
    stock_statuses = db.session.execute(db.select(StockStatus)).scalars()

    settings_in_base = db.session.execute(
        db.select(Module).filter_by(name='stock_statuses')).scalar()
    settings = {}
    if settings_in_base:
        settings = json.loads(settings_in_base.value)

    return render_template('stock_statuses.html',
                           stock_statuses=stock_statuses,
                           settings=settings)


@bp.route('/stock_statuses_action', methods=['POST'])
@login_required
def stock_statuses_action():
    settings_in_base = db.session.execute(
        db.select(Module).filter_by(name='stock_statuses')).scalar()

    settings = {}
    if settings_in_base:
        settings = json.loads(settings_in_base.value)

    count = 1
    while count <= request.form.get('statuses-count', 0, type=int):
        status_id = request.form.get('status-' + str(count))
        action = request.form.get('action-' + str(count))
        if not action:
            count += 1
            continue

        if action == 'delete':
            stock_status = db.session.execute(
                db.select(StockStatus)
                .filter_by(stock_status_id=int(status_id))).scalar()
            db.session.delete(stock_status)

        else:
            settings[status_id] = action

        count += 1

    if settings:
        if settings_in_base:
            settings_in_base.value = json.dumps(settings)
        else:
            new_status = Module(name='stock_statuses',
                                value=json.dumps(settings))
            db.session.add(new_status)
    db.session.commit()

    return redirect(url_for('stock_statuses'))


# @bp.route('/new_products', methods=['GET'])
# @login_required
# def new_products():
#     other_shops = tuple(db.session.execute(db.select(OtherShops)).scalars())
#
#     products = db.session.execute(
#         db.select(Product).filter_by(date_added=0)).scalars()
#
#     return render_template('products/new.html', products=products,
#                            other_shops=other_shops)


@bp.route('/new_products_comp', methods=['GET'])
@login_required
def new_products_comp():
    products = db.session.execute(
        db.select(Product).filter_by(date_added=0)).scalars()
    filter = {'products_ids': []}
    for product in products:
        filter['products_ids'].append(product.product_id)

    comparison_products.delay(filter)
    return redirect(url_for('new_products'))


@bp.route('/new_products', methods=['POST'])
@login_required
def new_products_post():
    products_count = request.form.get('products-count')

    count = 1

    while count <= int(products_count):
        name = request.form.get('name-' + str(count))
        if not name:
            count += 1
            continue

        new_product = Product(
            mpn=name,
            model='',
            sku='',
            upc='',
            location='',
            ean='',
            price=0,
            tax_class_id=0,
            manufacturer_id=0,
            isbn='',
            jan='',
            quantity=0,
            viewed=0,
            date_added=0,
            date_modified=0,
            cost=0,
            suppler_code=1,
            suppler_type=0,
            stock_status_id=0

        )
        db.session.add(new_product)

        count += 1
    db.session.commit()
    return 'OK'




