from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='tourist')  # 'tourist', 'authority', 'admin'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    authority_approved = db.Column(db.Boolean, default=False, nullable=False)  # Admin approves authorities
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    emergency_contacts = db.relationship('EmergencyContact', backref='user', cascade='all, delete-orphan')
    saved_destinations = db.relationship('SavedDestination', backref='user', cascade='all, delete-orphan')
    saved_stories = db.relationship('SavedStory', backref='user', cascade='all, delete-orphan')
    feedback_reports = db.relationship('FeedbackReport', foreign_keys='FeedbackReport.user_id', backref='author', cascade='all, delete-orphan')
    check_in_sessions = db.relationship('CheckInSession', backref='user', cascade='all, delete-orphan')
    emergency_incidents = db.relationship('EmergencyIncident', backref='user', cascade='all, delete-orphan')
    location_samples = db.relationship('LocationSample', backref='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_authority(self):
        return self.role == 'authority' and self.authority_approved

    @property
    def is_tourist(self):
        return self.role == 'tourist'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'authority_approved': self.authority_approved,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserProfile(db.Model):
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    full_name = db.Column(db.String(120), nullable=True)
    nationality = db.Column(db.String(80), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    preferred_city_id = db.Column(db.Integer, db.ForeignKey('cities.id', ondelete='SET NULL'), nullable=True)
    
    # Consents
    emergency_consent = db.Column(db.Boolean, default=False, nullable=False)
    sensor_consent = db.Column(db.Boolean, default=False, nullable=False)
    location_tracking_enabled = db.Column(db.Boolean, default=False, nullable=False)
    
    # Audio & proximity preferences
    audio_speech_rate = db.Column(db.Float, default=1.0, nullable=False)
    proximity_radius_meters = db.Column(db.Integer, default=50, nullable=False)  # Configurable (e.g. 10m-200m)
    auto_story_notifications = db.Column(db.Boolean, default=True, nullable=False)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'full_name': self.full_name or '',
            'nationality': self.nationality or '',
            'phone': self.phone or '',
            'preferred_city_id': self.preferred_city_id,
            'emergency_consent': self.emergency_consent,
            'sensor_consent': self.sensor_consent,
            'location_tracking_enabled': self.location_tracking_enabled,
            'audio_speech_rate': self.audio_speech_rate,
            'proximity_radius_meters': self.proximity_radius_meters,
            'auto_story_notifications': self.auto_story_notifications
        }


class EmergencyContact(db.Model):
    __tablename__ = 'emergency_contacts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    relationship = db.Column(db.String(50), nullable=True)  # 'family', 'friend', 'agency', 'consulate'
    is_agency = db.Column(db.Boolean, default=False)  # For international tourists connecting their agency
    is_primary = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verification = db.relationship('EmergencyContactVerification', backref='contact', uselist=False, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone or '',
            'relationship': self.relationship or '',
            'is_agency': self.is_agency,
            'is_primary': self.is_primary
        }


class EmergencyContactVerification(db.Model):
    __tablename__ = 'emergency_contact_verifications'

    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('emergency_contacts.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    token_hash = db.Column(db.String(64), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)

    @property
    def is_verified(self):
        return self.verified_at is not None
