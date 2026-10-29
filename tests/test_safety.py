from datetime import datetime, timedelta
import smtplib
from urllib.parse import urlparse
import pytest
from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import (
    EmergencyContact,
    EmergencyContactVerification,
    EmergencyIncident,
    LocationSample,
    PendingSafetyAction,
    User,
    UserProfile,
)

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()

        tourist = User(username='safety_tester', email='tester@traveltech.local', role='tourist')
        tourist.set_password('pass123')
        db.session.add(tourist)
        db.session.flush()
        db.session.add(UserProfile(
            user_id=tourist.id,
            emergency_consent=True,
            location_tracking_enabled=True,
            sensor_consent=False
        ))

        contact = EmergencyContact(
            user_id=tourist.id,
            name='Global Care Assistance',
            email='emergency.assist@globalcare.com',
            phone='+1 800 555 0199',
            relationship='Travel Agency',
            is_agency=True,
            is_primary=True
        )
        db.session.add(contact)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()


def test_safety_center_requires_profile_consent_before_motion_sensing(client, app):
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})

    response = client.get('/safety')
    assert response.status_code == 200
    assert b'Motion sensing is off. Enable sensor consent in your profile' in response.data
    assert b'id="enableMotionDetection"' not in response.data
    assert b'Review location and motion consent' in response.data


def test_safety_center_offers_motion_enable_after_profile_consent(client, app):
    with app.app_context():
        user = User.query.filter_by(username='safety_tester').first()
        user.profile.sensor_consent = True
        db.session.commit()

    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})

    response = client.get('/safety')
    assert response.status_code == 200
    assert b'id="enableMotionDetection" data-sensor-consent="true"' in response.data
    assert b'Safety monitoring automatically starts when the browser grants sensor and location access.' in response.data
    assert b'Monitoring stays enabled across TravelTech pages' in response.data
    assert b'cannot monitor a powered-off phone' in response.data


def test_safety_monitoring_requires_saved_location_consent(client, app):
    with app.app_context():
        user = User.query.filter_by(username='safety_tester').first()
        user.profile.sensor_consent = True
        user.profile.location_tracking_enabled = False
        db.session.commit()

    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})
    response = client.get('/safety')

    assert response.status_code == 200
    assert b'id="enableMotionDetection"' not in response.data
    assert b'Enable location tracking consent in your profile' in response.data


def test_saving_both_safety_consents_enables_automatic_monitoring_settings(client, app):
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})
    response = client.post('/profile', data={
        'full_name': 'Safety Tester',
        'proximity_radius': '50',
        'speech_rate': '1.0',
        'preferred_city_id': '',
        'location_tracking_enabled': 'on',
        'sensor_consent': 'on',
    })

    assert response.status_code == 302
    with app.app_context():
        profile = User.query.filter_by(username='safety_tester').first().profile
        assert profile.location_tracking_enabled is True
        assert profile.sensor_consent is True


def dispatch_queued_action(client, app, action_id):
    with app.app_context():
        action = db.session.get(PendingSafetyAction, action_id)
        action.dispatch_at = datetime.utcnow() - timedelta(seconds=1)
        db.session.commit()

    from app.services.safety_dispatch import dispatch_due_safety_actions
    dispatch_due_safety_actions(app)


def test_direct_sos_bypass_is_rejected(client):
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})

    res = client.post('/api/safety/sos', json={
        'latitude': 28.4089,
        'longitude': 77.3178,
        'accuracy': 12.5,
        'incident_type': 'sos_manual'
    })
    assert res.status_code == 410
    assert EmergencyIncident.query.count() == 0


def test_manual_sos_waits_for_server_countdown_and_safe_test_mode(client, app):
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})

    res = client.post('/api/safety/sos/prepare', json={
        'latitude': 28.4089,
        'longitude': 77.3178,
        'accuracy': 12.5,
        'incident_type': 'sos_manual'
    })
    assert res.status_code == 202
    assert res.get_json()['action']['seconds_remaining'] > 0
    with app.app_context():
        assert EmergencyIncident.query.count() == 0
    action_id = res.get_json()['action']['id']
    dispatch_queued_action(client, app, action_id)
    status = client.get(f'/api/safety/actions/{action_id}').get_json()
    assert status['action']['status'] == 'dispatched'

    data = status['incident']
    assert data['email_sent'] is False
    assert data['email_delivery_status'] == 'test_mode'
    assert data['email_recipient'] == 'emergency.assist@globalcare.com'
    with app.app_context():
        incident = EmergencyIncident.query.first()
        assert incident is not None
        assert incident.incident_type == 'sos_manual'
        assert incident.latitude == 28.4089
        assert incident.email_sent is False


def test_pending_sos_can_be_cancelled_before_deadline(client, app):
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})
    prepared = client.post('/api/safety/sos/prepare', json={'incident_type': 'sos_manual'}).get_json()
    action_id = prepared['action']['id']
    response = client.post(f'/api/safety/actions/{action_id}/cancel')
    assert response.status_code == 200
    dispatch_queued_action(client, app, action_id)
    assert client.get(f'/api/safety/actions/{action_id}').get_json()['action']['status'] == 'cancelled'
    with app.app_context():
        assert EmergencyIncident.query.count() == 0


def test_safety_dispatch_failure_is_visible_and_does_not_stick_pending(client, app, monkeypatch):
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})
    prepared = client.post('/api/safety/sos/prepare', json={'incident_type': 'sos_manual'}).get_json()
    action_id = prepared['action']['id']
    with app.app_context():
        action = db.session.get(PendingSafetyAction, action_id)
        action.dispatch_at = datetime.utcnow() - timedelta(seconds=1)
        db.session.commit()

    def fail_delivery(**kwargs):
        raise RuntimeError('simulated dispatcher failure')

    monkeypatch.setattr('app.services.safety_dispatch.EmailService.send_emergency_alert', fail_delivery)
    from app.services.safety_dispatch import dispatch_due_safety_actions
    dispatch_due_safety_actions(app)
    action = client.get(f'/api/safety/actions/{action_id}').get_json()['action']
    assert action['status'] == 'failed'
    assert 'Contact emergency services directly' in action['error']


def test_sos_requires_explicit_emergency_consent(client, app):
    with app.app_context():
        profile = User.query.filter_by(username='safety_tester').first().profile
        profile.emergency_consent = False
        db.session.commit()
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})
    response = client.post('/api/safety/sos/prepare', json={'incident_type': 'sos_manual'})
    assert response.status_code == 403


def test_sos_live_smtp_delivery_when_configured(client, app, monkeypatch):
    class FakeSMTP:
        def __init__(self, server, port, timeout):
            self.server = server
            self.port = port
            self.sent_messages = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            assert username == 'smtp-user@example.com'
            assert password == 'test-password'

        def send_message(self, message):
            self.sent_messages.append(message)

    smtp_instances = []

    def fake_smtp(*args, **kwargs):
        smtp = FakeSMTP(*args, **kwargs)
        smtp_instances.append(smtp)
        return smtp

    monkeypatch.setattr('app.services.email_service.smtplib.SMTP', fake_smtp)
    app.config.update(
        SMTP_TEST_MODE=False,
        SMTP_USERNAME='smtp-user@example.com',
        SMTP_PASSWORD='test-password',
        SMTP_DEFAULT_SENDER='TravelTech Safety <no-reply@traveltech.local>'
    )
    with app.app_context():
        contact = EmergencyContact.query.filter_by(is_primary=True).first()
        db.session.add(EmergencyContactVerification(
            contact_id=contact.id,
            verified_at=datetime.utcnow()
        ))
        db.session.commit()
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})

    response = client.post('/api/safety/sos/prepare', json={'incident_type': 'sos_manual'})
    assert response.status_code == 202
    action_id = response.get_json()['action']['id']
    dispatch_queued_action(client, app, action_id)
    status = client.get(f'/api/safety/actions/{action_id}').get_json()
    delivery = status['incident']
    assert delivery['email_sent'] is True
    assert delivery['email_delivery_status'] == 'live_smtp'
    assert delivery['email_recipient'] == 'emergency.assist@globalcare.com'
    assert len(smtp_instances) == 1
    assert smtp_instances[0].sent_messages[0]['From'] == 'smtp-user@example.com'


def test_sos_live_mode_without_credentials_reports_configuration_error(client, app):
    app.config.update(SMTP_TEST_MODE=False, SMTP_USERNAME='', SMTP_PASSWORD='')
    with app.app_context():
        contact = EmergencyContact.query.filter_by(is_primary=True).first()
        db.session.add(EmergencyContactVerification(
            contact_id=contact.id,
            verified_at=datetime.utcnow()
        ))
        db.session.commit()
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})

    response = client.post('/api/safety/sos/prepare', json={'incident_type': 'sos_manual'})
    action_id = response.get_json()['action']['id']
    dispatch_queued_action(client, app, action_id)
    delivery = client.get(f'/api/safety/actions/{action_id}').get_json()['incident']
    assert delivery['email_sent'] is False
    assert delivery['email_delivery_status'] == 'smtp_not_configured'
    with app.app_context():
        incident = EmergencyIncident.query.first()
        assert incident.email_delivery_status == 'smtp_not_configured'


def test_unverified_contact_cannot_receive_live_sos(client, app):
    app.config.update(
        SMTP_TEST_MODE=False,
        SMTP_USERNAME='smtp-user@example.com',
        SMTP_PASSWORD='test-password'
    )
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})
    response = client.post('/api/safety/sos/prepare', json={'incident_type': 'sos_manual'})
    action_id = response.get_json()['action']['id']
    dispatch_queued_action(client, app, action_id)
    delivery = client.get(f'/api/safety/actions/{action_id}').get_json()['incident']
    assert delivery['email_sent'] is False
    assert delivery['email_delivery_status'] == 'contact_not_verified'


def test_contact_verification_requires_explicit_confirmation(client, app, monkeypatch):
    verification_links = []
    monkeypatch.setattr(
        'app.routes.auth.EmailService.send_contact_verification',
        lambda contact, verification_url: verification_links.append(verification_url) or {'success': True}
    )
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})
    assert client.post('/profile/contact/verification').status_code == 302
    verify_path = urlparse(verification_links[0]).path
    assert client.get(verify_path).status_code == 200
    with app.app_context():
        contact = EmergencyContact.query.filter_by(is_primary=True).first()
        assert not contact.verification.is_verified

    assert client.post(verify_path).status_code == 302
    with app.app_context():
        contact = EmergencyContact.query.filter_by(is_primary=True).first()
        assert contact.verification.is_verified
        assert contact.verification.token_hash is None


def test_sos_smtp_authentication_failure_is_reported_as_not_sent(client, app, monkeypatch):
    class RejectingSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            raise smtplib.SMTPAuthenticationError(535, b'Authentication failed')

        def send_message(self, message):
            raise AssertionError('Do not send when SMTP authentication fails.')

    monkeypatch.setattr('app.services.email_service.smtplib.SMTP', RejectingSMTP)
    app.config.update(
        SMTP_TEST_MODE=False,
        SMTP_USERNAME='smtp-user@example.com',
        SMTP_PASSWORD='invalid-test-password',
        SMTP_DEFAULT_SENDER='smtp-user@example.com'
    )
    with app.app_context():
        contact = EmergencyContact.query.filter_by(is_primary=True).first()
        db.session.add(EmergencyContactVerification(
            contact_id=contact.id,
            verified_at=datetime.utcnow()
        ))
        db.session.commit()
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})

    response = client.post('/api/safety/sos/prepare', json={'incident_type': 'sos_manual'})
    action_id = response.get_json()['action']['id']
    dispatch_queued_action(client, app, action_id)
    delivery = client.get(f'/api/safety/actions/{action_id}').get_json()['incident']
    assert delivery['email_sent'] is False
    assert delivery['email_delivery_status'] == 'live_smtp_failed'
    with app.app_context():
        incident = EmergencyIncident.query.first()
        assert incident.email_sent is False
        assert incident.email_delivery_status == 'live_smtp_failed'


def test_checkin_timer_lifecycle(client, app):
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})

    start_res = client.post('/api/safety/checkin/start', json={
        'duration_minutes': 15,
        'notes': 'Exploring Faridabad heritage trail'
    })
    assert start_res.status_code == 200
    start_data = start_res.get_json()
    assert start_data['status'] == 'started'
    assert start_data['session']['status'] == 'active'

    status_res = client.get('/api/safety/checkin/status')
    assert status_res.status_code == 200
    assert status_res.get_json()['has_active'] is True

    confirm_res = client.post('/api/safety/checkin/confirm')
    assert confirm_res.status_code == 200
    assert confirm_res.get_json()['status'] == 'confirmed'

    final_status = client.get('/api/safety/checkin/status')
    assert final_status.get_json()['has_active'] is False
    with app.app_context():
        assert PendingSafetyAction.query.filter_by(status='cancelled').count() == 1


def test_expired_unconfirmed_checkin_dispatches_queued_alert(client, app):
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})
    start = client.post('/api/safety/checkin/start', json={'duration_minutes': 1}).get_json()
    action = client.get('/api/safety/checkin/status').get_json()['action']
    with app.app_context():
        pending = db.session.get(PendingSafetyAction, action['id'])
        from app.models.safety import CheckInSession
        checkin = db.session.get(CheckInSession, start['session']['id'])
        checkin.expires_at = datetime.utcnow() - timedelta(minutes=1)
        pending.dispatch_at = datetime.utcnow() - timedelta(seconds=1)
        db.session.commit()
    from app.services.safety_dispatch import dispatch_due_safety_actions
    dispatch_due_safety_actions(app)
    status = client.get(f'/api/safety/actions/{action["id"]}').get_json()
    assert status['action']['status'] == 'dispatched'
    assert status['incident']['incident_type'] == 'checkin_expired'


def test_rolling_10_minute_location_history_and_pruning(client):
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})

    with client.application.app_context():
        user = User.query.filter_by(username='safety_tester').first()
        old_sample = LocationSample(
            user_id=user.id,
            latitude=28.4000,
            longitude=77.3000,
            recorded_at=datetime.utcnow() - timedelta(minutes=16)
        )
        db.session.add(old_sample)
        db.session.commit()

    res = client.post('/api/safety/location-sample', json={
        'latitude': 28.4089,
        'longitude': 77.3178,
        'accuracy': 10
    })
    assert res.status_code == 200
    hist_res = client.get('/api/safety/location-history')
    assert hist_res.status_code == 200
    trail = hist_res.get_json()['trail']
    assert len(trail) == 1
    assert trail[0]['latitude'] == 28.4089


def test_location_samples_require_saved_consent(client, app):
    with app.app_context():
        profile = User.query.filter_by(username='safety_tester').first().profile
        profile.location_tracking_enabled = False
        db.session.commit()
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})
    response = client.post('/api/safety/location-sample', json={
        'latitude': 28.4, 'longitude': 77.3
    })
    assert response.status_code == 403


def test_saving_location_opt_out_deletes_existing_samples(client, app):
    with app.app_context():
        user = User.query.filter_by(username='safety_tester').first()
        db.session.add(LocationSample(
            user_id=user.id,
            latitude=28.4,
            longitude=77.3
        ))
        db.session.commit()
    client.post('/login', data={'identifier': 'safety_tester', 'password': 'pass123'})
    response = client.post('/profile', data={
        'full_name': 'Safety Tester',
        'proximity_radius': '50',
        'speech_rate': '1.0',
        'preferred_city_id': ''
    })
    assert response.status_code == 302
    with app.app_context():
        assert LocationSample.query.count() == 0
