from flask import flash

from clim.mixins import PageMixin

from ..models import db


class WorkerUtils(PageMixin):
    URL_PREFIX = '.worker_'

    @property
    def actions(self):
        return {
            'save': [True],
            'delete': [self.worker_id, 'Удадить', 'Удалить работника?', '']
        }

    def pages_settings(self):
        return {'settings': [True, 'Настройки']}

    def save(self):
        data = self.save_data

        self.name = data.get('name', '')
        self.start_day = data.get('start_day', '')
        self.end_day = data.get('end_day', '')
        db.session.flush()

    def delete(self):
        if self.employments:
            flash(f'У работника {self.name} есть запланированные задачи', 'warning')
            return False

        super().delete()
