from flask import Blueprint

from . import other_shops, option, product, category, report


bp = Blueprint('site', __name__, template_folder='templates', static_folder='static')


# Вложенные blueprints
bp.register_blueprint(other_shops.bp, url_prefix='/other_shops')
bp.register_blueprint(option.bp, url_prefix='/option')
bp.register_blueprint(product.bp, url_prefix='/product')
bp.register_blueprint(category.bp, url_prefix='/category')
bp.register_blueprint(report.bp, url_prefix='/report')


# Jinja фильтры
# bp.add_app_template_filter(utils.money)
# bp.add_app_template_filter(utils.smart_int)
# bp.add_app_template_filter(utils.to_json)
# bp.add_app_template_filter(utils.smart_date)
# bp.add_app_template_filter(utils.how_long_ago)
# bp.add_app_template_filter(utils.smart_phone)
# bp.add_app_template_filter(utils.datetime_from_str)
