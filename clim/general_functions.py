import json
import pickle
from flask import render_template, redirect, url_for, request, session
from flask_login import login_required, current_user

from clim.app import app, db, redis, celery, login_manager
from clim.models import Attribute, AttributeDescription, Category, Manufacturer, Module, OtherProduct, Product, ProductAttribute, ProductToCategory


def json_dumps_or_other(data, default=None):
    return json.dumps(data, ensure_ascii=False) if data else default


def json_loads_or_other(data, default=None):
    return json.loads(data) if data else default


def dict_from_serialize_array(list):
    info = {}
    for item in list:
        name = item['name']
        value = item['value']
        if info.get(name):
            if type(info.get(name)) != list:
                info[name] = [info[name]]

            info[name].append(value)
        else:
            info[name] = value
    return info


def dict_get_or_other(dict, key, default=None):
    return dict.get(key) if dict and dict.get(key) else default


def get_module(name):
    return db.session.execute(
        db.select(Module).filter_by(name=name)).scalar()

def get_category(id):
    return db.session.execute(
        db.select(Category).filter_by(category_id=id)).scalar()


def get_categories():
    return db.session.execute(
        db.select(Category).order_by(Category.sort_order)).scalars()


def get_product(id: int):
    return db.session.execute(
        db.select(Product).filter_by(product_id=id)).scalar()


def get_main_category(product_id):
    return db.session.execute(
        db.select(ProductToCategory)
        .filter_by(product_id=product_id, main_category=1)).scalar()


def get_discount_products():
    # Получем метки
    label = db.session.execute(
        db.select(AttributeDescription).filter_by(name='Метка')).scalar()
    attributes = db.session.execute(
            db.select(ProductAttribute)
            .filter_by(attribute_id=label.attribute_id)).scalars()

    # Отделяем акционные товары
    discount_product_ids = []
    for attribute in attributes:
        if 'Спецпредложение' in attribute.text:
            discount_product_ids.append(attribute.product_id)
    return discount_product_ids


def get_other_product(id: int):
    return db.session.execute(
        db.select(OtherProduct).filter_by(other_product_id=id)).scalar()


@app.route('/ajax/list_all_categories', methods=['GET'])
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


@app.route('/ajax/list_all_manufacturers', methods=['GET'])
@login_required
def get_list_all_manufacturers():
    per_page = 20
    search = request.args.get('search')
    result = {'results': []}

    request_base = Manufacturer.query

    if search:
        request_base = (request_base
                        .where(Manufacturer.name.contains(search)))

    manufacturers = request_base.paginate(page=int(request.args.get('page')),
                                           per_page=per_page,
                                           error_out=False)

    for manufacturer in manufacturers:
        result['results'].append(
            {
                'id': str(manufacturer.manufacturer_id),
                'text': manufacturer.name
            }
        )

    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}

    return json.dumps(result)


@app.route('/ajax/list_all_attributes', methods=['GET'])
@login_required
def get_list_all_attributes():
    per_page = 20
    search = request.args.get('search')
    result = {'results': []}

    request_base = Attribute.query.where(Attribute.description)

    if search:
        request_base = (request_base.join(Attribute.description)
                   .where(AttributeDescription.name.contains(search)))

    attributes = request_base.paginate(page=int(request.args.get('page')),
                                       per_page=per_page,
                                       error_out=False)

    for attribute in attributes:
        result['results'].append(
            {
                'id': str(attribute.attribute_id),
                'text': attribute.description.name
            }
        )

    more = len(result['results']) >= per_page
    result['pagination'] = {'more': more}

    return json.dumps(result)
