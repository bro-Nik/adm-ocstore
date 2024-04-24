from datetime import datetime
import json

from flask import flash

from ..booking.utils import get_event_booking
from ..utils import JsonMixin, dt_to_str
from ..models import db
from ..stock.utils import get_product, new_product_in_stock, get_product_in_stock


class Deal(db.Model, JsonMixin):
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

    # @property
    # def name(self):
    #     return self.info.get('name', '')

    def save(self):
        details = self.get('details', {})
        analytics = {}
        data = self.data
        info = data.get('info', {})

        # Name
        details['name'] = info.get('name') or f'Сделка #{Deal.query.count()}'
        # Contact
        self.contact_id = info.get('contact_id')
        # Date
        details['date_add'] = datetime.strftime(datetime.now(), "%d.%m.%Y %H:%M")
        details['date_end'] = info.get('date_end')

        details['adress'] = info.get('adress')
        details['what_need'] = info.get('what_need')
        details['date_service'] = info.get('date_service')
        details['comment'] = info.get('comment')

        if not self.posted:
            # Товары
            products = data.get('products', [])
            self.products = json.dumps(products, ensure_ascii=False)
            details['sum'] = 0 if products else data.get('sum', 0)  # Сумма сделки
            analytics['cost_products'] = 0  # Затраты
            for product in products:
                quantity = float(product['quantity'] or 0)
                details['sum'] += quantity * float(product['price'] or 0)
                if product['type'] != 'service':
                    product_in_base = get_product(product['id'])
                    analytics['cost_products'] += quantity * product_in_base.cost
                    product['unit'] = product_in_base.unit

            # Расходные материалы
            consumables = data.get('consumables', [])
            self.consumables = json.dumps(consumables, ensure_ascii=False)
            analytics['cost_consumables'] = 0  # Затраты
            for product in consumables:
                quantity = float(product['quantity'] or 0)
                product_in_base = get_product(product['id'])
                analytics['cost_consumables'] += quantity * product_in_base.cost
                product['unit'] = product_in_base.unit

            # Прочие расходы
            expenses = data.get('expenses', [])
            self.expenses = json.dumps(expenses, ensure_ascii=False)
            analytics['cost_expenses'] = 0  # Затраты
            for expense in expenses:
                analytics['cost_expenses'] += float(expense.get('price', 0))

            details['profit'] = (details['sum'] - (analytics['cost_products'] +
                                 analytics['cost_consumables'] + analytics['cost_expenses']))

        self.details = json.dumps(details, ensure_ascii=False)
        self.analytics = json.dumps(analytics, ensure_ascii=False)

    def posting(self, d=1):

        def change_quantity(products):
            nonlocal errors
            for product in products:
                if product.get('type') == 'service':
                    continue

                if not product.get('stock_id'):
                    errors.append(f'Не указан склад для {product["name"]}')
                    continue

                product_in_stock = get_product_in_stock(product['id'],
                                                        product['stock_id'])
                if not product_in_stock:
                    product_in_stock = new_product_in_stock(product['id'],
                                                            product['stock_id'])
                    db.session.flush()

                product_in_stock.quantity -= float(product.get('quantity')) * d

                if product_in_stock.quantity < 0:
                    errors.append(f'Нет достаточного количества на складе '
                                  f'{product["stock_name"]} - {product["name"]}')
                    continue

                # delete product if quantity 0
                if product_in_stock.quantity == 0:
                    db.session.delete(product_in_stock)

        errors = []
        if self.products:
            change_quantity(json.loads(self.products))
        if self.consumables:
            change_quantity(json.loads(self.consumables))

        # Если есть ошибки - печатаем и выходим
        if errors:
            for error in errors:
                flash(error, 'warning')
            return

        details = self.get('details', {})
        # Date
        details['date_end'] = details['date_end'] or dt_to_str(datetime.now())

        # Employments
        employments = get_event_booking(f'deal_{self.deal_id}')

        # Парсинг и объединение со старыми записями
        from .utils import employment_info
        details.setdefault('employments', {})
        details['employments'] |= employment_info(employments)

        for e in employments:
            db.session.delete(e)

        self.details = json.dumps(details)
        self.posted = d == 1  # True or False

    def unposting(self):
        self.posting(-1)

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
