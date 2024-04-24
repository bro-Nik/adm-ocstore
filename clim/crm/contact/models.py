from flask import flash
from ..models import db


class Contact(db.Model):
    __tablename__ = 'adm_contact'

    contact_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    phone = db.Column(db.String(64))
    email = db.Column(db.String(64))
    role = db.Column(db.String(64))
    deals = db.relationship('Deal', backref=db.backref('contact', lazy=True))
    movements = db.relationship('StockMovement',
                                backref=db.backref('contact', lazy=True))

    def delete(self):
        if self.deals:
            flash(f'У контакта {self.name} есть сделки', 'warning')
            return
        db.session.delete(self)
