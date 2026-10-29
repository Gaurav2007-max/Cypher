import json
import os
import threading
import time
from datetime import datetime, timedelta

from sqlalchemy import update

from app.extensions import db
from app.models.safety import CheckInSession, EmergencyIncident, LocationSample, PendingSafetyAction
from app.models.user import EmergencyContact, User
from app.services.audit_service import AuditService
from app.services.email_service import EmailService


_scheduler_lock = threading.Lock()
_started_apps = set()


def _process_claimed_action(action_id):
    action = db.session.get(PendingSafetyAction, action_id)
    if action.checkin_session_id:
        checkin = db.session.get(CheckInSession, action.checkin_session_id)
        if not checkin or checkin.status != 'active':
            action.status = 'cancelled'
            db.session.commit()
            return
    user = db.session.get(User, action.user_id)
    if not user or not user.profile or not user.profile.emergency_consent:
        action.status = 'cancelled'
        db.session.commit()
        return

    contact = EmergencyContact.query.filter_by(user_id=user.id, is_primary=True).first()
    if not contact and user.emergency_contacts:
        contact = user.emergency_contacts[0]

    cutoff = datetime.utcnow() - timedelta(minutes=10)
    samples = LocationSample.query.filter(
        LocationSample.user_id == user.id,
        LocationSample.recorded_at >= cutoff
    ).order_by(LocationSample.recorded_at.asc()).all()
    trail = [sample.to_dict() for sample in samples]

    latitude = action.latitude
    longitude = action.longitude
    accuracy = action.location_accuracy
    if latitude is None and samples:
        latest = samples[-1]
        latitude, longitude, accuracy = latest.latitude, latest.longitude, latest.accuracy

    delivery = EmailService.send_emergency_alert(
        user=user,
        emergency_contact=contact,
        incident_type=action.incident_type,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        location_trail=trail
    )
    incident = EmergencyIncident(
        user_id=user.id,
        incident_type=action.incident_type,
        latitude=latitude,
        longitude=longitude,
        location_accuracy=accuracy,
        snapshot_trail_json=json.dumps(trail),
        status='active',
        email_sent=delivery.get('success', False),
        email_recipient=contact.email if contact else None,
        email_delivery_status=delivery.get('mode', 'failed'),
        notes=f"Delivery detail: {delivery.get('error') or delivery.get('mode')}"
    )
    db.session.add(incident)
    db.session.flush()
    action.status = 'dispatched'
    action.dispatch_error = None
    action.incident_id = incident.id
    db.session.commit()
    AuditService.log(
        action='emergency_sos_triggered',
        user_id=user.id,
        entity_type='emergency_incident',
        entity_id=incident.id,
        details={'incident_type': action.incident_type, 'email_mode': delivery.get('mode')}
    )

    if action.checkin_session_id:
        checkin = db.session.get(CheckInSession, action.checkin_session_id)
        if checkin and checkin.status == 'active':
            checkin.status = 'emergency_triggered'
            db.session.commit()


def dispatch_due_safety_actions(app):
    with app.app_context():
        due_ids = [
            row.id for row in PendingSafetyAction.query.filter(
                PendingSafetyAction.status == 'pending',
                PendingSafetyAction.dispatch_at <= datetime.utcnow()
            ).order_by(PendingSafetyAction.id.asc()).limit(25).all()
        ]

        for action_id in due_ids:
            now = datetime.utcnow()
            claimed = db.session.execute(
                update(PendingSafetyAction)
                .where(
                    PendingSafetyAction.id == action_id,
                    PendingSafetyAction.status == 'pending',
                    PendingSafetyAction.dispatch_at <= now
                )
                .values(status='dispatching')
            )
            db.session.commit()
            if claimed.rowcount != 1:
                continue
            try:
                _process_claimed_action(action_id)
            except Exception:
                db.session.rollback()
                app.logger.exception('Failed while dispatching pending safety action %s.', action_id)
                failed = db.session.execute(
                    update(PendingSafetyAction)
                    .where(
                        PendingSafetyAction.id == action_id,
                        PendingSafetyAction.status == 'dispatching'
                    )
                    .values(
                        status='failed',
                        dispatch_error='Alert processing failed. Contact emergency services directly.'
                    )
                )
                if failed.rowcount:
                    db.session.commit()


def _scheduler_loop(app):
    next_prune = time.monotonic() + 30
    while True:
        try:
            dispatch_due_safety_actions(app)
            if time.monotonic() >= next_prune:
                with app.app_context():
                    LocationSample.prune_old_samples(retention_minutes=10)
                next_prune = time.monotonic() + 30
        except Exception:
            app.logger.exception('Safety action scheduler failed while processing due actions.')
        time.sleep(1)


def start_safety_scheduler(app):
    if app.testing:
        return
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return

    app_key = id(app)
    with _scheduler_lock:
        if app_key in _started_apps:
            return
        _started_apps.add(app_key)

    thread = threading.Thread(target=_scheduler_loop, args=(app,), name='traveltech-safety-dispatch', daemon=True)
    thread.start()
