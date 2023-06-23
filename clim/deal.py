import json
import os
from alembic.op import f
from flask import render_template, redirect, url_for, request, session, flash,\
    send_from_directory
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from clim.app import app, db, redis, celery, login_manager
from clim.models import Contact, Deal, DealStage, Option, OptionValue, Stock, StockProduct
from clim.options import get_option_value
from clim.routes import get_consumables, get_products, products
from clim.stock import get_product_in_stock


@app.route('/crm/deals', methods=['GET'])
@login_required
def deals():
    stages = db.session.execute(db.select(DealStage)).scalars()

    return render_template('deal/deals.html', stages=stages)


def get_deal(deal_id):
    return db.session.execute(db.select(Deal).filter(Deal.deal_id == deal_id)).scalar()


@app.route('/crm/deals/action', methods=['POST'])
@login_required
def deals_action():
    ids_list = request.form.get('deals-ids')
    ids_list = json.loads(ids_list) if ids_list else []

    for id in ids_list:
        deal = get_deal(id)
        db.session.delete(deal)

    db.session.commit()

    return redirect(url_for('deals'))




@app.route('/crm/deal/new', methods=['GET'])
@app.route('/crm/deal/<int:deal_id>', methods=['GET'])
@login_required
def deal_info(deal_id=None):
    deal = get_deal(deal_id)
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
    deal = get_deal(deal_id)
    if not deal:
        deal = Deal(date_add=datetime.now().date())
        db.session.add(deal)

    # Name
    deal_name = request.form.get('deal_name')
    if not deal_name:
        deal_name = 'Сделка #' + str(Deal.query.count())
    deal.name = deal_name

    # Date
    date_end = request.form.get('date_end')
    if date_end:
        deal.date_end = date_end

    # Sum
    deal_sum = request.form.get('deal_sum')
    deal.sum = deal_sum if deal_sum else 0

    # Contact
    contact_id = request.form.get('contact_id')

    if contact_id:
        deal.contact_id = contact_id
    else:
        contact_name = request.form.get('contact_name')
        contact_phone = request.form.get('contact_phone')
        contact_email = request.form.get('contact_email')

        if contact_name or contact_phone or contact_email:
            contact = Contact(
                name=contact_name if contact_name else '',
                phone=contact_phone if contact_phone else '',
                email=contact_email if contact_email else ''
            )
            db.session.add(contact)
            db.session.commit()
            deal.contact_id = contact.contact_id

    #
    deal.adress = request.form.get('adress')

    # Products
    products = request.form.get('products_data')
    if products:
        products = json.loads(products.replace(',]', ']'))
        deal.products = products

    # Consumables
    consumables = request.form.get('consumables_data')
    if consumables:
        consumables = json.loads(consumables.replace(',]', ']'))
        deal.consumables = consumables

    # Expenses
    expenses = request.form.get('expenses_data')
    if expenses:
        expenses = json.loads(expenses.replace(',]', ']'))
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
            flash('Заполните склады списания')
            return redirect(url_for('deal_info', deal_id=deal.deal_id))

        # Date
        if not deal.date_end:
            deal.date_end = datetime.now().date()

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

