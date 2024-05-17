from ..models import db
from .utils import ContactUtils


class Contact(ContactUtils, db.Model):
    __tablename__ = 'adm_contact'

    contact_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    phone = db.Column(db.String(64))
    email = db.Column(db.String(64))
    role = db.Column(db.String(64))
    deals = db.relationship('Deal', backref=db.backref('contact', lazy=True))
    movements = db.relationship('StockMovement',
                                backref=db.backref('contact', lazy=True))
