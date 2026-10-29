from datetime import datetime as DateTime
from types import SimpleNamespace

import app as app_module
from app import get_site_theme
from app.config import TestingConfig
from app.extensions import db
from app.models.city import City
from app.models.destination import Destination


def test_shimla_uses_winter_theme_during_winter_months():
    for month in (12, 1, 2):
        assert get_site_theme('Shimla', month) == 'winter'


def test_winter_theme_is_limited_to_shimla_and_winter_months():
    assert get_site_theme('Shimla', 3) == 'olive'
    assert get_site_theme('Faridabad', 1) == 'olive'
    assert get_site_theme(None, 1) == 'olive'


def test_destination_images_match_their_categories():
    forest = Destination(name='Asola Bhatti Sanctuary — Peacock Hidden Lake')
    lake = Destination(name='Badkhal Lake & Eco Biodiversity Ridge')
    temple = Destination(name='Sri Sri Radha Govind Temple (ISKCON Faridabad)')

    assert 'photo-1441974231531-c6227db76b6e' in forest.display_image_url
    assert 'photo-1470770841072-f978cf4d019e' in lake.display_image_url
    assert 'Iskcon_Delhi_Temple.jpg' in temple.display_image_url


def test_selected_shimla_winter_theme_is_exposed_to_all_templates(monkeypatch):
    class JanuaryDateTime:
        @staticmethod
        def now():
            return DateTime(2026, 1, 15)

        @staticmethod
        def utcnow():
            return DateTime(2026, 1, 15)

    monkeypatch.setattr(app_module, 'datetime', JanuaryDateTime)
    monkeypatch.setattr(
        app_module,
        'get_current_user',
        lambda: SimpleNamespace(is_tourist=True, profile=None, role='tourist')
    )
    app = app_module.create_app(TestingConfig)
    with app.app_context():
        city = City(
            name='Shimla',
            state='Himachal Pradesh',
            country='India',
            latitude=31.1048,
            longitude=77.1734
        )
        db.session.add(city)
        db.session.commit()
        city_id = city.id

    with app.test_client() as client:
        with client.session_transaction() as session:
            session['selected_city_id'] = city_id
        response = client.get('/login')

    assert b'data-seasonal-theme="winter"' in response.data
