from flask import flash
from ..models import db


class Worker(db.Model):
    __tablename__ = 'adm_worker'

    worker_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45))
    start_day = db.Column(db.Time)
    end_day = db.Column(db.Time)
    employments = db.relationship('Employment',
                                  backref=db.backref('worker', lazy=True))

    def delete(self):
        if self.employments:
            flash(f'У работника {self.name} есть запланированные задачи', 'warning')
            return
        db.session.delete(self)
