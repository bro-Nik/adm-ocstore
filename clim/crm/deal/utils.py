from datetime import datetime
import json

from flask import abort, flash
from clim.crm.booking.utils import get_event_booking
from clim.crm.stock.models import StockProduct
from clim.crm.utils import dt_to_str
from clim.mixins import JsonDetailsMixin, PageMixin
from .models import db


class DealUtils(PageMixin, JsonDetailsMixin):
    URL_PREFIX = 'crm.deal.deal_'

    @property
    def actions(self):
        return {
            'save': [True],
            'posting': [True],
            'unposting': [True],
            'delete': [self.deal_id, 'Удадить', 'Удалить сделку?', '']
        }

    def pages_settings(self):
        return {'info': [True, 'Инфо']}

    def save(self):
        from ..models import Product
        from .models import DealStage, Deal
        details = self.get_json('details') or {}
        analytics = {}
        data = self.save_data
        info = data.get('info', {})

        # Name
        details['name'] = info.get('name') or f'Сделка #{Deal.query.count()}'
        # Contact
        self.contact_id = info.get('contact_id')
        # Date
        details['date_add'] = details.get('date_add', datetime.strftime(datetime.now(), "%d.%m.%Y %H:%M"))
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
                    product_in_base = Product.get(product['id'])
                    analytics['cost_products'] += quantity * product_in_base.cost
                    product['unit'] = product_in_base.unit

            # Расходные материалы
            consumables = data.get('consumables', [])
            self.consumables = json.dumps(consumables, ensure_ascii=False)
            analytics['cost_consumables'] = 0  # Затраты
            for product in consumables:
                quantity = float(product['quantity'] or 0)
                product_in_base = Product.get(product['id'])
                analytics['cost_consumables'] += quantity * product_in_base.cost
                product['unit'] = product_in_base.unit

            # Прочие расходы
            expenses = data.get('expenses', [])
            self.expenses = json.dumps(expenses, ensure_ascii=False)
            analytics['cost_expenses'] = 0  # Затраты
            for expense in expenses:
                analytics['cost_expenses'] += float(expense['price'] or 0)

            # Аналитика
            self.analytics = json.dumps(analytics, ensure_ascii=False)

            details['profit'] = (details['sum'] - (analytics['cost_products'] +
                                 analytics['cost_consumables'] + analytics['cost_expenses']))

        self.details = json.dumps(details, ensure_ascii=False)

        # ToDo Проверка смены статуса после постинга
        new_stage = DealStage.get(info['stage_id']) or abort(404)
        action = None
        if self.posted and self.stage.type != new_stage.type:
            action = 'unposting'
        elif not self.posted and new_stage.type == 'end_good':
            action = 'posting'

        # Stage
        if self.stage.stage_id != new_stage.stage_id:
            self.sort_order = 1
            sort_stage_deals(new_stage.stage_id, self.deal_id, 0)

        # Если не будет постинга применяем стадию
        if not action:
            self.stage = new_stage
            db.session.flush()
            return

        # Сохранение перед постингом
        db.session.commit()

        # Posting or Unposting
        self.stage = new_stage
        return self.try_action(action)

    def posting(self, d=1):

        def change_quantity(products):
            nonlocal errors
            for p in products:
                # Пропускаем услуги
                if p.get('type') == 'service':
                    continue

                # Пропускаем товары без склада списания
                if not p.get('stock_id'):
                    errors.append(f'Не указан склад для {p["name"]}')
                    continue

                # Пропускаем товары с неверным количеством
                quantity = float(p.get('quantity') or 0)
                if quantity <= 0:
                    errors.append(f'Неверное количество - {p["name"]}')
                    continue

                # Обновляем количество товара на складе
                stock = StockProduct.get(p['id'], p['stock_id'], create=True)
                stock.quantity -= float(quantity) * d

                if stock.quantity < 0:
                    errors.append(f'Нет достаточного количества на складе '
                                  f'{p["stock_name"]} - {p["name"]}')
                    continue

                # Удалить, если нет остатков
                if stock.quantity == 0:
                    db.session.delete(stock)

        errors = []
        if self.products:
            change_quantity(json.loads(self.products))
        if self.consumables:
            change_quantity(json.loads(self.consumables))

        # Если есть ошибки - печатаем и выходим
        if errors:
            for error in errors:
                flash(error, 'warning')
            return False

        details = self.get_json('details') or {}
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

        # Удаляем краткую запись выездов
        if details.get('new_employments'):
            del details['new_employments']

        self.details = json.dumps(details)
        self.posted = d == 1  # True or False

    def unposting(self):
        return self.posting(-1)


def get_stages(status=''):
    from .models import DealStage
    if 'in_work' in status and 'end' in status:
        select = db.select(DealStage)
    elif 'in_work' in status:
        select = db.select(DealStage).filter(DealStage.type != 'end_good',
                                             DealStage.type != 'end_bad')
    elif 'end' in status:
        select = db.select(DealStage).filter((DealStage.type == 'end_good') |
                                             (DealStage.type == 'end_bad'))
    elif 'start' in status:
        select = db.select(DealStage).filter_by(type='start')
    else:
        select = db.select(DealStage)
    return db.session.execute(select.order_by(DealStage.sort_order)).scalars()


def sort_stage_deals(stage_id, deal_id, previous_deal_sort):
    from .models import DealStage
    previous_deal_sort = int(previous_deal_sort or 0)

    stage = DealStage.get(stage_id)

    for deal_in_stage in stage.deals:
        # deal_in_stage.sort_order = number(deal_in_stage.sort_order)
        deal_in_stage.sort_order = deal_in_stage.sort_order

        if (deal_in_stage.sort_order > previous_deal_sort
            and deal_in_stage.deal_id != deal_id):
            deal_in_stage.sort_order += 1
    db.session.commit()

    count = 1
    for deal_in_stage in stage.deals:
        deal_in_stage.sort_order = count
        count += 1
    db.session.commit()


def sort_stages(stage_id, sort_order):
    count = 0
    prew_stage = this_stage = None
    for stage in get_stages():
        if stage.sort_order == sort_order - 1:
            prew_stage = stage
        elif stage.stage_id == stage_id:
            this_stage = stage
        elif stage.sort_order == sort_order:
            count += 1

        stage.sort_order = count
        count += 1
    if this_stage and prew_stage:
        this_stage.sort_order = prew_stage.sort_order + 1
    elif this_stage:
        this_stage.sort_order = 0


def employment_info(employments):
    result = {}
    for e in employments:
        start = dt_to_str(datetime.combine(e.date_start, e.time_start))
        end = dt_to_str(datetime.combine(e.date_end, e.time_end))
        # Если дата одинаковая - оставляем одну
        end = end.replace(start[:11], '')
        date = f'{start}-{end}'

        # Список исполнителей в дату
        if not result.get(date):
            result[date] = []

        # Добавление исполнителя
        if e.worker.name not in result[date]:
            result[date].append(e.worker.name)
    return result


class StageUtils(PageMixin, JsonDetailsMixin):
    URL_PREFIX = 'crm.deal.stage_'

    @property
    def actions(self):
        return {
            'save': [True],
            'delete': [self.stage_id, 'Удадить', 'Удалить стадию?', '']
        }
    def pages_settings(self):
        return {'settings': [True, 'Настройки']}

    def save(self):
        data = self.save_data
        self.name = data.get('name')
        self.type = data.get('type')
        self.color = data.get('color')

    def delete(self):
        if self.deals:
            flash(f'У стадии есть сделки', 'warning')
            return False

        super().delete()
