import os
from dotenv import load_dotenv, find_dotenv

basedir = os.path.abspath(os.path.dirname(__name__))
load_dotenv(os.path.join(basedir, '.env'))
load_dotenv(find_dotenv())


SECRET_KEY = os.environ.get('SECRET_KEY')
SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
FLASK_DEBUG = os.environ.get('FLASK_DEBUG')
CATALOG_DOMAIN = os.environ.get('CATALOG_DOMAIN')

IMAGE_PATH = os.environ.get('IMAGE_PATH')
DOWNLOAD_PATH = os.environ.get('DOWNLOAD_PATH')

PROXY_KEY = os.environ.get('PROXY_KEY')
