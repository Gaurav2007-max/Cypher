from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import City, Destination, User
from seed_data import seed


def test_health_endpoint_checks_database_connection():
    app = create_app(TestingConfig)
    response = app.test_client().get('/health')
    assert response.status_code == 200
    assert response.get_json() == {'status': 'ok'}


def test_demo_seed_populates_empty_database_and_never_resets_existing_data():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        assert seed(app) is True
        assert City.query.count() == 5
        assert Destination.query.count() > 0
        assert User.query.filter_by(username='alex_traveler').first() is not None

        extra_city = City(
            name='Preserved city',
            state='Test State',
            country='India',
            latitude=20,
            longitude=70
        )
        db.session.add(extra_city)
        db.session.commit()
        assert seed(app) is False
        assert City.query.filter_by(name='Preserved city').first() is not None
        assert City.query.count() == 6
        assert Destination.query.count() > 0


def test_seed_can_create_public_sample_content_without_demo_accounts(monkeypatch):
    monkeypatch.setenv('SEED_DEMO_USERS', 'false')
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        assert seed(app) is True
        assert City.query.count() == 5
        assert Destination.query.count() > 0
        assert User.query.count() == 0
