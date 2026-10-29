import math
from flask import Blueprint, request, jsonify, session
from app.extensions import db
from app.models.city import City
from app.models.destination import Destination, Story, SavedDestination, SavedStory
from app.models.crowd import CrowdSubscription
from app.auth_utils import login_required, get_current_user
from app.services.crowd_service import CrowdService, haversine_distance

api_dest_bp = Blueprint('api_destinations', __name__, url_prefix='/api')


@api_dest_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    user = get_current_user()
    notifications = CrowdSubscription.query.filter_by(
        user_id=user.id, is_notified=True
    ).order_by(CrowdSubscription.requested_at.desc()).limit(50).all()
    return jsonify([notification.to_dict() for notification in notifications])

@api_dest_bp.route('/cities', methods=['GET'])
def get_cities():
    cities = City.query.filter_by(is_active=True).all()
    return jsonify([c.to_dict() for c in cities])

@api_dest_bp.route('/destinations', methods=['GET'])
def get_destinations():
    CrowdService.check_and_expire_alerts()

    city_id = request.args.get('city_id', type=int)
    category = request.args.get('category')
    hidden_gems_only = request.args.get('hidden_gems') == 'true'
    search = request.args.get('q', '').strip()

    query = Destination.query.filter_by(is_active=True)
    if city_id:
        query = query.filter_by(city_id=city_id)
    if category:
        query = query.filter_by(category=category)
    if hidden_gems_only:
        query = query.filter_by(is_hidden_gem=True)
    if search:
        query = query.filter(Destination.name.ilike(f'%{search}%'))

    destinations = query.all()
    return jsonify([d.to_dict() for d in destinations])

@api_dest_bp.route('/destinations/<int:dest_id>', methods=['GET'])
def get_destination_detail(dest_id):
    CrowdService.check_and_expire_alerts()
    dest = Destination.query.filter_by(id=dest_id, is_active=True).first_or_404()
    return jsonify(dest.to_dict(include_stories=True))

@api_dest_bp.route('/destinations/<int:dest_id>/recommendations', methods=['GET'])
def get_recommendations(dest_id):
    """Returns smart alternative recommendations when a place is Crowded or Overcrowded."""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if (lat is None) != (lon is None):
        return jsonify({'error': 'Both latitude and longitude must be supplied together.'}), 400
    if lat is not None and (
        not math.isfinite(lat) or not math.isfinite(lon)
        or not -90 <= lat <= 90 or not -180 <= lon <= 180
    ):
        return jsonify({'error': 'Coordinates are outside the valid range.'}), 400
    recs = CrowdService.get_smart_recommendations(dest_id, tourist_lat=lat, tourist_lon=lon)
    return jsonify(recs)

@api_dest_bp.route('/destinations/<int:dest_id>/save', methods=['POST'])
@login_required
def toggle_save_destination(dest_id):
    user = get_current_user()
    dest = Destination.query.filter_by(id=dest_id, is_active=True).first_or_404()

    existing = SavedDestination.query.filter_by(user_id=user.id, destination_id=dest.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'saved': False, 'message': f"Removed '{dest.name}' from your saved places."})
    else:
        new_save = SavedDestination(user_id=user.id, destination_id=dest.id)
        db.session.add(new_save)
        db.session.commit()
        return jsonify({'saved': True, 'message': f"Added '{dest.name}' to your saved places!"})

@api_dest_bp.route('/stories/<int:story_id>/save', methods=['POST'])
@login_required
def toggle_save_story(story_id):
    user = get_current_user()
    story = Story.query.filter_by(id=story_id, is_active=True).first_or_404()

    existing = SavedStory.query.filter_by(user_id=user.id, story_id=story.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'saved': False, 'message': f"Story '{story.title}' removed from saved."})
    else:
        new_save = SavedStory(user_id=user.id, story_id=story.id)
        db.session.add(new_save)
        db.session.commit()
        return jsonify({'saved': True, 'message': f"Story '{story.title}' saved for offline reading!"})

@api_dest_bp.route('/destinations/<int:dest_id>/subscribe-crowd', methods=['POST'])
@login_required
def subscribe_crowd(dest_id):
    user = get_current_user()
    dest = Destination.query.filter_by(id=dest_id, is_active=True).first_or_404()

    existing = CrowdSubscription.query.filter_by(user_id=user.id, destination_id=dest.id, is_notified=False).first()
    if existing:
        return jsonify({'subscribed': True, 'message': 'You are already subscribed to crowd updates for this destination.'})

    sub = CrowdSubscription(user_id=user.id, destination_id=dest.id)
    db.session.add(sub)
    db.session.commit()
    return jsonify({
        'subscribed': True,
        'message': f"Subscribed! We will notify you as soon as crowd levels at {dest.name} return to Normal."
    })

@api_dest_bp.route('/stories/proximity', methods=['POST'])
@login_required
def check_proximity_story():
    """
    Checks user's current GPS location against destinations in their selected city.
    If tourist approaches a destination within proximity radius (default 50m, configurable down to 10m),
    returns the story payload with photo, audio text, and interesting facts.
    """
    data = request.get_json() or {}
    lat = data.get('latitude')
    lon = data.get('longitude')
    city_id = data.get('city_id') or session.get('selected_city_id')
    user = get_current_user()

    if lat is None or lon is None:
        return jsonify({'error': 'Coordinates required'}), 400

    radius_meters = user.profile.proximity_radius_meters if user.profile else 50
    radius_km = radius_meters / 1000.0

    query = Destination.query.filter_by(is_active=True)
    if city_id:
        query = query.filter_by(city_id=city_id)
    destinations = query.all()

    triggered = None
    min_dist_meters = 999999

    for dest in destinations:
        dist_km = haversine_distance(lat, lon, dest.latitude, dest.longitude)
        dist_meters = dist_km * 1000.0
        if dist_meters <= radius_meters:
            if dist_meters < min_dist_meters:
                min_dist_meters = dist_meters
                triggered = dest

    stories = [story for story in triggered.stories if story.is_active] if triggered else []
    if triggered and stories:
        story = stories[0]
        return jsonify({
            'in_proximity': True,
            'distance_meters': round(min_dist_meters, 1),
            'radius_meters': radius_meters,
            'destination': triggered.to_dict(include_stories=False),
            'story': story.to_dict()
        })

    return jsonify({
        'in_proximity': False,
        'closest_distance_meters': round(min_dist_meters, 1) if min_dist_meters < 999999 else None,
        'radius_meters': radius_meters
    })
