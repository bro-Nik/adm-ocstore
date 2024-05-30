import json
from flask import render_template, request
from flask_login import login_required

from clim.utils import actions_in

from ..utils import smart_int
from ..models import db
from clim.user.models import User
from . import bp


@bp.route('/', methods=['GET', 'POST'])
@login_required
def users():
    page = request.args.get('page', 1, type=int)

    if request.method == 'POST':
        return actions_in(User.get)

    users = db.paginate(db.select(User),
                          per_page=10, error_out=False, page=page)
    return render_template('user/users.html', users=users,
                           child_obj=User(id=0))
