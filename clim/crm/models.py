from clim.models import *


class Service(db.Model):
    __tablename__ = 'adm_deal_service'

    service_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45))
    time = db.Column(db.Integer)
