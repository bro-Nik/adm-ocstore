from flask import Blueprint


bp = Blueprint('booking', __name__, template_folder='templates', static_folder='static')

from . import routes
