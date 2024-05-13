from flask import Blueprint


bp = Blueprint('report', __name__, template_folder='templates', static_folder='static')

from . import routes
