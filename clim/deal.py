import json
import os
from alembic.op import f
from flask import render_template, redirect, url_for, request, session, flash,\
    send_from_directory
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from clim.app import app, db, redis, celery, login_manager
from clim.models import Contact, Deal, DealStage, Option, OptionValue, Stock, StockProduct
from clim.routes import get_consumables, get_products, products


@app.route('/crm/deals', methods=['GET'])
@login_required
def deals():
    stages = db.session.execute(db.select(DealStage)).scalars()

    return render_template('deal/deals.html', stages=stages)


@app.route('/crm/deals/action', methods=['POST'])
@login_required
def deals_action():
    ids_list = request.form.get('deals-ids')
    ids_list = json.loads(ids_list) if ids_list else []

    for id in ids_list:
        deal = db.session.execute(db.select(Deal).filter(Deal.deal_id == id)).scalar()
        db.session.delete(deal)

    db.session.commit()

    return redirect(url_for('deals'))


@app.route('/crm/deal/new', methods=['GET'])
@app.route('/crm/deal/<int:deal_id>', methods=['GET'])
@login_required
def deal_info(deal_id=None):
    deal = db.session.execute(db.select(Deal).filter(Deal.deal_id == deal_id)).scalar()
    deal_products = []
    if deal and deal.products:
        deal_products = json.loads(deal.products)

    contacts = db.session.execute(db.select(Contact)).scalars()

    products = tuple(get_products(pagination=False))

    stocks = tuple(db.session.execute(db.select(Stock)).scalars())

    options = tuple(db.session.execute(db.select(Option)).scalars())

    consumables = get_consumables()

    stages = tuple(db.session.execute(db.select(DealStage)).scalars())

    analytics = {}
    if deal and deal.posted and deal.analytics:
        analytics = json.loads(deal.analytics)

    return render_template('deal/deal_info.html',
                           deal=deal,
                           deal_products=deal_products,
                           contacts=contacts,
                           products=products,
                           stocks=stocks,
                           options=options,
                           consumables=consumables,
                           stages=stages,
                           analytics=analytics)


@app.route('/crm/deal/new', methods=['POST'])
@app.route('/crm/deal/<int:deal_id>', methods=['POST'])
@login_required
def deal_info_update(deal_id=None):
    deal = db.session.execute(db.select(Deal).filter(Deal.deal_id == deal_id)).scalar()
    if not deal:
        deal = Deal(date_add=datetime.now().date())
        db.session.add(deal)


    # Name
    deal_name = request.form.get('deal_name')
    if not deal_name:
        deal_name = 'Сделка #' + str(Deal.query.count())
    deal.name = deal_name

    # Sum
    deal_sum = request.form.get('deal_sum')
    deal.sum = deal_sum if deal_sum else 0

    # Contact
    contact_id = request.form.get('contact_id')

    if contact_id:
        deal.contact_id = contact_id
    else:
        contact = Contact(
            name=request.form.get('contact_name'),
            phone=request.form.get('contact_phone'),
            email=request.form.get('contact_email')
        )
        db.session.add(contact)
        db.session.commit()
        deal.contact_id = contact.contact_id

    #
    deal.adress = request.form.get('adress')

    # Products
    count = 1
    products_count = request.form.get('products-count')
    products_count = int(products_count) if products_count else 0

    products = []

    while count <= products_count:
        product_id = request.form.get('product_id_' + str(count))
        if not product_id:
            count += 1
            continue

        product = {
            'product_id': int(product_id),
            'product_type': request.form.get('product_type_' + str(count)),
            'quantity': float(request.form.get('quantity_' + str(count))),
            'price': float(request.form.get('price_' + str(count)))
        }
        if product['product_type'] == 'product':
            product['stock_id'] = request.form.get('stock_id_' + str(count))

        products.append(product)
        count += 1

    if products:
        products = json.dumps(products)
        deal.products = products

    # Consumables
    count = 1
    products_count = request.form.get('consumables-count')
    products_count = int(products_count) if products_count else 0

    products = []

    while count <= products_count:
        product_id = request.form.get('consumable_id_' + str(count))
        if not product_id:
            count += 1
            continue

        product = {
            'product_id': int(product_id),
            'quantity': float(request.form.get('consumable_quantity_' + str(count))),
            'stock_id': request.form.get('consumable_stock_id_' + str(count))
        }

        products.append(product)
        count += 1

    if products:
        products = json.dumps(products)
        deal.consumables = products


    # Expenses
    count = 1
    expenses_count = request.form.get('expenses-count')
    expenses_count = int(expenses_count) if expenses_count else 0

    expenses = []

    while count <= expenses_count:
        name = request.form.get('expense_name_' + str(count))
        if not name:
            count += 1
            continue

        sum = request.form.get('expense_sum_' + str(count))
        sum = sum if sum else 0
        expense = {
            'name': name,
            'sum': float(sum)
        }

        expenses.append(expense)
        count += 1

    if expenses:
        expenses = json.dumps(expenses)
        deal.expenses = expenses

    # Stage
    posting = request.form.get('posting')
    if posting:
        deal.stage_id = request.form.get('old_stage')
    db.session.commit()
    deal.stage_id = request.form.get('stages')

    # Posting
    if not deal.posted and request.form.get('posting'):

        def change_quantity(products):
            nonlocal not_stock_id
            cost_price = 0
            for product in products:
                if product.get('product_type') == 'service':
                    service = db.session.execute(
                        db.select(OptionValue)
                        .filter(OptionValue.option_value_id == product['product_id'])).scalar()

                    product['product_name'] = service.description.name

                else:
                    if not product.get('stock_id'):
                        not_stock_id = True
                        break

                    quantity = product.get('quantity')
                    product_in_stock = db.session.execute(
                        db.select(StockProduct)
                        .filter(StockProduct.stock_id == product['stock_id'],
                                StockProduct.product_id == product['product_id'])).scalar()
                    product_in_stock.quantity -= quantity

                    product['stock_name'] = product_in_stock.stock.name
                    product['product_name'] = product_in_stock.product.mpn

                    # to analytics
                    cost_price += product_in_stock.purchase_price * quantity

            return json.dumps(products), cost_price

        not_stock_id = False
        cost_price_products = 0
        if deal.products:
            deal.products, cost_price_products = change_quantity(json.loads(deal.products))

        cost_price_consumables = 0
        if deal.consumables:
            deal.consumables, cost_price_consumables = change_quantity(json.loads(deal.consumables))

        if not_stock_id:
            flash('Заполните склады списания')
            return redirect(url_for('deal_info', deal_id=deal.deal_id))

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

    db.session.commit()

    return redirect(url_for('deal_info', deal_id=deal.deal_id))


@app.route('/json/deal/products/<int:deal_id>', methods=['GET'])
@login_required
def json_deal_products(deal_id=None):
    deal = db.session.execute(db.select(Deal).filter(Deal.deal_id == deal_id)).scalar()
    products = []
    if deal and deal.products:
        products = deal.products

    return products


@app.route('/json/deal/consumables/<int:deal_id>', methods=['GET'])
@login_required
def json_deal_consumables(deal_id=None):
    deal = db.session.execute(db.select(Deal).filter(Deal.deal_id == deal_id)).scalar()
    products = []
    if deal and deal.consumables:
        products = deal.consumables

    return products


@app.route('/json/deal/expenses/<int:deal_id>', methods=['GET'])
@login_required
def json_deal_expenses(deal_id=None):
    deal = db.session.execute(db.select(Deal).filter(Deal.deal_id == deal_id)).scalar()
    expenses = []
    if deal and deal.expenses:
        expenses = deal.expenses

    return expenses


