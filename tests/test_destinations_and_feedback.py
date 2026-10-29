import pytest
from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import (
    CrowdSubscription,
    User,
    City,
    Destination,
    Story,
    FeedbackReport,
)

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()

        c_fbd = City(name='Faridabad', state='Haryana', country='India', latitude=28.4089, longitude=77.3178)
        c_agra = City(name='Agra', state='Uttar Pradesh', country='India', latitude=27.1767, longitude=78.0081)
        db.session.add_all([c_fbd, c_agra])
        db.session.flush()

        tourist = User(username='travel_user', email='travel@test.local', role='tourist')
        tourist.set_password('pass123')

        admin = User(username='admin_user', email='admin@test.local', role='admin', authority_approved=True)
        admin.set_password('pass123')

        d1 = Destination(
            city_id=c_fbd.id,
            name='Surajkund',
            category='heritage',
            description='Sun reservoir',
            latitude=28.4870,
            longitude=77.2831
        )
        db.session.add_all([tourist, admin, d1])
        db.session.flush()

        s1 = Story(
            destination_id=d1.id,
            title='Tomar Sun Temple Story',
            content='Built in the 10th century CE.'
        )
        db.session.add(s1)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_city_destinations_filtering(client):
    # Query cities
    res_cities = client.get('/api/cities')
    assert res_cities.status_code == 200
    cities = res_cities.get_json()
    assert len(cities) == 2

    # Query Faridabad destinations
    fbd_id = cities[0]['id']
    res_dest = client.get(f'/api/destinations?city_id={fbd_id}')
    assert res_dest.status_code == 200
    destinations = res_dest.get_json()
    assert len(destinations) >= 1
    assert destinations[0]['name'] == 'Surajkund'

def test_proximity_story_trigger(client):
    client.post('/login', data={'identifier': 'travel_user', 'password': 'pass123'})

    # Tourist within 20 metres of Surajkund (28.4870, 77.2831)
    res = client.post('/api/stories/proximity', json={
        'latitude': 28.4871,
        'longitude': 77.2831
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data['in_proximity'] is True
    assert data['story']['title'] == 'Tomar Sun Temple Story'

def test_feedback_submission_and_resolution(client):
    # 1. Tourist submits feedback
    client.post('/login', data={'identifier': 'travel_user', 'password': 'pass123'})

    with client.application.app_context():
        d = Destination.query.filter_by(name='Surajkund').first()
        dest_id = d.id

    sub_res = client.post('/api/feedback/submit', json={
        'destination_id': dest_id,
        'feedback_type': 'outdated_price',
        'title': 'Entry ticket updated',
        'description': 'Ticket counter now charges ₹30 instead of ₹20.'
    })
    assert sub_res.status_code == 200
    report_id = sub_res.get_json()['report_id']

    # Verify persistence
    with client.application.app_context():
        report = FeedbackReport.query.get(report_id)
        assert report is not None
        assert report.status == 'pending'
        assert report.feedback_type == 'outdated_price'

    # 2. Logout tourist, login as admin to resolve feedback
    client.post('/logout')
    client.post('/login', data={'identifier': 'admin_user', 'password': 'pass123'})
    res_resolve = client.post(f'/admin/resolve-feedback/{report_id}', data={
        'status': 'resolved',
        'admin_notes': 'Verified with counter staff and updated.'
    }, follow_redirects=True)
    assert res_resolve.status_code == 200

    with client.application.app_context():
        rechecked = FeedbackReport.query.get(report_id)
        assert rechecked.status == 'resolved'
        assert 'counter staff' in rechecked.admin_notes


def test_feedback_rejects_invalid_destination_and_type(client):
    client.post('/login', data={'identifier': 'travel_user', 'password': 'pass123'})
    unknown_destination = client.post('/api/feedback/submit', json={
        'destination_id': 'not-an-id',
        'description': 'Report'
    })
    assert unknown_destination.status_code == 400
    unknown_type = client.post('/api/feedback/submit', json={
        'feedback_type': 'unsupported',
        'description': 'Report'
    })
    assert unknown_type.status_code == 400

def test_route_calculation_endpoint(client):
    res = client.post('/api/routes/calculate', json={
        'origin_lat': 28.4089,
        'origin_lon': 77.3178,
        'dest_lat': 28.4870,
        'dest_lon': 77.2831,
        'mode': 'driving'
    })
    assert res.status_code == 200
    data = res.get_json()
    assert 'distance_km' in data
    assert 'modes' in data
    assert 'walking' in data['modes']
    assert 'driving' in data['modes']
    assert 'transit' in data['modes']


def test_inactive_stories_are_hidden_from_public_destination_payload(client, app):
    with app.app_context():
        story = Story.query.first()
        story.is_active = False
        destination_id = story.destination_id
        story_id = story.id
        db.session.commit()

    destination = client.get(f'/api/destinations/{destination_id}').get_json()
    assert destination['stories'] == []
    client.post('/login', data={'identifier': 'travel_user', 'password': 'pass123'})
    assert client.post(f'/api/stories/{story_id}/save').status_code == 404


def test_feedback_list_is_owner_scoped_for_tourists(client, app):
    with app.app_context():
        user = User.query.filter_by(username='travel_user').first()
        other = User(username='other_user', email='other@test.local', role='tourist')
        other.set_password('pass123')
        db.session.add(other)
        db.session.flush()
        db.session.add_all([
            FeedbackReport(user_id=user.id, feedback_type='general', description='My report'),
            FeedbackReport(user_id=other.id, feedback_type='general', description='Private report')
        ])
        db.session.commit()

    client.post('/login', data={'identifier': 'travel_user', 'password': 'pass123'})
    reports = client.get('/api/feedback/list').get_json()
    assert [report['description'] for report in reports] == ['My report']


def test_crowd_notifications_are_owner_scoped(client, app):
    with app.app_context():
        destination = Destination.query.first()
        user = User.query.filter_by(username='travel_user').first()
        other = User(username='other_subscriber', email='other_sub@test.local', role='tourist')
        other.set_password('pass123')
        db.session.add(other)
        db.session.flush()
        db.session.add_all([
            CrowdSubscription(
                user_id=user.id,
                destination_id=destination.id,
                is_notified=True,
                notification_message='Your update'
            ),
            CrowdSubscription(
                user_id=other.id,
                destination_id=destination.id,
                is_notified=True,
                notification_message='Private update'
            )
        ])
        db.session.commit()

    client.post('/login', data={'identifier': 'travel_user', 'password': 'pass123'})
    notifications = client.get('/api/notifications').get_json()
    assert len(notifications) == 1
    assert notifications[0]['notification_message'] == 'Your update'


def test_transit_route_is_not_fabricated_as_live(client):
    response = client.post('/api/routes/calculate', json={
        'origin_lat': 28.4,
        'origin_lon': 77.3,
        'dest_lat': 28.5,
        'dest_lon': 77.4,
        'mode': 'transit'
    })
    data = response.get_json()
    assert response.status_code == 200
    assert data['is_live_routing'] is False
    assert data['modes']['transit']['available'] is False
    assert 'provider is configured' in data['modes']['transit']['description']


def test_admin_can_create_and_deactivate_cuisine_content(client, app):
    client.post('/login', data={'identifier': 'admin_user', 'password': 'pass123'})
    with app.app_context():
        city_id = City.query.filter_by(name='Faridabad').first().id

    response = client.post('/admin/content/cuisine', data={
        'city_id': str(city_id),
        'name': 'Test dish',
        'description': 'A sample local dish.',
        'cultural_background': 'Sample background.',
        'dietary_tags': 'vegetarian',
        'allergen_info': 'Not verified; ask the vendor',
        'price_range': 'Unverified',
        'famous_spots': '',
        'image_url': '',
        'verified_status': 'sample',
        'user_rating': ''
    })
    assert response.status_code == 302
    with app.app_context():
        from app.models import CuisineItem
        item = CuisineItem.query.filter_by(name='Test dish').first()
        item_id = item.id
        assert item.verified_status == 'sample'

    response = client.post(f'/admin/content/cuisine/{item_id}/toggle')
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(CuisineItem, item_id).is_active is False


def test_admin_content_pages_render_and_create_each_content_type(client, app):
    client.post('/login', data={'identifier': 'admin_user', 'password': 'pass123'})
    with app.app_context():
        city_id = City.query.filter_by(name='Faridabad').first().id
        destination_id = Destination.query.first().id

    for kind in ('destinations', 'stories', 'activities', 'cuisine'):
        assert client.get(f'/admin/content/{kind}').status_code == 200

    destination_response = client.post('/admin/content/destinations', data={
        'city_id': str(city_id),
        'name': 'Managed destination',
        'category': 'heritage',
        'description': 'Admin-managed test destination.',
        'latitude': '28.4',
        'longitude': '77.3',
        'source_attribution': 'Unverified sample data'
    })
    assert destination_response.status_code == 302
    story_response = client.post('/admin/content/stories', data={
        'destination_id': str(destination_id),
        'title': 'Managed story',
        'content': 'Admin-managed test story.'
    })
    assert story_response.status_code == 302
    activity_response = client.post('/admin/content/activities', data={
        'city_id': str(city_id),
        'name': 'Managed activity',
        'category': 'experience',
        'description': 'Admin-managed test activity.',
        'price_range': 'Unverified',
        'price_source': 'Sample data; verify locally'
    })
    assert activity_response.status_code == 302


def test_admin_dashboard_links_content_pages(client):
    client.post('/login', data={'identifier': 'admin_user', 'password': 'pass123'})
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'Manage Destinations' in response.data or b'>Destinations</a>' in response.data
