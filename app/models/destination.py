from datetime import datetime
import json
from app.extensions import db

class Destination(db.Model):
    __tablename__ = 'destinations'

    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, default='heritage')  # 'heritage', 'nature', 'cultural', 'spiritual', 'monument', 'lake'
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    gallery_json = db.Column(db.Text, nullable=True)  # JSON list of image URLs
    
    historical_significance = db.Column(db.Text, nullable=True)
    local_stories = db.Column(db.Text, nullable=True)
    opening_hours = db.Column(db.String(150), nullable=True, default='09:00 AM - 06:00 PM')
    accessibility_info = db.Column(db.String(250), nullable=True, default='Wheelchair accessible at main gate')
    is_hidden_gem = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # Verification & Source Attribution
    source_attribution = db.Column(db.String(200), default='Haryana Tourism & Archeological Survey of India')
    last_verified_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Crowd status managed by authorities
    crowd_status = db.Column(db.String(30), default='Normal', nullable=False)  # 'Normal', 'Moderate', 'Crowded', 'Overcrowded'
    crowd_updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    crowd_expires_at = db.Column(db.DateTime, nullable=True)
    crowd_explanation = db.Column(db.String(300), nullable=True)
    crowd_updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    stories = db.relationship('Story', backref='destination', cascade='all, delete-orphan')
    crowd_records = db.relationship('CrowdStatusRecord', backref='destination', cascade='all, delete-orphan')
    saved_by = db.relationship('SavedDestination', backref='destination', cascade='all, delete-orphan')
    feedback_reports = db.relationship('FeedbackReport', backref='destination', cascade='all, delete-orphan')

    @property
    def effective_crowd_status(self):
        """Checks expiry of crowd alert. If expired, automatically returns Normal."""
        if self.crowd_expires_at and datetime.utcnow() > self.crowd_expires_at:
            return 'Normal'
        return self.crowd_status or 'Normal'

    @property
    def is_crowded_or_more(self):
        return self.effective_crowd_status in ('Crowded', 'Overcrowded')

    @property
    def gallery(self):
        if self.gallery_json:
            try:
                return json.loads(self.gallery_json)
            except Exception:
                return []
        return [self.image_url] if self.image_url else []

    @property
    def display_image_url(self):
        name = self.name.casefold()
        if name.startswith('asola bhatti sanctuary'):
            return 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1000&q=85'
        if name.startswith('badkhal lake'):
            return 'https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=1000&q=85'
        if 'iskcon faridabad' in name:
            return 'https://upload.wikimedia.org/wikipedia/commons/d/d2/Iskcon_Delhi_Temple.jpg'
        return self.image_url

    def to_dict(self, include_stories=True):
        status = self.effective_crowd_status
        return {
            'id': self.id,
            'city_id': self.city_id,
            'city_name': self.city.name if self.city else '',
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'image_url': self.display_image_url,
            'gallery': self.gallery,
            'historical_significance': self.historical_significance,
            'local_stories': self.local_stories,
            'opening_hours': self.opening_hours,
            'accessibility_info': self.accessibility_info,
            'is_hidden_gem': self.is_hidden_gem,
            'source_attribution': self.source_attribution,
            'last_verified_at': self.last_verified_at.strftime('%Y-%m-%d') if self.last_verified_at else None,
            'crowd_status': status,
            'crowd_explanation': self.crowd_explanation if status != 'Normal' else None,
            'crowd_expires_at': self.crowd_expires_at.isoformat() if self.crowd_expires_at else None,
            'stories': [s.to_dict() for s in self.stories if s.is_active] if include_stories else []
        }


class Story(db.Model):
    __tablename__ = 'stories'

    id = db.Column(db.Integer, primary_key=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    audio_text = db.Column(db.Text, nullable=True)  # Clean speech-optimized text
    audio_duration_seconds = db.Column(db.Integer, default=60)
    language = db.Column(db.String(10), default='en')
    fun_facts = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    saved_by = db.relationship('SavedStory', backref='story', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'destination_id': self.destination_id,
            'destination_name': self.destination.name if self.destination else '',
            'title': self.title,
            'content': self.content,
            'audio_text': self.audio_text or self.content,
            'audio_duration_seconds': self.audio_duration_seconds,
            'language': self.language,
            'fun_facts': self.fun_facts,
            'image_url': self.image_url or (self.destination.image_url if self.destination else '')
        }


class SavedDestination(db.Model):
    __tablename__ = 'saved_destinations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'destination_id', name='uq_user_destination'),)


class SavedStory(db.Model):
    __tablename__ = 'saved_stories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id', ondelete='CASCADE'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'story_id', name='uq_user_story'),)
