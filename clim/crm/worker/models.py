from ..models import db
from .utils import WorkerUtils


class Worker(WorkerUtils, db.Model):
    __tablename__ = 'adm_worker'

    worker_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45))
    start_day = db.Column(db.Time)
    end_day = db.Column(db.Time)
    employments = db.relationship('Employment',
                                  backref=db.backref('worker', lazy=True))
