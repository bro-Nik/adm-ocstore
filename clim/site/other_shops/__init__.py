from flask import Blueprint


bp = Blueprint('other_shops', __name__, template_folder='templates', static_folder='static')

from . import routes
