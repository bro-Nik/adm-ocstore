import json
from flask import render_template, request
from flask_login import login_required

from ..booking.utils import get_event_booking
from ..utils import actions_in, get_services, smart_int
from ..models import db
from .models import Worker
from .utils import get_worker
from . import bp


@bp.route('/workers_list', methods=['GET', 'POST'])
@login_required
def workers_list():
    if request.method == 'POST':
        # Действия
        actions_in(request.data, get_worker)
        db.session.commit()
        return ''

    workers = db.session.execute(db.select(Worker)).scalars()
    return render_template('worker/workers.html', workers=workers)


@bp.route('/worker_info', methods=['GET', 'POST'])
@login_required
def worker_info():
    worker = get_worker(request.args.get('worker_id')) or Worker()

    if request.method == 'POST':
        if not worker.worker_id:
            db.session.add(worker)

        worker.name = request.form.get('name', '')
        worker.start_day = request.form.get('start_day', '')
        worker.end_day = request.form.get('end_day', '')
        db.session.commit()
        return ''

    return render_template('worker/worker/main.html', worker=worker,
                           services=get_services())


@bp.route('/ajax_services', methods=['GET'])
@login_required
def ajax_services():
    services = get_services()
    search = request.args.get('search', '').lower()

    result = {'results': [], 'pagination': {'more': False}}
    for service in services:
        if search and search not in service.name.lower():
            continue

        result['results'].append({'id': service.time,
                                  'text': service.name,
                                  'subtext': f'{smart_int(service.time / 60)}ч'})

    return json.dumps(result)
