from ..models import db
from .utils import DealUtils, StageUtils


class Deal(DealUtils, db.Model):
    __tablename__ = 'adm_deal'

    deal_id = db.Column(db.Integer, primary_key=True)
    # name = db.Column(db.String(128))
    contact_id = db.Column(db.Integer, db.ForeignKey('adm_contact.contact_id'))
    stage_id = db.Column(db.Integer, db.ForeignKey('adm_deal_stage.stage_id'))
    details = db.Column(db.Text)
    products = db.Column(db.Text)
    consumables = db.Column(db.Text)
    expenses = db.Column(db.Text)
    posted = db.Column(db.Boolean)
    date_add = db.Column(db.Date)
    date_end = db.Column(db.Date)
    sum = db.Column(db.Float(15.4))
    analytics = db.Column(db.Text)
    profit = db.Column(db.Float(15.4))
    sort_order = db.Column(db.Integer)


class DealStage(StageUtils, db.Model):
    __tablename__ = 'adm_deal_stage'

    stage_id = db.Column(db.Integer, primary_key=True,)
    name = db.Column(db.String(128))
    type = db.Column(db.String(64))
    sort_order = db.Column(db.Integer, default=0)
    color = db.Column(db.String(45))
    deals = db.relationship('Deal', backref=db.backref('stage', lazy=True),
                            order_by='Deal.sort_order')

    @property
    def completed(self):
        return 'end_' in self.type
