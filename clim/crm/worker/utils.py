from datetime import datetime

from ..utils import dt_to_str
from .models import Worker, db


def get_worker(worker_id):
    if worker_id:
        return db.session.execute(
            db.select(Worker).filter_by(worker_id=worker_id)).scalar()
