from flask import Blueprint


bp = Blueprint('product', __name__, template_folder='templates', static_folder='static')

from . import routes
