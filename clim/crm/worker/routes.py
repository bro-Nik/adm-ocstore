import json
from flask import render_template, request
from flask_login import login_required

from clim.utils import actions_in

from ..utils import smart_int
from ..models import Service, db
from .models import Worker
from . import bp


@bp.route('/', methods=['GET', 'POST'])
@login_required
def workers():
    page = request.args.get('page', 1, type=int)

    if request.method == 'POST':
        return actions_in(Worker.get)

    workers = db.paginate(db.select(Worker),
                          per_page=10, error_out=False, page=page)
    return render_template('worker/workers.html', workers=workers,
                           child_obj=Worker(worker_id=0))


@bp.route('/worker_settings', methods=['GET', 'POST'])
@login_required
def worker_settings():
    worker = Worker.get(request.args.get('worker_id')) or Worker()

    if request.method == 'POST':
        return actions_in(worker)

    return render_template('worker/worker/main.html', worker=worker)


@bp.route('/ajax_services', methods=['GET'])
@login_required
def ajax_services():
    services = db.select(Service)

    search = request.args.get('search', '').lower()
    # Разделяем на пробелы и ищем совпадения
    for word in search.split(' '):
        if word:
            services = (services.filter(Service.name.contains(word)))

    per_page = 20
    page = request.args.get('page', 1, type=int)
    services = db.paginate(services,
                           page=page, per_page=per_page, error_out=False)

    result = []
    for service in services:
        result.append({'id': service.time,
                       'text': service.name,
                       'subtext': f'{smart_int(service.time / 60)}ч'})

    return json.dumps({'results': result, 'pagination': {'more': bool(result)}})
