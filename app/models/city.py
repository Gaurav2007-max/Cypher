from datetime import datetime
from app.extensions import db

class City(db.Model):
    __tablename__ = 'cities'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    state = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), default='India', nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def display_image_url(self):
        if self.name.casefold() == 'faridabad':
            return 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Nahar_Singh_Palace%2C_Ballabhgarh.jpg/1920px-Nahar_Singh_Palace%2C_Ballabhgarh.jpg'
        return self.image_url

    # Relationships
    destinations = db.relationship('Destination', backref='city', cascade='all, delete-orphan')
    activities = db.relationship('Activity', backref='city', cascade='all, delete-orphan')
    cuisine_items = db.relationship('CuisineItem', backref='city', cascade='all, delete-orphan')
    transport_options = db.relationship('TransportOption', backref='city', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state,
            'country': self.country,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'image_url': self.display_image_url,
            'description': self.description,
            'destinations_count': len(self.destinations) if self.destinations else 0
        }
