import json

from flask import render_template, request
from flask_login import login_required

from clim.utils import actions_in

from ..models import db
from .models import Contact
from .utils import ROLES
from . import bp


@bp.route('/', methods=['GET', 'POST'])
@login_required
def contacts():
    page = request.args.get('page', 1, type=int)

    if request.method == 'POST':
        return actions_in(Contact.get)

    contacts = db.paginate(db.select(Contact),
                           per_page=10, error_out=False, page=page)
    return render_template('contact/contacts.html', contacts=contacts,
                           child_obj=Contact(contact_id=0))


@bp.route('/contact_info', methods=['GET', 'POST'])
@login_required
def contact_settings():
    contact = Contact.get(request.args.get('contact_id')
                          ) or Contact(role=request.args.get('role', ''))

    if request.method == 'POST':
        return actions_in(contact)

    return render_template('contact/contact/main.html',
                           contact=contact, roles=ROLES)


@bp.route('/ajax_contacts', methods=['GET'])
@login_required
def ajax_contacts():
    contacts = db.select(Contact)
    if (role := request.args.get('role', '')):
        contacts = contacts.filter_by(role=role)
    if (search := request.args.get('search', '').lower()):
        contacts = (contacts.where(Contact.name.contains(search) |
                                   Contact.phone.contains(search) |
                                   Contact.email.contains(search)))

    per_page = 20
    page = request.args.get('page', 1, type=int)
    contacts = db.paginate(contacts,
                           page=page, per_page=per_page, error_out=False)

    result = []
    for contact in contacts:
        contacts_list = [contact.phone, contact.email]
        contacts_list = filter(lambda s: s not in [None, ''], contacts_list)
        result.append({'id': str(contact.contact_id),
                       'text': contact.name,
                       'subtext': ', '.join(contacts_list)})

    return json.dumps({'results': result, 'pagination': {'more': bool(result)}})
