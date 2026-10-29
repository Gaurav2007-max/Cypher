from flask import Blueprint, render_template, request, session, jsonify
from app.extensions import db
from app.models.city import City
from app.models.destination import Destination, Story, SavedDestination, SavedStory
from app.models.activity import Activity, CuisineItem
from app.models.transport import TransportOption
from app.models.safety import CheckInSession
from app.auth_utils import login_required, get_current_user

tourist_bp = Blueprint('tourist', __name__)

@tourist_bp.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    cities = City.query.filter_by(is_active=True).all()
    
    # Selected city: from query param, session, user profile, or default to Faridabad
    selected_city_id = request.args.get('city_id', type=int)
    if not selected_city_id:
        selected_city_id = session.get('selected_city_id')
    if not selected_city_id and user.profile and user.profile.preferred_city_id:
        selected_city_id = user.profile.preferred_city_id
    if not selected_city_id:
        faridabad = City.query.filter(City.name.ilike('%Faridabad%')).first()
        selected_city_id = faridabad.id if faridabad else (cities[0].id if cities else 1)

    current_city = City.query.get(selected_city_id) or (cities[0] if cities else None)
    if current_city:
        session['selected_city_id'] = current_city.id

    destinations = []
    destinations_dict_list = []
    hidden_gems = []
    activities = []
    cuisine_items = []
    transport_options = []

    if current_city:
        destinations = Destination.query.filter_by(city_id=current_city.id, is_active=True).all()
        destinations_dict_list = [d.to_dict() for d in destinations]
        hidden_gems = [d for d in destinations if d.is_hidden_gem]
        activities = Activity.query.filter_by(city_id=current_city.id, is_active=True).all()
        cuisine_items = CuisineItem.query.filter_by(city_id=current_city.id, is_active=True).all()
        transport_options = TransportOption.query.filter_by(city_id=current_city.id, is_active=True).all()

    # User saved destinations IDs
    saved_dest_ids = [s.destination_id for s in user.saved_destinations]
    saved_story_ids = [s.story_id for s in user.saved_stories]

    # Active check-in session if any
    active_checkin = CheckInSession.query.filter_by(user_id=user.id, status='active').order_by(CheckInSession.id.desc()).first()

    return render_template(
        'tourist/dashboard.html',
        user=user,
        cities=cities,
        current_city=current_city,
        destinations=destinations,
        destinations_json=destinations_dict_list,
        hidden_gems=hidden_gems,
        activities=activities,
        cuisine_items=cuisine_items,
        transport_options=transport_options,
        saved_dest_ids=saved_dest_ids,
        saved_story_ids=saved_story_ids,
        active_checkin=active_checkin
    )

@tourist_bp.route('/saved')
@login_required
def saved():
    user = get_current_user()
    saved_dests = [
        sd.destination for sd in user.saved_destinations
        if sd.destination and sd.destination.is_active
    ]
    saved_stories = [
        ss.story for ss in user.saved_stories
        if ss.story and ss.story.is_active and ss.story.destination and ss.story.destination.is_active
    ]
    return render_template('tourist/saved.html', user=user, saved_destinations=saved_dests, saved_stories=saved_stories)

@tourist_bp.route('/safety')
@login_required
def safety_center():
    user = get_current_user()
    primary_contact = user.emergency_contacts[0] if user.emergency_contacts else None
    active_checkin = CheckInSession.query.filter_by(user_id=user.id, status='active').order_by(CheckInSession.id.desc()).first()
    return render_template(
        'tourist/safety.html',
        user=user,
        contact=primary_contact,
        active_checkin=active_checkin,
        sensor_consent=bool(user.profile and user.profile.sensor_consent),
        emergency_consent=bool(user.profile and user.profile.emergency_consent)
    )
