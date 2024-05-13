from flask import Blueprint


bp = Blueprint('category', __name__, template_folder='templates', static_folder='static')

from . import routes
