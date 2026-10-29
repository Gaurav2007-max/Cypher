import math
from datetime import datetime
from app.extensions import db
from app.models.destination import Destination
from app.models.crowd import CrowdStatusRecord, CrowdSubscription

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth in kilometers."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class CrowdService:
    @staticmethod
    def check_and_expire_alerts():
        """Auto-expires alerts whose validity period has elapsed."""
        now = datetime.utcnow()
        expired_destinations = Destination.query.filter(
            Destination.crowd_expires_at.isnot(None),
            Destination.crowd_expires_at <= now,
            Destination.crowd_status.in_(['Crowded', 'Overcrowded'])
        ).all()

        for dest in expired_destinations:
            prev = dest.crowd_status
            dest.crowd_status = 'Normal'
            dest.crowd_explanation = 'Alert expired automatically.'
            dest.crowd_expires_at = None
            dest.crowd_updated_at = now
            
            # Record audit record
            record = CrowdStatusRecord(
                destination_id=dest.id,
                status='Normal',
                previous_status=prev,
                duration_minutes=0,
                explanation='System auto-expired alert after validity duration',
                expires_at=None,
                updated_by_id=None
            )
            db.session.add(record)
            
            # Notify subscriptions
            CrowdService.notify_subscribers(dest.id, f"{dest.name} crowd status has normalized back to Normal.")

        if expired_destinations:
            db.session.commit()

    @staticmethod
    def notify_subscribers(destination_id, message):
        """Notifies tourists waiting for a destination to clear up."""
        subs = CrowdSubscription.query.filter_by(destination_id=destination_id, is_notified=False).all()
        for sub in subs:
            sub.is_notified = True
            sub.notification_message = message
        db.session.commit()

    @staticmethod
    def get_smart_recommendations(destination_id, tourist_lat=None, tourist_lon=None, limit=3):
        """
        Calculates intelligent hidden-gem and cultural alternatives when a destination is Crowded or Overcrowded.
        Filters out destinations that are themselves Overcrowded or closed.
        Uses distance, travel time, crowd status, and cultural factors to rank recommendations.
        """
        CrowdService.check_and_expire_alerts()

        target_dest = Destination.query.filter_by(id=destination_id, is_active=True).first()
        if not target_dest:
            return []

        # Find candidates in the same city (or active destinations)
        candidates = Destination.query.filter(
            Destination.city_id == target_dest.city_id,
            Destination.id != target_dest.id,
            Destination.is_active == True,
            Destination.crowd_status.in_(['Normal', 'Moderate'])
        ).all()

        results = []
        base_lat = tourist_lat if tourist_lat is not None else target_dest.latitude
        base_lon = tourist_lon if tourist_lon is not None else target_dest.longitude

        for cand in candidates:
            listed_hours = (cand.opening_hours or '').strip().casefold()
            if any(marker in listed_hours for marker in ('closed', 'not operating', 'unavailable')):
                continue
            dist_km = haversine_distance(base_lat, base_lon, cand.latitude, cand.longitude)
            # Estimate travel time:
            # If under 1.5 km, show walking time (~12 min per km)
            # If over 1.5 km, show urban driving/transit time (~25 km/h -> ~2.4 min per km + 3 min buffer)
            if dist_km <= 1.5:
                est_minutes = max(3, round(dist_km * 13))
                travel_mode = "walking"
            else:
                est_minutes = max(5, round(dist_km * 2.5 + 4))
                travel_mode = "driving / cab"

            # Scoring:
            # Normal gets +10 points over Moderate
            # Hidden gem gets +5 points
            # Distance penalty
            score = 100 - (dist_km * 3)
            if cand.crowd_status == 'Normal':
                score += 15
            elif cand.crowd_status == 'Moderate':
                score += 5

            if cand.is_hidden_gem:
                score += 10

            explanation = (
                f"{target_dest.name} is currently {target_dest.crowd_status.lower()}. "
                f"Consider {cand.name} instead. Estimated straight-line distance is {dist_km:.1f} km; "
                f"estimated {travel_mode} travel time is about {est_minutes} minutes. It is currently marked "
                f"{cand.crowd_status}. Listed hours (not live-verified): {cand.opening_hours or 'not available'}."
            )

            results.append({
                'destination': cand.to_dict(include_stories=False),
                'distance_km': round(dist_km, 2),
                'travel_time_minutes': est_minutes,
                'travel_mode': travel_mode,
                'distance_method': 'straight_line_estimate',
                'travel_time_is_estimate': True,
                'crowd_status': cand.crowd_status,
                'score': score,
                'explanation': explanation
            })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
