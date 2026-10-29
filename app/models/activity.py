from datetime import datetime
from app.extensions import db

class Activity(db.Model):
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id', ondelete='CASCADE'), nullable=False, index=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='SET NULL'), nullable=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'adventure', 'heritage_walk', 'workshop', 'cultural_show', 'trek'
    description = db.Column(db.Text, nullable=False)
    price_range = db.Column(db.String(80), nullable=False, default='₹200 - ₹500')
    typical_duration = db.Column(db.String(80), nullable=False, default='2 hours')
    recommended_time = db.Column(db.String(80), default='Early morning or late afternoon')
    safety_precautions = db.Column(db.Text, nullable=True)
    price_source = db.Column(db.String(150), default='Sample data; verify with the local operator')
    last_verified_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    destination = db.relationship('Destination')

    def to_dict(self):
        return {
            'id': self.id,
            'city_id': self.city_id,
            'destination_id': self.destination_id,
            'destination_name': self.destination.name if self.destination else None,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'price_range': self.price_range,
            'typical_duration': self.typical_duration,
            'recommended_time': self.recommended_time,
            'safety_precautions': self.safety_precautions,
            'price_source': self.price_source,
            'last_verified_at': self.last_verified_at.strftime('%Y-%m-%d') if self.last_verified_at else None,
            'image_url': self.image_url
        }


class CuisineItem(db.Model):
    __tablename__ = 'cuisine_items'

    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    cultural_background = db.Column(db.Text, nullable=True)
    dietary_tags = db.Column(db.String(150), default='vegetarian')  # comma-separated: 'vegetarian,gluten-free,street-food'
    allergen_info = db.Column(db.String(200), default='Contains dairy; check with vendor')
    price_range = db.Column(db.String(80), default='₹80 - ₹200')
    famous_spots = db.Column(db.String(250), nullable=True)
    user_rating = db.Column(db.Float, nullable=True)
    verified_status = db.Column(db.String(30), default='sample')  # 'verified', 'sample', 'community'
    image_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'city_id': self.city_id,
            'name': self.name,
            'description': self.description,
            'cultural_background': self.cultural_background,
            'dietary_tags': [t.strip() for t in self.dietary_tags.split(',')] if self.dietary_tags else [],
            'allergen_info': self.allergen_info,
            'price_range': self.price_range,
            'famous_spots': self.famous_spots,
            'user_rating': self.user_rating,
            'verified_status': self.verified_status,
            'image_url': self.image_url
        }
