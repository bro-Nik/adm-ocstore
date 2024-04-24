from datetime import datetime
from clim.crm.utils import dt_to_str
from .models import db, Deal, DealStage


def get_stage(stage_id: int = 0, stage_type: str = ''):
    if stage_id:
        select = db.select(DealStage).filter_by(stage_id=stage_id)
    elif stage_type:
        select = db.select(DealStage).filter_by(type=stage_type)
    else:
        return
    return db.session.execute(select).scalar()


def get_stages(status=''):
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


def get_deal(deal_id):
    return db.session.execute(
        db.select(Deal).filter(Deal.deal_id == deal_id)).scalar()


def sort_stage_deals(stage_id, deal_id, previous_deal_sort):
    def number(number):
        try:
            return int(number)
        except:
            return 0

    previous_deal_sort = number(previous_deal_sort)

    stage = get_stage(stage_id)

    for deal_in_stage in stage.deals:
        deal_in_stage.sort_order = number(deal_in_stage.sort_order)

        if (deal_in_stage.sort_order > previous_deal_sort
            and deal_in_stage.deal_id != deal_id):
            deal_in_stage.sort_order += 1
    db.session.commit()

    count = 1
    for deal_in_stage in stage.deals:
        deal_in_stage.sort_order = count
        count += 1
    db.session.commit()


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
