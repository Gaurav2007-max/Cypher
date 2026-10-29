import json
from io import BytesIO
from types import SimpleNamespace
from urllib.error import URLError
from urllib.parse import parse_qs

import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import City, User
from app.services import emergency_kit
from app.services.emergency_kit import EmergencyKitSourceError, build_emergency_kit


@pytest.fixture
def client():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        user = User(username='kit_tester', email='kit@example.test', role='tourist')
        user.set_password('pass123')
        city = City(
            name='Faridabad',
            state='Haryana',
            country='India',
            latitude=28.4089,
            longitude=77.3178,
        )
        db.session.add_all([user, city])
        db.session.commit()
        city_id = city.id
        yield app.test_client(), city_id
        db.session.remove()
        db.drop_all()


def _city(country='India'):
    return SimpleNamespace(
        name='Faridabad',
        state='Haryana',
        country=country,
        latitude=28.4089,
        longitude=77.3178,
    )


def test_build_emergency_kit_includes_attributed_facilities_roads_and_national_number(monkeypatch):
    overpass_response = {
        'elements': [
            {
                'type': 'node',
                'id': 42,
                'lat': 28.41,
                'lon': 77.32,
                'tags': {'amenity': 'police', 'name': 'Example Police Station', 'phone': '112'},
            },
            {
                'type': 'way',
                'id': 43,
                'center': {'lat': 28.42, 'lon': 77.33},
                'geometry': [{'lat': 28.42, 'lon': 77.33}],
                'tags': {'amenity': 'hospital', 'name': 'Example Hospital'},
            },
            {
                'type': 'way',
                'id': 44,
                'geometry': [{'lat': 28.4, 'lon': 77.3}, {'lat': 28.41, 'lon': 77.31}],
                'tags': {'highway': 'primary'},
            },
        ]
    }

    def fake_urlopen(request, timeout):
        assert request.full_url == emergency_kit.OVERPASS_URL
        assert timeout == 30
        query = parse_qs(request.data.decode('ascii'))['data'][0]
        assert '.facilities out center;' in query
        assert '.roads out geom;' in query
        return BytesIO(json.dumps(overpass_response).encode('utf-8'))

    monkeypatch.setattr(emergency_kit, 'urlopen', fake_urlopen)
    kit = build_emergency_kit(_city())

    assert kit['city']['name'] == 'Faridabad'
    assert kit['emergency_numbers'][0]['number'] == '112'
    assert kit['emergency_numbers'][0]['scope'] == 'National'
    assert kit['facilities'][0]['name'] == 'Example Police Station'
    assert kit['facilities'][1]['category'] == 'hospital'
    assert kit['roads'][0]['type'] == 'primary'
    assert kit['safe_avoid_zones'] == []
    assert 'OpenStreetMap' in kit['attribution']


def test_build_emergency_kit_does_not_assume_india_number_for_other_countries(monkeypatch):
    monkeypatch.setattr(
        emergency_kit,
        'urlopen',
        lambda request, timeout: BytesIO(b'{"elements":[]}'),
    )

    kit = build_emergency_kit(_city(country='Nepal'))

    assert kit['emergency_numbers'] == []


def test_build_emergency_kit_reports_openstreetmap_unavailability(monkeypatch):
    def fail_request(request, timeout):
        raise URLError('offline')

    monkeypatch.setattr(emergency_kit, 'urlopen', fail_request)

    with pytest.raises(EmergencyKitSourceError, match='Could not retrieve OpenStreetMap'):
        build_emergency_kit(_city())


def test_build_emergency_kit_rejects_invalid_city_coordinates(monkeypatch):
    monkeypatch.setattr(
        emergency_kit,
        'urlopen',
        lambda request, timeout: pytest.fail('must not fetch for invalid coordinates'),
    )

    with pytest.raises(EmergencyKitSourceError, match='invalid coordinates'):
        build_emergency_kit(SimpleNamespace(
            name='Invalid',
            state='State',
            country='India',
            latitude=float('nan'),
            longitude=77.3,
        ))


def test_emergency_kit_api_requires_login_and_uses_active_city(client, monkeypatch):
    test_client, city_id = client
    response = test_client.get(f'/api/safety/emergency-kit/{city_id}')
    assert response.status_code == 401

    test_client.post('/login', data={'identifier': 'kit_tester', 'password': 'pass123'})
    safety_page = test_client.get('/safety')
    assert safety_page.status_code == 200
    assert f'data-city-id="{city_id}"'.encode() in safety_page.data

    monkeypatch.setattr(
        'app.routes.api_safety.build_emergency_kit',
        lambda city: {'city': {'name': city.name}, 'facilities': []},
    )
    response = test_client.get(f'/api/safety/emergency-kit/{city_id}')

    assert response.status_code == 200
    assert response.get_json()['city']['name'] == 'Faridabad'


def test_emergency_kit_api_surfaces_data_source_errors(client, monkeypatch):
    test_client, city_id = client
    test_client.post('/login', data={'identifier': 'kit_tester', 'password': 'pass123'})

    def fail(_city):
        raise EmergencyKitSourceError('Could not retrieve OpenStreetMap data.')

    monkeypatch.setattr('app.routes.api_safety.build_emergency_kit', fail)
    response = test_client.get(f'/api/safety/emergency-kit/{city_id}')

    assert response.status_code == 502
    assert 'OpenStreetMap' in response.get_json()['error']
