from flask import flash, url_for

from ..models import db


ROLES = {'client': 'Клиент', 'provider': 'Поставщик'}


class ContactUtils:
    URL_PREFIX = '.contact_'

    @property
    def actions(self):
        return {
            'save': [True],
            'delete': [self.contact_id, 'Удадить', 'Удалить контакт?', '']
        }

    @property
    def url_id(self):
        return dict(contact_id=self.contact_id) if self.contact_id else {}

    def pages_settings(self):
        return {'settings': [True, 'Настройки']}

    def save(self):
        data = self.save_data

        self.name = data.get('name', '')
        self.phone = data.get('phone', '')
        self.email = data.get('email', '')
        self.role = data.get('role', '')
        return {'url': url_for('.contact_settings', contact_id=self.contact_id)}

    def delete(self):
        if self.deals:
            flash(f'У контакта {self.name} есть сделки', 'warning')
            return False

        setattr(self, self.primary_attr_name, None)
        db.session.delete(self)
