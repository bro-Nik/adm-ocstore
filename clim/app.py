from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import redis
from celery import Celery


db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('settings.py')

    db.init_app(app)

    with app.app_context():
        if db.engine.url.drivername == 'sqllite':
            migrate.init_app(app, db, render_as_batch=True)
        else:
            migrate.init_app(app, db)
        db.create_all()
    
    return app


app = create_app()


def make_celery(app):
    celery = Celery(app.name)
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = make_celery(app)
redis = redis.StrictRedis('127.0.0.1', 6379)



if __name__ == '__main__':
    db.create_all()
    app.run(port=5001)
