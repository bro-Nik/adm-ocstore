from flask import render_template, redirect, url_for, request, session, abort,\
    g, Blueprint
from flask_login import login_required
from bs4 import BeautifulSoup
import requests
import json
import time
import re
from datetime import datetime

from clim.app import celery
from clim.models import db, OtherCategory, OtherProduct, OtherShops
from . import bp


def get_shop(id):
    return db.session.execute(
            db.select(OtherShops).filter_by(shop_id=id)).scalar()

def get_categories(shop_id):
    return db.session.execute(
        db.select(OtherCategory).filter_by(shop_id=shop_id)).scalars()

def get_category(id):
    return db.session.execute(
        db.select(OtherCategory).filter_by(other_category_id=id)).scalar()

def int_or_other(number, default):
    return int(number) if number else default


@bp.route('/shops', methods=['GET'])
@login_required
def shops():
    """ Страница магазинов """
    shops = db.session.execute(db.select(OtherShops)).scalars()
    return render_template('other_shops/shops.html', shops=shops)


@bp.route('/shops_action', methods=['POST'])
@login_required
def shops_action():
    """ Действия над магазинами """
    data = json.loads(request.data) if request.data else {}

    action = data.get('action')
    ids = data.get('ids')

    for id in ids:
        shop = get_shop(id)
        for category in shop.categories:
            for product in category.products:
                db.session.delete(product)
            db.session.delete(category)
        db.session.delete(shop)
    db.session.commit()

    return ''


@bp.route('/shop_settings', methods=['GET', 'POST'])
@login_required
def shop_settings():
    """ Добавить или изменить магазин """
    shop_id = request.args.get('shop_id')

    if request.method == 'GET':
        return render_template('other_shops/shop_settings.html',
                               shop=get_shop(shop_id))
    else:
        shop = get_shop(shop_id)
        if not shop:
            shop = OtherShops()
            db.session.add(shop)

        shop.name = request.form.get('name')
        shop.domain = request.form.get('domain')
        shop.parsing = request.form.get('parsing')
    
        db.session.commit()
        return ''


@bp.route('/<int:shop_id>/categories', methods=['GET'])
@login_required
def shop_categories(shop_id):
    """ Категории магазина """
    new_price = {}
    new_product = {}

    shop = get_shop(shop_id)
    for category in shop.categories:
        if category.new_price:
            new_price[category.other_category_id] = category.new_price.split(',')

        if category.new_product:
            new_product[category.other_category_id] = category.new_product.split(',')

    return render_template('other_shops/shop_categories.html',
                           shop=shop,
                           new_price=new_price,
                           new_product=new_product)


@bp.route('/other_shops/<int:shop_id>', methods=['POST'])
@login_required
def shop_action(shop_id):
    """ Действия над категориями или товарами """
    data = json.loads(request.data) if request.data else {}

    action = data.get('action')
    ids = data.get('ids')

    for category_id in ids:

        # Старт парсинга
        if action == 'parsing':
            get_other_products_task.delay(category_id)

        # Удаление
        elif (action == 'del_categories_and_products'
                or action == 'del_only_products'):

            category = get_category(category_id)
            for product in category.products:
                db.session.delete(product)
            if action == 'del_categories_and_products':
                db.session.delete(category)
            else:
                category.new_price = None
                category.new_product = None

        # Принять изменения
        elif action == 'accept_changes':
            category = get_category(category_id)
            category.new_price = None
            category.new_product = None
    db.session.commit()

    return ''


@bp.route('/<int:shop_id>/category_update', methods=['POST'])
@login_required
def category_update(shop_id):
    """ Отправка настроек категории """
    category_id = request.args.get('category_id')

    # Parsing parameters
    minus = request.form.get('minus')
    if minus:
        minus = re.sub(r'( ,|, )', ',', minus)

    parsing = None
    parsing_parameters = {
        'blocks_type': request.form.get('blocks_type'),
        'blocks_class': request.form.get('blocks_class'),
        'block_name_type': request.form.get('block_name_type'),
        'block_name_class': request.form.get('block_name_class'),
        'block_name_inside': request.form.get('block_name_inside'),
        'block_link_type': request.form.get('block_link_type'),
        'block_link_class': request.form.get('block_link_class'),
        'block_price_type': request.form.get('block_price_type'),
        'block_price_class': request.form.get('block_price_class'),
        'block_other_price_type': request.form.get('block_other_price_type'),
        'block_other_price_class': request.form.get('block_other_price_class'),
        'minus': minus
        }
    for parameter in parsing_parameters:
        if parsing_parameters[parameter]:
            parsing = json.dumps(parsing_parameters)
            break

    if category_id:
        category = get_category(category_id)
    else:
        category = OtherCategory(shop_id=shop_id)
        db.session.add(category)

    category.name = request.form.get('name')
    category.url = request.form.get('url')
    category.parent_id = int_or_other(request.form.get('parent_id'), 0)
    category.sort = int_or_other(request.form.get('sort'), 0)
    category.parsing = parsing

    db.session.commit()

    return ''


@bp.route('/<int:shop_id>/category_settings', methods=['GET'])
@login_required
def category_settings(shop_id):
    """ Настройки категории магазина """
    category_id = request.args.get('category_id')

    return render_template('other_shops/category_settings.html',
                           category=get_category(category_id),
                           shop=get_shop(shop_id))


@bp.route('/<int:shop_id>/category/products', methods=['GET'])
@login_required
def category_products(shop_id):
    category_id = request.args.get('category_id')
    changes = request.args.get('changes')

    new_price_ids = []
    new_product_ids = []

    idlist = []

    if category_id:
        category = get_category(category_id)

        new_price_ids = category.new_price.split(',') if category.new_price else []
        new_product_ids = category.new_product.split(',') if category.new_product else []

        if changes == 'new_product':
            idlist = [int(x) for x in new_product_ids]
        elif changes == 'new_price':
            idlist = [int(x) for x in new_price_ids]

    page = int_or_other(request.args.get('page'), 1)
    per_page = 20

    request_base = OtherProduct.query.filter_by(shop_id=shop_id)
    if category_id:
        request_base = request_base.filter_by(category_id=category_id)

    if idlist:
        request_base = request_base.where(OtherProduct.other_product_id.in_(idlist))
    products = request_base.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('other_shops/category_products.html',
                           products=products,
                           category_id=category_id,
                           categories=tuple(get_categories(shop_id)),
                           new_product_ids=new_product_ids,
                           new_price_ids=new_price_ids,
                           changes=changes
                           )


@bp.route('/get_products_test/<int:category_id>', methods=['GET'])
@login_required
def get_products_test(category_id):
    result = get_other_products_task(category_id, True)
    return json.dumps(result)


@bp.route('/<int:shop_id>/get_products/<int:category_id>', methods=['GET'])
@login_required
def get_products(shop_id, category_id):
    get_other_products_task.delay(category_id)
    return redirect(url_for('other_shop_categories', shop_id=shop_id))


@celery.task()
def get_other_products_task(category_id, test=None):
    category = get_category(category_id)

    parsing = json.loads(category.parsing)

    if category.shop.parsing == 'domain':
        prefix = category.shop.domain
    else:
        prefix = category.url

    n_page = 2
    page = ''
    result = []
    products_count = len(category.products)
    new_price_ids = category.new_price.split(',') if category.new_price else []
    new_product_ids = category.new_product.split(',') if category.new_product else []

    links_list = []

    while True:
        response = requests.get(category.url + page)
        print(page)
        bs = BeautifulSoup(response.text, "lxml")
        blocks = bs.find(parsing['blocks_type'], parsing['blocks_class'])
        if not blocks or blocks == -1:
            break

        for block in blocks:
            if not block or block == -1:
                continue

            block_name = block.find(parsing['block_name_type'],
                                    parsing['block_name_class'])
            if parsing.get('block_name_inside'):
                block_name = block_name.find(parsing['block_name_inside'])

            if not block_name or block_name == -1:
                continue
            name = block_name.get_text()
            if not name:
                continue
            name = re.sub(parsing['minus'], '', name, flags=re.IGNORECASE)
            name = name.strip()

            block_link = block.find(parsing['block_link_type'],
                                    parsing['block_link_class'])
            link = block_link.a.get('href')
            if link:
                if prefix[-1] == '/' and link[0] == '/':
                    prefix = prefix[:-1]
                elif prefix[-1] != '/' and link[0] != '/':
                    prefix += '/'
                link = (prefix + link).lower()
            else:
                continue

            if link in links_list:
                continue

            links_list.append(link)

            block_price = block.find(parsing['block_price_type'],
                                     parsing['block_price_class'])
            if not block_price:
                block_price = block.find(parsing['block_other_price_type'],
                                         parsing['block_other_price_class'])
            price = block_price.get_text(strip=True)
            if price:
                price = re.sub(r'(руб.|руб| |р)', '', price, flags=re.IGNORECASE)    

            if test:
                result.append({'name': name, 'link': link, 'price': price})
                continue

            product_in_base = db.session.execute(
                    db.select(OtherProduct).filter_by(link=link)).scalar()

            if not product_in_base:
                product_in_base = OtherProduct(
                        shop_id=category.shop_id,
                        category_id=category_id,
                        name=name,
                        link=link,
                        product_id=0
                        )
                db.session.add(product_in_base)
                db.session.commit()
                new_product_ids.append(str(product_in_base.other_product_id))

            product_in_base.price = price
            db.session.commit()

            if product_in_base.link_confirmed:
                new_price_ids.append(str(product_in_base.other_product_id))
                continue

        if test:
            return result

        page = '?page=' + str(n_page)
        n_page += 1
        time.sleep(1)

    changes = {}
    if len(category.products) != products_count:
        new_products_count = len(category.products) - products_count
        changes['products'] = new_products_count
    category.changes_confirmed = json.dumps(changes)

    if new_price_ids:
        new_price_ids = (',').join(new_price_ids)
        category.new_price = new_price_ids

    if new_product_ids:
        new_product_ids = (',').join(new_product_ids)
        category.new_product = new_product_ids

    category.last_parsing = str(datetime.now().date())
    db.session.commit()
    print('End')




