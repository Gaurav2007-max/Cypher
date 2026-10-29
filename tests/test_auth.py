import pytest
from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models.user import User, UserProfile
from app.config import BASE_DIR, resolve_database_uri

def test_relative_sqlite_database_uri_resolves_from_project_root():
    uri = resolve_database_uri('sqlite:///traveltech.db')
    expected_path = f'{BASE_DIR}\\traveltech.db'
    assert uri.endswith(expected_path)

def test_in_memory_sqlite_database_uri_is_preserved():
    assert resolve_database_uri('sqlite:///:memory:') == 'sqlite:///:memory:'


def test_render_postgres_database_url_uses_installed_psycopg_driver():
    uri = resolve_database_uri('postgres://travel_user:secret@db.example.com/travel')
    assert uri == 'postgresql+psycopg://travel_user:secret@db.example.com/travel'


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        # Seed test admin, approved authority, unapproved authority, and tourist
        admin = User(username='admin_test', email='admin@test.local', role='admin', authority_approved=True)
        admin.set_password('pass123')

        auth_approved = User(username='auth_appr', email='auth_appr@test.local', role='authority', authority_approved=True)
        auth_approved.set_password('pass123')

        auth_pending = User(username='auth_pend', email='auth_pend@test.local', role='authority', authority_approved=False)
        auth_pending.set_password('pass123')

        tourist = User(username='tourist_test', email='tourist@test.local', role='tourist')
        tourist.set_password('pass123')

        db.session.add_all([admin, auth_approved, auth_pending, tourist])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_tourist_registration(client):
    res = client.post('/register', data={
        'username': 'new_tourist',
        'email': 'new_tourist@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'role': 'tourist',
        'full_name': 'New Tourist'
    }, follow_redirects=True)
    assert res.status_code == 200

    with client.application.app_context():
        user = User.query.filter_by(username='new_tourist').first()
        assert user is not None
        assert user.role == 'tourist'
        assert user.authority_approved is False
        assert user.profile.emergency_consent is False
        assert user.profile.location_tracking_enabled is False

def test_authority_registration_requires_approval(client):
    res = client.post('/register', data={
        'username': 'new_officer',
        'email': 'officer@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'role': 'authority',
        'full_name': 'Officer Bob'
    }, follow_redirects=True)
    assert res.status_code == 200

    with client.application.app_context():
        officer = User.query.filter_by(username='new_officer').first()
        assert officer is not None
        assert officer.role == 'authority'
        # Crucial security check: must be False until admin approves!
        assert officer.authority_approved is False

def test_login_success_and_failure(client):
    # Invalid password
    bad_login = client.post('/login', data={'identifier': 'tourist_test', 'password': 'wrongpassword'}, follow_redirects=True)
    assert b'Invalid login credentials' in bad_login.data

    # Valid password
    good_login = client.post('/login', data={'identifier': 'tourist_test', 'password': 'pass123'}, follow_redirects=False)
    assert good_login.status_code == 302
    assert '/dashboard' in good_login.headers['Location']

def test_rbac_tourist_cannot_access_authority_dashboard(client):
    # Login as tourist
    client.post('/login', data={'identifier': 'tourist_test', 'password': 'pass123'})
    res = client.get('/authority/dashboard')
    assert res.status_code == 403

def test_rbac_unapproved_authority_cannot_access_authority_dashboard(client):
    # Login as pending authority
    client.post('/login', data={'identifier': 'auth_pend', 'password': 'pass123'})
    res = client.get('/authority/dashboard')
    # Must be 403 / pending notice
    assert res.status_code == 403
    assert b'Pending Approval' in res.data or b'awaiting' in res.data

def test_admin_approves_authority(client):
    # Login as admin
    client.post('/login', data={'identifier': 'admin_test', 'password': 'pass123'})
    
    with client.application.app_context():
        pend_user = User.query.filter_by(username='auth_pend').first()
        target_id = pend_user.id
        assert pend_user.authority_approved is False

    res = client.post(f'/admin/approve-authority/{target_id}', follow_redirects=True)
    assert res.status_code == 200

    with client.application.app_context():
        approved_user = User.query.get(target_id)
        assert approved_user.authority_approved is True

def test_admin_rejects_pending_authority(client):
    client.post('/login', data={'identifier': 'admin_test', 'password': 'pass123'})

    with client.application.app_context():
        pending_user = User.query.filter_by(username='auth_pend').first()
        target_id = pending_user.id
        assert pending_user.is_active is True
        assert pending_user.authority_approved is False

    response = client.post(f'/admin/reject-authority/{target_id}', follow_redirects=True)
    assert response.status_code == 200

    with client.application.app_context():
        rejected_user = User.query.get(target_id)
        assert rejected_user.is_active is False
        assert rejected_user.authority_approved is False
