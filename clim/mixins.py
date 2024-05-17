import json

from flask_sqlalchemy.model import Model
from flask import flash, url_for


class ModelMixin(Model):

    @property
    def name(self):
        return self.description.name if self.description else ''

    def try_action(self, action):
        if not hasattr(self, action) or action not in self.actions:
            flash(f'Метод {action} не найден')
        elif not self.actions.get(action, [])[0]:
            flash(f'Метод {action} не разрешен')
        else:
            return getattr(self, action)()
        return False

    @staticmethod
    def child_dependencies() -> list:
        """ Список зависимых столбцов при удалении """
        return []

    def delete_dependencies(self) -> None:
        """ Удаление зависимых столбцов """
        primary_attr = self.primary_attr_name
        for item in self.child_dependencies():
            dependence = getattr(self, item, None)
            if dependence:
                # Приводим к списку
                dependence = dependence if isinstance(dependence, list) else [dependence]
                for item in dependence:
                    if hasattr(item, primary_attr):
                        setattr(item, primary_attr, None)
                    item.delete()

    def delete(self) -> None:
        """ Удаление объекта """
        from clim.app import db
        self.delete_dependencies()
        setattr(self, self.primary_attr_name, None)
        print(f'id={self.get_id}')
        db.session.delete(self)

    @classmethod
    def get_all(cls, **kwargs):
        """ Получение всех строк объекта """
        from clim.app import db
        select = db.select(cls)
        if kwargs:
            select = select.filter_by(**kwargs)
        if hasattr(cls, 'sort_order'):
            select = select.order_by(cls.sort_order)

        return db.session.execute(select).scalars()

    @classmethod
    def get(cls, unique_id=None, **kwargs):
        """ Получение объекта по primary key """
        from clim.app import db
        if not kwargs:
            return db.session.get(cls, unique_id)
        return db.session.execute(db.select(cls).filter_by(**kwargs)).scalar()

    @classmethod
    def create(cls, *args, **kwargs):
        from clim.app import db
        obj = cls(*args, **kwargs)
        db.session.add(obj)
        return obj

    def get_json(self, attr):
        # Кэштруем
        attr_name = f'{attr}_'
        if not hasattr(self, attr_name):
            value = getattr(self, attr, '')
            setattr(self, attr_name, json.loads(value) if value else None)
        return getattr(self, attr_name)

    @property
    def primary_attr_name(self):
        """ Получение имени столбца primary key """
        return list(self.__table__.primary_key)[0].name

    @property
    def get_id(self):
        """ Получение имени столбца primary key """
        attr = self.primary_attr_name
        return getattr(self, attr, None)


class PageMixin:
    URL_PREFIX = ''
    PAGES = {}

    @property
    def actions(self) -> dict:
        """ Варианты действий над объектом """

        """
        Словарь вида
        {'атрибут действия':
        ['текст кнопки', 'заголовок модульного', 'описание действия'], 'разрешено ли действие'}
        """
        return {}

    def url_id(self):
        return {self.primary_attr_name: self.get_id} if self.get_id else {}

    def pages_settings(self):
        return {}

    @property
    def url_actions(self):
        url_actions = self.urls(key_type='actions')
        if url_actions:
            return url_actions[0][2]

    def urls(self, key_name=None, key_type=None):
        # Тип ключа ('new', 'actions')
        if key_type:
            key_name = self.PAGES.get(key_type)

        # Получение настроек
        settings = self.pages_settings()
        if key_name:
            settings = {key_name: settings.get(key_name) or [None, None]}

        # Выбираем разрешенные
        urls = [(k, s[1]) for k, s in settings.items() if s[0]]

        result = []
        url_id = self.url_id()
        for key, text in urls:
            result.append([key, text, url_for(f'{self.URL_PREFIX}{key}', **url_id)])
        return result
