from datetime import datetime
from app.extensions import db

class FeedbackReport(db.Model):
    __tablename__ = 'feedback_reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='SET NULL'), nullable=True, index=True)
    feedback_type = db.Column(db.String(50), nullable=False)  # 'inaccurate_info', 'outdated_price', 'wrong_hours', 'transport_issue', 'closed_location', 'safety_concern', 'wrong_story', 'general'
    title = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='pending', nullable=False)  # 'pending', 'reviewed', 'resolved', 'dismissed'
    admin_notes = db.Column(db.Text, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    reviewer = db.relationship('User', foreign_keys=[reviewed_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.author.username if self.author else 'Anonymous Traveler',
            'destination_id': self.destination_id,
            'destination_name': self.destination.name if self.destination else 'General / City-wide',
            'feedback_type': self.feedback_type,
            'title': self.title or self.feedback_type.replace('_', ' ').title(),
            'description': self.description,
            'status': self.status,
            'admin_notes': self.admin_notes,
            'reviewed_by': self.reviewer.username if self.reviewer else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

