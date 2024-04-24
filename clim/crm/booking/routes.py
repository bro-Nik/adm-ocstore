import json
from datetime import datetime, timedelta

from flask import render_template, request
from flask_login import login_required

from ..utils import get_services
from ..models import db
from .models import Employment
from .utils import get_booking
from . import bp


@bp.route('/booking', methods=['GET'])
@login_required
def booking_page():
    event_name = request.args.get('event_name')

    start_date = request.args.get('start_date')
    if not start_date:
        start_date = datetime.now().date().strftime('%Y-%m-%d')

    return render_template('booking/booking.html', start_date=start_date,
                           services=get_services(), event_name=event_name)


@bp.route('/booking_post', methods=['POST'])
@login_required
def booking_post():
    from ..deal.utils import get_deal

    def str_date(string):
        return datetime.strptime(string, '%Y-%m-%d')

    data = json.loads(request.data) if request.data else []
    for worker in data:
        if not worker.get('schedule'):
            continue

        for schedule in worker.get('schedule'):
            if schedule.get('employmentId'):
                employment = get_booking(schedule.get('employmentId'))
            else:
                employment = Employment()
                db.session.add(employment)

            if schedule.get('delete'):
                db.session.delete(employment)
                continue

            # К чему относится событие
            event = schedule.get('booking_event', '')
            if 'deal' in event:
                event = get_deal(event.replace('deal_', ''))

            employment.title = f"{schedule.get('text', '')} ({event.name})"
            employment.worker_id = worker.get('worker_id')
            employment.event = schedule.get('booking_event')
            employment.time_start = schedule.get('start')
            employment.time_end = schedule.get('end')
            employment.date_start = str_date(schedule.get('startDate'))
            employment.date_end = str_date(schedule.get('endDate'))

    db.session.commit()
    return ''


@bp.route('/booking_data', methods=['GET'])
@login_required
def booking_data():
    from ..worker.routes import Worker

    def str_date(string):
        return datetime.strptime(string, '%Y-%m-%d').date()

    date = request.args.get('date')
    date_start = str_date(date) if date else datetime.now().date()
    date_end = date_start + timedelta(days=14)

    workers = db.session.execute(db.select(Worker)).scalars()
    rows = {}
    count = 0

    for worker in workers:
        schedule = []
        for employment in worker.employments:
            if ((employment.date_start < date_start and employment.date_end < date_start)
                    or (employment.date_start > date_end and employment.date_end > date_end)):
                continue

            schedule.append({
                'employment_id': employment.employment_id,
                'booking_event': employment.event,
                'start': str(employment.time_start),
                'end': str(employment.time_end),
                'date_start': employment.date_start,
                'date_end': employment.date_end,
                'text': str(employment.title),
                'data': {
                }
            })
        rows[count] = {
            'title': worker.name,
            'worker_id': worker.worker_id,
            'schedule': schedule
        }
        count += 1

    return rows
