import re

import pytest

from app import create_app
from app.config import TestingConfig


class SecurityTestingConfig(TestingConfig):
    WTF_CSRF_ENABLED = True
    RATELIMIT_STORAGE_URI = 'memory://'


@pytest.fixture
def client():
    app = create_app(SecurityTestingConfig)
    return app.test_client()


def csrf_token_from(response):
    match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', response.data)
    assert match is not None
    return match.group(1).decode()


def test_form_requests_require_a_valid_csrf_token(client):
    token = csrf_token_from(client.get('/register'))
    form_data = {
        'username': 'csrf_user',
        'email': 'csrf@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
    }

    rejected = client.post('/register', data=form_data)
    assert rejected.status_code == 400

    accepted = client.post('/register', data={**form_data, 'csrf_token': token})
    assert accepted.status_code == 302


def test_json_requests_accept_csrf_header_and_reject_missing_token(client):
    payload = {
        'origin_lat': 28.4,
        'origin_lon': 77.3,
        'dest_lat': 28.5,
        'dest_lon': 77.4,
        'mode': 'transit',
    }

    rejected = client.post('/api/routes/calculate', json=payload)
    assert rejected.status_code == 400

    token = csrf_token_from(client.get('/login'))
    accepted = client.post(
        '/api/routes/calculate',
        json=payload,
        headers={'X-CSRFToken': token},
    )
    assert accepted.status_code == 200


def test_login_is_rate_limited(client):
    token = csrf_token_from(client.get('/login'))
    for _ in range(5):
        response = client.post(
            '/login',
            data={'identifier': 'unknown', 'password': 'invalid', 'csrf_token': token},
        )
        assert response.status_code == 200

    limited = client.post(
        '/login',
        data={'identifier': 'unknown', 'password': 'invalid', 'csrf_token': token},
    )
    assert limited.status_code == 429
