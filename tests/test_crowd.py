from datetime import datetime, timedelta
import pytest
from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import User, City, Destination
from app.services.crowd_service import CrowdService

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()

        city = City(name='Faridabad', state='Haryana', country='India', latitude=28.4089, longitude=77.3178)
        db.session.add(city)
        db.session.flush()

        auth = User(username='auth_user', email='auth@test.local', role='authority', authority_approved=True)
        auth.set_password('pass123')

        tourist = User(username='tourist_user', email='tourist@test.local', role='tourist')
        tourist.set_password('pass123')

        d1 = Destination(
            city_id=city.id,
            name='Surajkund Reservoir',
            description='Ancient amphitheater',
            latitude=28.4870,
            longitude=77.2831,
            crowd_status='Overcrowded',
            crowd_expires_at=datetime.utcnow() + timedelta(hours=2)
        )

        d2 = Destination(
            city_id=city.id,
            name='Raja Nahar Singh Palace',
            description='Royal Ballabhgarh fort',
            latitude=28.3414,
            longitude=77.3228,
            crowd_status='Normal',
            is_hidden_gem=True
        )

        d3 = Destination(
            city_id=city.id,
            name='Badkhal Lake',
            description='Scenic ridge lake',
            latitude=28.4180,
            longitude=77.2796,
            crowd_status='Overcrowded'  # Congested candidate
        )

        db.session.add_all([auth, tourist, d1, d2, d3])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_authorized_crowd_status_update(client):
    client.post('/login', data={'identifier': 'auth_user', 'password': 'pass123'})

    with client.application.app_context():
        dest = Destination.query.filter_by(name='Raja Nahar Singh Palace').first()
        dest_id = dest.id

    res = client.post('/authority/update-crowd', data={
        'destination_id': dest_id,
        'status': 'Moderate',
        'duration_minutes': 60,
        'explanation': 'Visiting school group present'
    }, follow_redirects=True)
    assert res.status_code == 200

    with client.application.app_context():
        dest = Destination.query.get(dest_id)
        assert dest.crowd_status == 'Moderate'
        assert 'school group' in dest.crowd_explanation

def test_tourist_cannot_change_crowd_status(client):
    client.post('/login', data={'identifier': 'tourist_user', 'password': 'pass123'})

    with client.application.app_context():
        dest = Destination.query.filter_by(name='Raja Nahar Singh Palace').first()
        dest_id = dest.id

    # Tourist attempts to POST to authority update endpoint
    res = client.post('/authority/update-crowd', data={
        'destination_id': dest_id,
        'status': 'Overcrowded',
        'duration_minutes': 120
    })
    # Must be 403 Forbidden!
    assert res.status_code == 403

def test_crowd_alert_auto_expiry(client):
    with client.application.app_context():
        dest = Destination.query.filter_by(name='Surajkund Reservoir').first()
        # Set expiry in the past
        dest.crowd_expires_at = datetime.utcnow() - timedelta(minutes=10)
        db.session.commit()

        # effective_crowd_status property should automatically report Normal
        assert dest.effective_crowd_status == 'Normal'

        # CrowdService check_and_expire_alerts should commit the change
        CrowdService.check_and_expire_alerts()
        rechecked = Destination.query.get(dest.id)
        assert rechecked.crowd_status == 'Normal'

def test_smart_alternative_recommendations(client):
    with client.application.app_context():
        surajkund = Destination.query.filter_by(name='Surajkund Reservoir').first()
        recs = CrowdService.get_smart_recommendations(surajkund.id)

        assert len(recs) > 0
        top = recs[0]
        # Should recommend Raja Nahar Singh Palace (which is Normal)
        assert top['destination']['name'] == 'Raja Nahar Singh Palace'
        assert top['crowd_status'] == 'Normal'
        # Crucial requirement: Should NOT recommend Badkhal Lake because it is Overcrowded!
        rec_names = [r['destination']['name'] for r in recs]
        assert 'Badkhal Lake' not in rec_names
        # Check computed explanation
        assert 'is currently overcrowded' in top['explanation'].lower()
        assert 'minutes away' in top['explanation'] or 'km' in top['explanation']

def test_crowd_subscription(client):
    client.post('/login', data={'identifier': 'tourist_user', 'password': 'pass123'})

    with client.application.app_context():
        surajkund = Destination.query.filter_by(name='Surajkund Reservoir').first()
        dest_id = surajkund.id

    res = client.post(f'/api/destinations/{dest_id}/subscribe-crowd')
    assert res.status_code == 200
    data = res.get_json()
    assert data['subscribed'] is True

