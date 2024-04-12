from datetime import datetime
import json

from flask import flash

from ..app import db
from ..models import OptionValue
from ..stock.utils import new_product_in_stock, get_product_in_stock


class Deal(db.Model):
    __tablename__ = 'adm_deal'

    deal_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    contact_id = db.Column(db.Integer, db.ForeignKey('adm_contact.contact_id'))
    stage_id = db.Column(db.Integer, db.ForeignKey('adm_deal_stage.stage_id'))
    details = db.Column(db.Text)
    products = db.Column(db.Text)
    consumables = db.Column(db.Text)
    expenses = db.Column(db.Text)
    posted = db.Column(db.Boolean)
    date_add = db.Column(db.Date)
    date_end = db.Column(db.Date)
    sum = db.Column(db.Float(15.4))
    analytics = db.Column(db.Text)
    profit = db.Column(db.Float(15.4))
    sort_order = db.Column(db.Integer)

    def posting(self, d=1):

        def change_quantity(products):
            nonlocal not_stock_id
            cost_price = 0
            for product in products:
                if product.get('type') == 'service':
                    service = OptionValue.get(product['product_id'])
                    product['product_name'] = service.description.name

                else:
                    if not product.get('stock_id'):
                        not_stock_id = True
                        break

                    quantity = product.get('quantity')
                    product_in_stock = get_product_in_stock(product['product_id'],
                                                            product['stock_id'])
                    if not product_in_stock:
                        product_in_stock = new_product_in_stock(product['product_id'],
                                                                product['stock_id'])
                        db.session.flush()
                    product_in_stock.quantity -= quantity * d

                    product['stock_name'] = product_in_stock.stock.name
                    product['product_name'] = product_in_stock.main_product.description.meta_h1
                    product['unit'] = product_in_stock.main_product.unit

                    # to analytics
                    cost_price += product_in_stock.main_product.cost * quantity * d

                    # delete product if quantity 0
                    if product_in_stock.quantity == 0:
                        db.session.delete(product_in_stock)

            return json.dumps(products), cost_price

        not_stock_id = False
        cost_price_products = 0
        if self.products:
            self.products, cost_price_products = change_quantity(json.loads(self.products))

        cost_price_consumables = 0
        if self.consumables:
            self.consumables, cost_price_consumables = change_quantity(json.loads(self.consumables))

        if not_stock_id:
            flash('Заполните склады списания', 'warning')
            return False

        # Date
        if not self.date_end:
            self.date_end = datetime.now().date()

        # Employments
        details = json.loads(self.details) if self.details else {}

        employments = WorkerEmployment.get(f'deal_{self.deal_id}')
        details['employments'] = []
        for employment in employments:
            details['employments'].append(employment.worker.name)
            db.session.delete(employment)
        self.details = json.dumps(details)

        # Analytics
        cost_price_expenses = 0
        if self.expenses:
            for expense in json.loads(self.expenses):
                cost_price_expenses += expense.get('sum')

        all_cost_price = (cost_price_products + cost_price_consumables
                          + cost_price_expenses)
        self.profit = self.sum - all_cost_price

        analytics = {
            'Товары': cost_price_products,
            'Расходные материалы': cost_price_consumables,
            'Прочие расходы': cost_price_expenses
        }

        analytics = json.dumps(analytics)
        self.analytics = analytics
        self.posted = True
        return True

    def unposting(self):
        if self.posting(-1) is True:
            self.posted = False
            return True
        return False

    def delete(self):
        db.session.delete(self)


class DealStage(db.Model):
    __tablename__ = 'adm_deal_stage'

    stage_id = db.Column(db.Integer, primary_key=True,)
    name = db.Column(db.String(128))
    type = db.Column(db.String(64))
    sort_order = db.Column(db.Integer)
    color = db.Column(db.String(45))
    deals = db.relationship('Deal', backref=db.backref('stage', lazy=True),
                            order_by='Deal.sort_order')

    @property
    def completed(self):
        return 'end_' in self.type


class Contact(db.Model):
    __tablename__ = 'adm_contact'

    contact_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    phone = db.Column(db.String(64))
    email = db.Column(db.String(64))
    role = db.Column(db.String(64))
    deals = db.relationship('Deal', backref=db.backref('contact', lazy=True))

    def delete(self):
        db.session.delete(self)


class Worker(db.Model):
    __tablename__ = 'adm_worker'

    worker_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45))
    start_day = db.Column(db.Time)
    end_day = db.Column(db.Time)
    employments = db.relationship('WorkerEmployment',
                                  backref=db.backref('worker', lazy=True))


class WorkerEmployment(db.Model):
    __tablename__ = 'adm_worker_employment'

    employment_id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('adm_worker.worker_id'))
    title = db.Column(db.String(64))
    date_start = db.Column(db.Date)
    date_end = db.Column(db.Date)
    time_start = db.Column(db.Time)
    time_end = db.Column(db.Time)
    event = db.Column(db.String(64))

    @staticmethod
    def get(event):
        return tuple(db.session.execute(
                     db.select(WorkerEmployment)
                     .filter(WorkerEmployment.event == event)).scalars())


class DealService(db.Model):
    __tablename__ = 'adm_deal_service'

    service_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45))
    time = db.Column(db.Integer)
