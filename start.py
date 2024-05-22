from clim.app import create_app, init_celery, celery


app = create_app()
init_celery(app, celery)
