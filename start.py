from clim.app import create_app, init_celery, celery


app = create_app()
init_celery(app, celery)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
