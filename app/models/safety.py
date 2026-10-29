from datetime import datetime, timedelta
import json
from app.extensions import db

class CheckInSession(db.Model):
    __tablename__ = 'check_in_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    duration_minutes = db.Column(db.Integer, default=30, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), default='active', nullable=False)  # 'active', 'checked_in', 'emergency_triggered', 'cancelled'
    notes = db.Column(db.String(255), nullable=True)

    @property
    def is_expired(self):
        return self.status == 'active' and datetime.utcnow() > self.expires_at

    @property
    def remaining_seconds(self):
        if self.status != 'active':
            return 0
        diff = (self.expires_at - datetime.utcnow()).total_seconds()
        return max(0, int(diff))

    def to_dict(self):
        return {
            'id': self.id,
            'duration_minutes': self.duration_minutes,
            'started_at': self.started_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'status': self.status,
            'is_expired': self.is_expired,
            'remaining_seconds': self.remaining_seconds,
            'notes': self.notes
        }


class PendingSafetyAction(db.Model):
    __tablename__ = 'pending_safety_actions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    checkin_session_id = db.Column(db.Integer, db.ForeignKey('check_in_sessions.id', ondelete='CASCADE'), nullable=True, index=True)
    incident_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(30), default='pending', nullable=False, index=True)
    dispatch_at = db.Column(db.DateTime, nullable=False, index=True)
    dispatch_error = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_accuracy = db.Column(db.Float, nullable=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('emergency_incidents.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'incident_type': self.incident_type,
            'status': self.status,
            'dispatch_at': f'{self.dispatch_at.isoformat()}Z',
            'error': self.dispatch_error,
            'incident_id': self.incident_id,
            'seconds_remaining': max(0, int((self.dispatch_at - datetime.utcnow()).total_seconds()))
        }


class EmergencyIncident(db.Model):
    __tablename__ = 'emergency_incidents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    incident_type = db.Column(db.String(50), nullable=False)  # 'sos_manual', 'fall_detected', 'checkin_expired'
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_accuracy = db.Column(db.Float, nullable=True)
    snapshot_trail_json = db.Column(db.Text, nullable=True)  # Snapshot of 10-minute location trail at time of incident
    status = db.Column(db.String(30), default='active', nullable=False)  # 'active', 'resolved', 'cancelled', 'false_alarm'
    
    email_sent = db.Column(db.Boolean, default=False)
    email_recipient = db.Column(db.String(120), nullable=True)
    email_delivery_status = db.Column(db.String(100), default='pending')  # 'delivered', 'test_mode_logged', 'failed'
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    @property
    def snapshot_trail(self):
        if self.snapshot_trail_json:
            try:
                return json.loads(self.snapshot_trail_json)
            except Exception:
                return []
        return []

    def to_dict(self):
        return {
            'id': self.id,
            'incident_type': self.incident_type,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location_accuracy': self.location_accuracy,
            'snapshot_trail': self.snapshot_trail,
            'status': self.status,
            'email_sent': self.email_sent,
            'email_recipient': self.email_recipient,
            'email_delivery_status': self.email_delivery_status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'map_link': f"https://www.google.com/maps?q={self.latitude},{self.longitude}" if self.latitude is not None and self.longitude is not None else None
        }


class LocationSample(db.Model):
    __tablename__ = 'location_samples'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    accuracy = db.Column(db.Float, nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    @classmethod
    def prune_old_samples(cls, user_id=None, retention_minutes=10):
        cutoff = datetime.utcnow() - timedelta(minutes=retention_minutes)
        query = cls.query.filter(cls.recorded_at < cutoff)
        if user_id is not None:
            query = query.filter(cls.user_id == user_id)
        query.delete(synchronize_session=False)
        db.session.commit()

    def to_dict(self):
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy': self.accuracy,
            'recorded_at': self.recorded_at.isoformat()
        }
