from datetime import datetime
from app.extensions import db

class TransportOption(db.Model):
    __tablename__ = 'transport_options'

    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id', ondelete='CASCADE'), nullable=False, index=True)
    mode = db.Column(db.String(50), nullable=False)  # 'metro', 'bus', 'auto_rickshaw', 'cab', 'walking', 'shared_auto'
    name_or_route = db.Column(db.String(150), nullable=False)
    operating_hours = db.Column(db.String(100), default='06:00 AM - 11:00 PM')
    fare_estimate = db.Column(db.String(100), default='₹20 - ₹50')
    frequency = db.Column(db.String(100), default='Every 10-15 minutes')
    sample_timings = db.Column(db.String(200), nullable=True)
    source_type = db.Column(db.String(30), default='sample')  # 'verified', 'estimated', 'sample'
    details = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'city_id': self.city_id,
            'mode': self.mode,
            'name_or_route': self.name_or_route,
            'operating_hours': self.operating_hours,
            'fare_estimate': self.fare_estimate,
            'frequency': self.frequency,
            'sample_timings': self.sample_timings,
            'source_type': self.source_type,
            'details': self.details,
            'image_url': self.image_url
        }
