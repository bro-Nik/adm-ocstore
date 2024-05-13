import json

from flask import render_template, request, url_for
from flask_login import login_required

from clim.utils import actions_in

from ..models import db
from .models import Contact
from .utils import ROLES, get_contact
from . import bp


@bp.route('/ajax_contacts', methods=['GET'])
@login_required
def ajax_contacts():
    per_page = 20
    search = request.args.get('search')
    role = request.args.get('role')

    select = Contact.query.where(Contact.role == role) if role else Contact.query

    if search:
        select = (select.where(Contact.name.contains(search) |
                               Contact.phone.contains(search) |
                               Contact.email.contains(search)))

    contacts = select.paginate(page=request.args.get('page', 1, type=int),
                               per_page=per_page, error_out=False)

    result = {'results': []}
    for contact in contacts:
        contacts_list = [contact.phone, contact.email]
        contacts_list = filter(lambda s: s not in [None, ''], contacts_list)
        result['results'].append({'id': str(contact.contact_id),
                                  'text': contact.name,
                                  # 'phone': contact.phone,
                                  # 'email': contact.email,
                                  'subtext': ', '.join(contacts_list)})
    result['pagination'] = {'more': bool(len(result['results']) >= per_page)}

    return json.dumps(result)


@bp.route('/contacts', methods=['GET', 'POST'])
@login_required
def contacts():
    if request.method == 'POST':
        # Действия
        actions_in(request.data, get_contact)
        db.session.commit()
        return ''

    contacts = db.session.execute(db.select(Contact)).scalars()
    return render_template('contact/contacts.html', contacts=contacts)


@bp.route('/contact_info', methods=['GET', 'POST'])
@login_required
def contact_info():
    role = request.args.get('role', '')
    contact = get_contact(request.args.get('contact_id')) or Contact(role=role)

    if request.method == 'POST':
        if not contact.contact_id:
            db.session.add(contact)

        data = json.loads(request.data) if request.data else {}
        contact.name = data.get('name', '')
        contact.phone = data.get('phone', '')
        contact.email = data.get('email', '')
        contact.role = data.get('role', '')
        db.session.commit()
        return {'redirect': url_for('.contact_info', contact_id=contact.contact_id)}

    return render_template('contact/contact/main.html', contact=contact,
                           roles=ROLES)
