from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from redis import Redis
from celery import Celery

from clim.mixins import ModelMixin


# db = SQLAlchemy()
db = SQLAlchemy(model_class=ModelMixin)
migrate = Migrate()
celery = Celery()
# redis = redis.StrictRedis('127.0.0.1', 6379)
redis = Redis(host='redis', port=6379)
login_manager = LoginManager()
login_manager.login_view = 'user.login'
login_manager.login_message = 'Пожалуйста, войдите, чтобы получить доступ к этой странице'
login_manager.login_message_category = 'warning'


def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('settings.py')

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    init_celery(app, celery)

    from . import site, main, user, crm
    app.register_blueprint(crm.bp, url_prefix='/crm')
    app.register_blueprint(site.bp, url_prefix='/site')
    app.register_blueprint(user.bp, url_prefix='/user')
    app.register_blueprint(main.bp)

    return app


def init_celery(app, celery):
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
