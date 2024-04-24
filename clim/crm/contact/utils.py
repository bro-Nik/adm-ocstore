from .models import db, Contact


ROLES = {'client': 'Клиент', 'provider': 'Поставщик'}


def get_contact(contact_id):
    if contact_id:
        return db.session.execute(
            db.select(Contact).filter_by(contact_id=contact_id)).scalar()
