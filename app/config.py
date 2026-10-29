import os
import secrets
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def resolve_database_uri(database_uri):
    url = make_url(database_uri)
    if url.drivername in {'postgres', 'postgresql'}:
        return url.set(drivername='postgresql+psycopg').render_as_string(hide_password=False)
    if (
        url.drivername.startswith('sqlite')
        and url.database
        and url.database != ':memory:'
        and not url.database.startswith('file:')
        and not os.path.isabs(url.database)
    ):
        database_path = os.path.abspath(os.path.join(BASE_DIR, url.database))
        return url.set(database=database_path).render_as_string(hide_password=False)
    return database_uri


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    if os.getenv('RENDER') and not SECRET_KEY:
        raise RuntimeError('Set a strong SECRET_KEY in the Render environment before starting the service.')
    SECRET_KEY = SECRET_KEY or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = resolve_database_uri(
        os.getenv('DATABASE_URL')
        or os.getenv('DATABASE_URI')
        or f'sqlite:///{os.path.join(BASE_DIR, "traveltech.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = bool(os.getenv('RENDER'))
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    
    # SMTP / Email alerts
    SMTP_TEST_MODE = os.getenv('SMTP_TEST_MODE', 'True').lower() in ('true', '1', 'yes')
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_DEFAULT_SENDER = os.getenv('SMTP_DEFAULT_SENDER') or SMTP_USERNAME
    
    # Geolocation / Proximity
    DEFAULT_PROXIMITY_RADIUS_METERS = int(os.getenv('DEFAULT_PROXIMITY_RADIUS_METERS', 50))
    LOCATION_HISTORY_RETENTION_MINUTES = int(os.getenv('LOCATION_HISTORY_RETENTION_MINUTES', 10))

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SMTP_TEST_MODE = True
