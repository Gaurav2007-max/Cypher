from datetime import datetime, timedelta
import math
from flask import Blueprint, request, jsonify
from app.extensions import db, limiter
from app.models.safety import CheckInSession, EmergencyIncident, LocationSample, PendingSafetyAction
from app.models.city import City
from app.auth_utils import login_required, get_current_user
from app.services.audit_service import AuditService
from app.services.emergency_kit import EmergencyKitSourceError, build_emergency_kit
from sqlalchemy import update

api_safety_bp = Blueprint('api_safety', __name__, url_prefix='/api/safety')


@api_safety_bp.route('/emergency-kit/<int:city_id>', methods=['GET'])
@login_required
@limiter.limit('1 per minute')
def get_emergency_kit_data(city_id):
    city = City.query.filter_by(id=city_id, is_active=True).first_or_404()
    try:
        kit = build_emergency_kit(city)
    except EmergencyKitSourceError as error:
        return jsonify({'error': str(error)}), 502
    return jsonify(kit)


@api_safety_bp.route('/sos/prepare', methods=['POST'])
@login_required
@limiter.limit('5 per minute')
def prepare_sos():
    user = get_current_user()
    if not user.profile or not user.profile.emergency_consent:
        return jsonify({'error': 'Enable emergency alert consent in your profile before starting SOS.'}), 403

    data = request.get_json() or {}
    try:
        lat = float(data['latitude']) if data.get('latitude') is not None else None
        lon = float(data['longitude']) if data.get('longitude') is not None else None
        acc = float(data['accuracy']) if data.get('accuracy') is not None else None
    except (TypeError, ValueError):
        return jsonify({'error': 'Coordinates and accuracy must be numbers.'}), 400
    incident_type = data.get('incident_type', 'sos_manual')

    if incident_type not in {'sos_manual', 'fall_detected', 'checkin_expired'}:
        return jsonify({'error': 'Unsupported emergency incident type.'}), 400
    if (lat is None) != (lon is None):
        return jsonify({'error': 'Both latitude and longitude must be supplied together.'}), 400
    if lat is not None and not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({'error': 'Coordinates are outside the valid range.'}), 400
    if acc is not None and (not math.isfinite(acc) or acc < 0):
        return jsonify({'error': 'Location accuracy must be a non-negative number.'}), 400

    action = PendingSafetyAction(
        user_id=user.id,
        incident_type=incident_type,
        status='pending',
        dispatch_at=datetime.utcnow() + timedelta(seconds=30),
        latitude=lat,
        longitude=lon,
        location_accuracy=acc
    )
    db.session.add(action)
    db.session.commit()
    return jsonify({'status': 'pending', 'action': action.to_dict()}), 202


@api_safety_bp.route('/actions/<int:action_id>', methods=['GET'])
@login_required
def get_safety_action(action_id):
    user = get_current_user()
    action = PendingSafetyAction.query.filter_by(id=action_id, user_id=user.id).first_or_404()
    incident = db.session.get(EmergencyIncident, action.incident_id) if action.incident_id else None
    return jsonify({
        'action': action.to_dict(),
        'incident': incident.to_dict() if incident else None
    })


@api_safety_bp.route('/actions/<int:action_id>/location', methods=['PATCH'])
@login_required
def update_safety_action_location(action_id):
    user = get_current_user()
    action = PendingSafetyAction.query.filter_by(id=action_id, user_id=user.id).first_or_404()
    if action.status != 'pending' or action.dispatch_at <= datetime.utcnow():
        return jsonify({'error': 'The alert is already being dispatched.'}), 409
    data = request.get_json() or {}
    try:
        lat, lon = float(data['latitude']), float(data['longitude'])
        acc = float(data['accuracy']) if data.get('accuracy') is not None else None
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': 'Valid latitude and longitude are required.'}), 400
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({'error': 'Valid latitude and longitude are required.'}), 400
    if acc is not None and (not math.isfinite(acc) or acc < 0):
        return jsonify({'error': 'Location accuracy must be a non-negative number.'}), 400
    action.latitude = lat
    action.longitude = lon
    action.location_accuracy = acc
    db.session.commit()
    return jsonify({'status': 'updated'})


@api_safety_bp.route('/actions/<int:action_id>/cancel', methods=['POST'])
@login_required
def cancel_safety_action(action_id):
    user = get_current_user()
    action = PendingSafetyAction.query.filter_by(id=action_id, user_id=user.id).first_or_404()
    now = datetime.utcnow()
    if action.status != 'pending' or action.dispatch_at <= now:
        return jsonify({'error': 'The alert is already being dispatched and can no longer be cancelled.'}), 409
    cancelled = db.session.execute(
        update(PendingSafetyAction)
        .where(
            PendingSafetyAction.id == action.id,
            PendingSafetyAction.user_id == user.id,
            PendingSafetyAction.status == 'pending',
            PendingSafetyAction.dispatch_at > now
        )
        .values(status='cancelled')
    )
    if cancelled.rowcount != 1:
        db.session.rollback()
        return jsonify({'error': 'The alert is already being dispatched and can no longer be cancelled.'}), 409
    db.session.commit()
    return jsonify({'status': 'cancelled', 'message': 'SOS cancelled; no alert was sent.'})


@api_safety_bp.route('/sos', methods=['POST'])
@login_required
def reject_direct_sos():
    return jsonify({'error': 'Direct SOS dispatch is disabled. Start a pending SOS with /api/safety/sos/prepare.'}), 410


@api_safety_bp.route('/checkin/start', methods=['POST'])
@login_required
@limiter.limit('10 per minute')
def start_checkin():
    user = get_current_user()
    data = request.get_json() or {}
    try:
        duration_minutes = int(data.get('duration_minutes', 30))
    except (TypeError, ValueError):
        return jsonify({'error': 'Timer duration must be a whole number of minutes.'}), 400
    if not 1 <= duration_minutes <= 24 * 60:
        return jsonify({'error': 'Timer duration must be between 1 minute and 24 hours.'}), 400
    notes = str(data.get('notes', 'Routine safety check-in'))[:255]

    prev_sessions = CheckInSession.query.filter_by(user_id=user.id, status='active').all()
    if prev_sessions and PendingSafetyAction.query.filter(
        PendingSafetyAction.user_id == user.id,
        PendingSafetyAction.checkin_session_id.in_([item.id for item in prev_sessions]),
        PendingSafetyAction.status == 'dispatching'
    ).first():
        return jsonify({'error': 'The previous check-in alert is already being processed.'}), 409
    for previous in prev_sessions:
        previous.status = 'cancelled'
        PendingSafetyAction.query.filter_by(
            checkin_session_id=previous.id, status='pending'
        ).update({'status': 'cancelled'})

    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=duration_minutes)
    session_obj = CheckInSession(
        user_id=user.id,
        duration_minutes=duration_minutes,
        started_at=now,
        expires_at=expires_at,
        status='active',
        notes=notes
    )
    db.session.add(session_obj)
    db.session.flush()
    if user.profile and user.profile.emergency_consent:
        db.session.add(PendingSafetyAction(
            user_id=user.id,
            checkin_session_id=session_obj.id,
            incident_type='checkin_expired',
            status='pending',
            dispatch_at=expires_at + timedelta(seconds=45)
        ))
    db.session.commit()

    AuditService.log('checkin_timer_started', user_id=user.id, entity_type='checkin', entity_id=session_obj.id, details={'duration_minutes': duration_minutes})

    return jsonify({
        'status': 'started',
        'session': session_obj.to_dict(),
        'automatic_alert_enabled': bool(user.profile and user.profile.emergency_consent)
    })


@api_safety_bp.route('/checkin/help', methods=['POST'])
@login_required
@limiter.limit('5 per minute')
def request_checkin_help():
    user = get_current_user()
    if not user.profile or not user.profile.emergency_consent:
        return jsonify({'error': 'Emergency alert consent is disabled in your profile.'}), 403
    checkin = CheckInSession.query.filter_by(user_id=user.id, status='active').order_by(CheckInSession.id.desc()).first()
    if not checkin or checkin.expires_at > datetime.utcnow():
        return jsonify({'error': 'There is no expired active check-in to escalate.'}), 409
    action = PendingSafetyAction.query.filter_by(
        user_id=user.id, checkin_session_id=checkin.id, status='pending'
    ).first()
    if not action:
        return jsonify({'error': 'The check-in alert is already being processed.'}), 409
    dispatch_at = datetime.utcnow() + timedelta(seconds=30)
    queued = db.session.execute(
        update(PendingSafetyAction)
        .where(
            PendingSafetyAction.id == action.id,
            PendingSafetyAction.user_id == user.id,
            PendingSafetyAction.status == 'pending'
        )
        .values(dispatch_at=dispatch_at)
    )
    if queued.rowcount != 1:
        db.session.rollback()
        return jsonify({'error': 'The check-in alert is already being processed.'}), 409
    db.session.commit()
    db.session.refresh(action)
    return jsonify({'status': 'pending', 'action': action.to_dict()}), 202

@api_safety_bp.route('/checkin/confirm', methods=['POST'])
@login_required
def confirm_checkin():
    user = get_current_user()
    active_session = CheckInSession.query.filter_by(user_id=user.id, status='active').order_by(CheckInSession.id.desc()).first()

    if not active_session:
        return jsonify({'status': 'none', 'message': 'No active check-in timer found.'}), 404

    actions = PendingSafetyAction.query.filter(
        PendingSafetyAction.user_id == user.id,
        PendingSafetyAction.checkin_session_id == active_session.id,
        PendingSafetyAction.status.in_(['pending', 'dispatching', 'dispatched'])
    ).all()
    if any(action.status != 'pending' or action.dispatch_at <= datetime.utcnow() for action in actions):
        return jsonify({'error': 'The emergency alert is already being processed.'}), 409
    if actions:
        now = datetime.utcnow()
        action_ids = [action.id for action in actions]
        cancelled = db.session.execute(
            update(PendingSafetyAction)
            .where(
                PendingSafetyAction.id.in_(action_ids),
                PendingSafetyAction.user_id == user.id,
                PendingSafetyAction.status == 'pending',
                PendingSafetyAction.dispatch_at > now
            )
            .values(status='cancelled')
        )
        if cancelled.rowcount != len(action_ids):
            db.session.rollback()
            return jsonify({'error': 'The emergency alert is already being processed.'}), 409
    active_session.status = 'checked_in'
    db.session.commit()

    AuditService.log('checkin_confirmed_safe', user_id=user.id, entity_type='checkin', entity_id=active_session.id)
    return jsonify({
        'status': 'confirmed',
        'message': 'Glad to know you are safe! Check-in confirmed.'
    })

@api_safety_bp.route('/checkin/status', methods=['GET'])
@login_required
def get_checkin_status():
    user = get_current_user()
    active_session = CheckInSession.query.filter_by(user_id=user.id, status='active').order_by(CheckInSession.id.desc()).first()

    if not active_session:
        return jsonify({'has_active': False})

    pending_action = PendingSafetyAction.query.filter_by(
        user_id=user.id, checkin_session_id=active_session.id, status='pending'
    ).first()
    return jsonify({
        'has_active': True,
        'session': active_session.to_dict(),
        'action': pending_action.to_dict() if pending_action else None
    })

@api_safety_bp.route('/location-sample', methods=['POST'])
@login_required
@limiter.limit('60 per minute')
def post_location_sample():
    user = get_current_user()
    if not user.profile or not user.profile.location_tracking_enabled:
        return jsonify({'error': 'Location tracking consent is disabled.'}), 403
    data = request.get_json() or {}
    lat = data.get('latitude')
    lon = data.get('longitude')
    acc = data.get('accuracy')

    if lat is None or lon is None:
        return jsonify({'error': 'Latitude and longitude required'}), 400
    try:
        lat, lon = float(lat), float(lon)
        acc = float(acc) if acc is not None else None
    except (TypeError, ValueError):
        return jsonify({'error': 'Coordinates and accuracy must be numbers.'}), 400
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({'error': 'Coordinates are outside the valid range.'}), 400
    if acc is not None and (not math.isfinite(acc) or acc < 0):
        return jsonify({'error': 'Location accuracy must be a non-negative number.'}), 400

    sample = LocationSample(
        user_id=user.id,
        latitude=lat,
        longitude=lon,
        accuracy=acc,
        recorded_at=datetime.utcnow()
    )
    db.session.add(sample)
    db.session.commit()

    # Automatically prune old samples beyond configured retention window (10 minutes)
    LocationSample.prune_old_samples(retention_minutes=10)

    return jsonify({'status': 'recorded'})

@api_safety_bp.route('/location-history', methods=['GET'])
@login_required
def get_location_history():
    user = get_current_user()
    if not user.profile or not user.profile.location_tracking_enabled:
        return jsonify({'retention_minutes': 10, 'count': 0, 'trail': []})
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    samples = LocationSample.query.filter(
        LocationSample.user_id == user.id,
        LocationSample.recorded_at >= cutoff
    ).order_by(LocationSample.recorded_at.asc()).all()

    return jsonify({
        'retention_minutes': 10,
        'count': len(samples),
        'trail': [s.to_dict() for s in samples]
    })
