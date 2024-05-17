from flask import Blueprint

from . import deal, stock, contact, worker, booking, utils


bp = Blueprint('crm', __name__, template_folder='templates', static_folder='static')


# Вложенные blueprints
bp.register_blueprint(stock.bp, url_prefix='/stock')
bp.register_blueprint(deal.bp, url_prefix='/deal')
bp.register_blueprint(contact.bp, url_prefix='/contact')
bp.register_blueprint(worker.bp, url_prefix='/worker')
bp.register_blueprint(booking.bp, url_prefix='/booking')


# Jinja фильтры
bp.add_app_template_filter(utils.money)
bp.add_app_template_filter(utils.smart_int)
bp.add_app_template_filter(utils.smart_date)
bp.add_app_template_filter(utils.smart_phone)
bp.add_app_template_filter(utils.datetime_from_str)
