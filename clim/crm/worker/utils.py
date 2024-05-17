from flask import flash, url_for

from ..models import db


class WorkerUtils:
    URL_PREFIX = '.worker_'

    @property
    def actions(self):
        return {
            'save': [True],
            'delete': [self.worker_id, 'Удадить', 'Удалить работника?', '']
        }

    @property
    def url_id(self):
        return dict(worker_id=self.worker_id) if self.worker_id else {}

    def pages_settings(self):
        return {'settings': [True, 'Настройки']}

    def save(self):
        data = self.save_data

        self.name = data.get('name', '')
        self.start_day = data.get('start_day', '')
        self.end_day = data.get('end_day', '')
        return {'url': url_for('.worker_settings', worker_id=self.worker_id)}

    def delete(self):
        if self.employments:
            flash(f'У работника {self.name} есть запланированные задачи', 'warning')
        else:
            setattr(self, self.primary_attr_name, None)
            db.session.delete(self)
