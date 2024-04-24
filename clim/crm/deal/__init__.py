from flask import Blueprint


bp = Blueprint('deal', __name__, template_folder='templates', static_folder='static')

from . import routes
