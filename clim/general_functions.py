import json
import pickle
from flask import render_template, redirect, url_for, request, session
from flask_login import login_required, current_user

from clim.app import app, db, redis, celery, login_manager
from clim.models import Attribute, AttributeDescription, Category, Manufacturer, Product


def get_product(product_id: int):
    return db.session.execute(
        db.select(Product).filter_by(product_id=product_id)).scalar()


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
