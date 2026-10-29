from datetime import datetime
from app.extensions import db

class CrowdStatusRecord(db.Model):
    __tablename__ = 'crowd_status_records'

    id = db.Column(db.Integer, primary_key=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False)  # 'Normal', 'Moderate', 'Crowded', 'Overcrowded'
    previous_status = db.Column(db.String(30), nullable=True)
    duration_minutes = db.Column(db.Integer, default=120)
    explanation = db.Column(db.String(300), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    updater = db.relationship('User', foreign_keys=[updated_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'destination_id': self.destination_id,
            'destination_name': self.destination.name if self.destination else '',
            'status': self.status,
            'previous_status': self.previous_status,
            'duration_minutes': self.duration_minutes,
            'explanation': self.explanation,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'updated_by': self.updater.username if self.updater else 'System/Authority',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class CrowdSubscription(db.Model):
    __tablename__ = 'crowd_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_notified = db.Column(db.Boolean, default=False)
    notification_message = db.Column(db.String(255), nullable=True)

    destination = db.relationship('Destination')

    def to_dict(self):
        return {
            'id': self.id,
            'destination_id': self.destination_id,
            'destination_name': self.destination.name if self.destination else '',
            'requested_at': self.requested_at.isoformat(),
            'is_notified': self.is_notified,
            'notification_message': self.notification_message
        }

