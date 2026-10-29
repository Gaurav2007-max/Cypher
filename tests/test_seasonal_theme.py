from datetime import datetime as DateTime
from types import SimpleNamespace

import app as app_module
from app import get_site_theme
from app.config import TestingConfig
from app.extensions import db
from app.models.city import City
from app.models.destination import Destination


def test_olive_theme_is_used_for_every_city_and_month():
    for city_name in ('Shimla', 'Faridabad', 'Agra', 'Jaipur', 'Varanasi', None):
        for month in range(1, 13):
            assert get_site_theme(city_name, month) == 'olive'


def test_destination_images_match_their_categories():
    forest = Destination(name='Asola Bhatti Sanctuary — Peacock Hidden Lake')
    lake = Destination(name='Badkhal Lake & Eco Biodiversity Ridge')
    temple = Destination(name='Sri Sri Radha Govind Temple (ISKCON Faridabad)')

    assert 'photo-1441974231531-c6227db76b6e' in forest.display_image_url
    assert 'photo-1470770841072-f978cf4d019e' in lake.display_image_url
    assert 'Iskcon_Delhi_Temple.jpg' in temple.display_image_url


def test_selected_shimla_uses_olive_theme_in_all_templates(monkeypatch):
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

    assert b'data-seasonal-theme="olive"' in response.data
    assert b'class="olive-theme"' in response.data
