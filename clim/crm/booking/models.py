from ..models import db


class Employment(db.Model):
    __tablename__ = 'adm_worker_employment'

    employment_id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('adm_worker.worker_id'))
    title = db.Column(db.String(64))
    date_start = db.Column(db.Date)
    date_end = db.Column(db.Date)
    time_start = db.Column(db.Time)
    time_end = db.Column(db.Time)
    event = db.Column(db.String(64))
