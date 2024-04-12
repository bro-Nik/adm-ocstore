from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import redis
from celery import Celery


db = SQLAlchemy()
migrate = Migrate()
celery = Celery()
redis = redis.StrictRedis('127.0.0.1', 6379)
login_manager = LoginManager()
login_manager.login_view = 'user.login'
login_manager.login_message = 'Пожалуйста, войдите, чтобы получить доступ к этой странице'
login_manager.login_message_category = 'danger'


def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('settings.py')

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    init_celery(app, celery)

    from clim.blueprints import make_blueprints
    make_blueprints(app)

    # with app.app_context():
    #     if db.engine.url.drivername == 'sqllite':
    #         migrate.init_app(app, db, render_as_batch=True)
    #     else:
    #         migrate.init_app(app, db)
    #     db.create_all()
    # 
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
