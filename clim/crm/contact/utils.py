from flask import flash

from clim.mixins import JsonDetailsMixin, PageMixin

from ..models import db


ROLES = {'client': 'Клиент', 'provider': 'Поставщик'}


class ContactUtils(PageMixin, JsonDetailsMixin):
    URL_PREFIX = '.contact_'

    @property
    def actions(self):
        return {
            'save': [True],
            'delete': [self.contact_id, 'Удадить', 'Удалить контакт?', '']
        }

    def pages_settings(self):
        return {'settings': [True, 'Настройки']}

    def save(self):
        data = self.save_data

        self.name = data.get('name', '')
        self.phone = data.get('phone', '')
        self.email = data.get('email', '')
        self.role = data.get('role', '')
        db.session.flush()

    def delete(self):
        if self.deals:
            flash(f'У контакта {self.name} есть сделки', 'warning')
            return False

        super().delete()
