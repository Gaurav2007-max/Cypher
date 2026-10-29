import math
import requests
from flask import Blueprint, request, jsonify
from app.services.crowd_service import haversine_distance

api_routes_bp = Blueprint('api_routes', __name__, url_prefix='/api/routes')

@api_routes_bp.route('/calculate', methods=['POST'])
def calculate_route():
    data = request.get_json() or {}
    try:
        orig_lat = float(data['origin_lat'])
        orig_lon = float(data['origin_lon'])
        dest_lat = float(data['dest_lat'])
        dest_lon = float(data['dest_lon'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': 'Four numeric origin and destination coordinates are required.'}), 400
    mode = data.get('mode', 'driving')  # 'walking', 'driving', 'transit'

    if mode not in {'walking', 'driving', 'transit'}:
        return jsonify({'error': 'Mode must be walking, driving, or transit.'}), 400
    if not all(math.isfinite(value) for value in (orig_lat, orig_lon, dest_lat, dest_lon)):
        return jsonify({'error': 'Coordinates must be finite numbers.'}), 400
    if not (-90 <= orig_lat <= 90 and -90 <= dest_lat <= 90 and -180 <= orig_lon <= 180 and -180 <= dest_lon <= 180):
        return jsonify({'error': 'Coordinates are outside the valid range.'}), 400

    dist_km = haversine_distance(orig_lat, orig_lon, dest_lat, dest_lon)

    # Attempt OSRM if accessible, otherwise graceful calculation fallback
    route_geometry = None
    is_live_routing = False

    try:
        if mode == 'transit':
            raise RuntimeError('No live transit routing provider is configured.')
        profile = 'foot' if mode == 'walking' else 'car'
        osrm_url = f"https://router.project-osrm.org/route/v1/{profile}/{orig_lon},{orig_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"
        resp = requests.get(osrm_url, timeout=3)
        if resp.status_code == 200:
            res_data = resp.json()
            if res_data.get('routes'):
                route_obj = res_data['routes'][0]
                route_geometry = route_obj.get('geometry')
                dist_km = route_obj.get('distance', dist_km * 1000) / 1000.0
                is_live_routing = True
    except (requests.RequestException, ValueError, RuntimeError):
        # Fallback to direct coords calculation
        pass

    if not route_geometry:
        # Interpolate 5 waypoints for visual rendering on Leaflet
        points = []
        for i in range(6):
            fraction = i / 5.0
            plat = orig_lat + (dest_lat - orig_lat) * fraction
            plon = orig_lon + (dest_lon - orig_lon) * fraction
            points.append([plon, plat])
        route_geometry = {
            'type': 'LineString',
            'coordinates': points
        }

    # Calculations for different modes
    walking_mins = max(3, round(dist_km * 13))
    driving_mins = max(4, round((dist_km / 24.0) * 60 + 3))
    auto_fare = max(30, round(30 + max(0, dist_km - 2) * 12))

    return jsonify({
        'distance_km': round(dist_km, 2),
        'is_live_routing': is_live_routing,
        'source_label': 'Live OSRM Routing' if is_live_routing else 'Estimated Urban Travel Model',
        'geometry': route_geometry,
        'modes': {
            'walking': {
                'duration_minutes': walking_mins,
                'is_estimate': not (is_live_routing and mode == 'walking'),
                'fare_inr': 0,
                'fare_display': 'Free',
                'description': f'Scenic walk ({dist_km:.1f} km)'
            },
            'driving': {
                'duration_minutes': driving_mins,
                'is_estimate': not (is_live_routing and mode == 'driving'),
                'fare_inr': auto_fare,
                'fare_display': f'₹{auto_fare} (Auto/Cab)',
                'description': f'Cab / Auto-rickshaw via main roads'
            },
            'transit': {
                'available': False,
                'is_estimate': True,
                'description': 'No transit schedule provider is configured. Check local operator information.'
            }
        }
    })
