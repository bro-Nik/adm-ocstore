from flask import render_template, redirect, url_for, request, session, abort,\
    g
from flask_login import login_required
from bs4 import BeautifulSoup
import requests
import json
import time
import re
from datetime import datetime

from clim.app import app, db, redis, celery
from clim.models import OtherCategory, OtherProduct, OtherShops
from clim.routes import products


@app.route('/adm/other_shops', methods=['GET'])
@login_required
def other_shops():
    """ Страница магазинов """
    shops = db.session.execute(db.select(OtherShops)).scalars()
    return render_template('other_shops/other_shops.html', shops=shops)


@app.route('/adm/other_shops/add_shop', methods=['GET'])
@app.route('/adm/other_shops/<int:shop_id>/settings', methods=['GET'])
@login_required
def other_shop_settings(shop_id=None):
    """ Добавить или изменить магазин """
    if shop_id:
        shop = db.session.execute(
                db.select(OtherShops).filter_by(shop_id=shop_id)).scalar()
    else:
        shop = ''
    return render_template('other_shops/settings.html', shop=shop)


@app.route('/adm/other_shops/add_shop', methods=['POST'])
@app.route('/adm/other_shops/<int:shop_id>/update', methods=['POST'])
@login_required
def other_shop_add(shop_id=None):
    """ Отправка данных на добавление или изменение магазина """
    name = request.form.get('name')
    domain = request.form.get('domain')
    parsing = request.form.get('parsing')

    if shop_id:
        shop = db.session.execute(
                db.select(OtherShops).filter_by(shop_id=shop_id)).scalar()
        shop.name = name
        shop.domain = domain
        shop.parsing = parsing

    else:
        shop = OtherShops(name=name, domain=domain, parsing=parsing)
        db.session.add(shop)
    db.session.commit()
    return redirect(url_for('other_shops'))


@app.route('/adm/other_shops/delete', methods=['POST'])
@login_required
def other_shop_delete():
    """ Удаление магазинов """
    shops_count = request.form.get('shops-count')
    if not shops_count:
        return redirect(url_for('other_shops'))

    counter = 1
    while counter <= int(shops_count):
        shop_id = request.form.get('shop-' + str(counter))
        if not shop_id:
            counter += 1
            continue
        shop = db.session.execute(
            db.select(OtherShops).filter_by(shop_id=shop_id)).scalar()
        for category in shop.categories:
            for product in category.products:
                db.session.delete(product)
            db.session.delete(category)
        db.session.delete(shop)
        counter += 1
    db.session.commit()
    return redirect(url_for('other_shops'))


@app.route('/adm/other_shops/<int:shop_id>/categories', methods=['GET'])
@login_required
def other_shop_categories(shop_id):
    """ Категории магазина """
    shop = db.session.execute(db.select(OtherShops).filter_by(shop_id=shop_id)).scalar()

    new_price = {}
    new_product = {}

    for category in shop.categories:
        if category.new_price:
            new_price[category.other_category_id] = category.new_price.split(',')

        if category.new_product:
            new_product[category.other_category_id] = category.new_product.split(',')

    return render_template('other_shops/categories.html',
                           shop=shop,
                           new_price=new_price,
                           new_product=new_product)


@app.route('/adm/other_shops/<int:shop_id>/add_categories', methods=['POST'])
@app.route('/adm/other_shops/<int:shop_id>/<int:category_id>', methods=['POST'])
@login_required
def other_shop_add_category(shop_id, category_id=None):
    """ Отправка данных на добавление или изменение категории """
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

    name = request.form.get('name')
    url = request.form.get('url')
    parent_id = request.form.get('parent_id')
    parent_id = int(parent_id) if parent_id else 0
    sort = request.form.get('sort')
    sort = sort if sort else 0
    if category_id:
        category = db.session.execute(
                db.select(OtherCategory)
                .filter_by(other_category_id=category_id)).scalar()
        category.name = name
        category.url = url
        category.parent_id = parent_id
        category.sort = sort
        category.parsing = parsing
    else:
        category = OtherCategory(name=name, url=url, shop_id=shop_id,
                                 parent_id=parent_id, sort=sort,
                                 parsing=parsing)
        db.session.add(category)

    db.session.commit()

    return redirect(url_for('other_shop_category', shop_id=shop_id,
                            category_id=category.other_category_id))


@app.route('/adm/other_shops/<int:shop_id>/new_category', methods=['GET'])
@app.route('/adm/other_shops/<int:shop_id>/category/<int:category_id>', methods=['GET'])
@login_required
def other_shop_category(shop_id, category_id=None):
    """ Настройки категории магазина """
    shop = db.session.execute(
            db.select(OtherShops).filter_by(shop_id=shop_id)).scalar()
    if category_id:
        category = db.session.execute(
                db.select(OtherCategory).filter_by(other_category_id=category_id)).scalar()
        parsing = json.loads(category.parsing) if category.parsing else {}
    else:
        category = parsing = ''
    return render_template('other_shops/category_info.html', category=category,
                           parsing=parsing, shop=shop)


@app.route('/adm/other_shops/get_products_test/<int:category_id>',
           methods=['GET'])
@login_required
def get_other_products_test(category_id):
    result = get_other_products_task(category_id, True)
    return json.dumps(result)


@app.route('/adm/other_shops/<int:shop_id>/get_products/<int:category_id>',
           methods=['GET'])
@login_required
def get_other_products(shop_id, category_id):
    get_other_products_task.delay(category_id)
    return redirect(url_for('other_shop_categories', shop_id=shop_id))


@celery.task()
def get_other_products_task(category_id, test=None):
    category = db.session.execute(
            db.select(OtherCategory)
            .filter_by(other_category_id=category_id)).scalar()

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

            if product_in_base:
                if product_in_base.price != price:
                    product_in_base.price = price
                    db.session.commit()
                    if product_in_base.link_confirmed:
                        new_price_ids.append(str(product_in_base.other_product_id))
                continue

            new_product = OtherProduct(
                    shop_id=category.shop_id,
                    category_id=category_id,
                    name=name,
                    price=price,
                    link=link,
                    product_id=0
                    )
            db.session.add(new_product)
            db.session.commit()
            new_product_ids.append(str(new_product.other_product_id))
        if test:
            return result

        page = '?page=' + str(n_page)
        n_page += 1

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


@app.route('/adm/other_shops/<int:shop_id>', methods=['POST'])
@app.route('/adm/other_shops/<int:shop_id>/<string:action>', methods=['POST'])
@login_required
def other_shop_action(shop_id, action=None):
    """ Действия над категориями или товарами """
    categories_count = request.form.get('categories-count')
    if not categories_count:
        return redirect(url_for('other_shop_categories', shop_id=shop_id))

    def get_category(category_id):
        category = db.session.execute(
            db.select(OtherCategory)
            .filter_by(other_category_id=category_id)).scalar()
        return category

    counter = 1
    while counter <= int(categories_count):
        category_id = request.form.get('category-' + str(counter))
        if not category_id:
            counter += 1
            continue

        # Старт парсинга
        if action == 'start_parsing':
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
        counter += 1
    db.session.commit()
    return redirect(url_for('other_shop_categories', shop_id=shop_id))


@app.route('/adm/other_shops/<int:shop_id>/category/<int:category_id>/products/<string:changes>',
           methods=['GET', 'POST'])
@app.route('/adm/other_shops/<int:shop_id>/category/<int:category_id>/products',
           methods=['GET', 'POST'])
@app.route('/adm/other_shops/<int:shop_id>/category/products',
           methods=['GET', 'POST'])
@login_required
def other_shops_products(shop_id, category_id=None, changes=None):
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        changes = request.form.get('changes')

    new_price_ids = []
    new_product_ids = []

    idlist = []

    if category_id:
        category = db.session.execute(
            db.select(OtherCategory)
            .filter_by(other_category_id=category_id)).scalar()

        new_price_ids = category.new_price.split(',') if category.new_price else []
        new_product_ids = category.new_product.split(',') if category.new_product else []

        if changes == 'new_product':
            idlist = [int(x) for x in new_product_ids]
        elif changes == 'new_price':
            idlist = [int(x) for x in new_price_ids]

    page = request.args.get('page')
    page = int(page) if page else 1
    per_page = 20

    request_base = OtherProduct.query.filter_by(shop_id=shop_id, category_id=category_id)

    if idlist:
        request_base = request_base.where(OtherProduct.other_product_id.in_(idlist))
    products = request_base.paginate(page=page, per_page=per_page, error_out=False)

    categories = db.session.execute(db.select(OtherCategory)
                                    .filter_by(shop_id=shop_id)).scalars()

    return render_template('other_shops/products.html',
                           products=products,
                           category_id=category_id,
                           categories=tuple(categories),
                           new_product_ids=new_product_ids,
                           new_price_ids=new_price_ids,
                           changes=changes
                           )


def how_long_ago(event_date):
    ''' Возвращает сколько прошло от входящей даты '''
    if type(event_date) == str:
        event_date = datetime.strptime(event_date, '%Y-%m-%d')

    today = datetime.now().date()
    if today == datetime.date(event_date):
        result = 'сегодня'
    else:
        result = str((today - datetime.date(event_date)).days) + ' д. назад'

    return result

app.add_template_filter(how_long_ago)
