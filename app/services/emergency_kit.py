import json
import math
from datetime import datetime, timezone
from http.client import HTTPException
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OVERPASS_URL = 'https://overpass-api.de/api/interpreter'
SEARCH_RADIUS_METERS = 6000
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
FACILITY_LABELS = {
    'police': 'Police station',
    'hospital': 'Hospital',
    'clinic': 'Clinic',
    'doctors': 'Doctor',
    'fuel': 'Petrol pump / fuel station',
    'fire_station': 'Fire station',
}


class EmergencyKitSourceError(Exception):
    pass


def build_emergency_kit(city):
    latitude = float(city.latitude)
    longitude = float(city.longitude)
    if not (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    ):
        raise EmergencyKitSourceError('The selected city has invalid coordinates.')

    query = (
        '[out:json][timeout:25];'
        f'nwr(around:{SEARCH_RADIUS_METERS},{latitude:.6f},{longitude:.6f})'
        '["amenity"~"^(police|hospital|clinic|doctors|fuel|fire_station)$"]->.facilities;'
        '.facilities out center;'
        f'way(around:{SEARCH_RADIUS_METERS},{latitude:.6f},{longitude:.6f})'
        '["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified|living_street|pedestrian|service)$"]->.roads;'
        '.roads out geom;'
    )
    request = Request(
        OVERPASS_URL,
        data=urlencode({'data': query}).encode('utf-8'),
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'TravelTech offline emergency kit',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw_data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw_data) > MAX_RESPONSE_BYTES:
            raise EmergencyKitSourceError('OpenStreetMap returned too much data. Try again later.')
        overpass_data = json.loads(raw_data)
    except EmergencyKitSourceError:
        raise
    except (
        URLError,
        TimeoutError,
        OSError,
        HTTPException,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise EmergencyKitSourceError(
            'Could not retrieve OpenStreetMap data. Check your connection or try again later.'
        ) from error

    if not isinstance(overpass_data, dict):
        raise EmergencyKitSourceError('OpenStreetMap returned an invalid data response.')
    elements = overpass_data.get('elements')
    if not isinstance(elements, list):
        raise EmergencyKitSourceError('OpenStreetMap returned an invalid data response.')

    facilities = []
    roads = []
    for element in elements:
        if not isinstance(element, dict):
            raise EmergencyKitSourceError('OpenStreetMap returned an invalid data response.')
        tags = element.get('tags') or {}
        if not isinstance(tags, dict):
            raise EmergencyKitSourceError('OpenStreetMap returned an invalid data response.')
        amenity = tags.get('amenity')
        if amenity in FACILITY_LABELS:
            location = element.get('center', element)
            try:
                facility_latitude = float(location['lat'])
                facility_longitude = float(location['lon'])
            except (KeyError, TypeError, ValueError):
                continue
            if not (
                math.isfinite(facility_latitude)
                and math.isfinite(facility_longitude)
                and -90 <= facility_latitude <= 90
                and -180 <= facility_longitude <= 180
            ):
                continue
            facilities.append({
                'id': f"{element.get('type', 'object')}/{element.get('id', '')}",
                'name': tags.get('name') or f'Unnamed {FACILITY_LABELS[amenity]}',
                'category': amenity,
                'category_label': FACILITY_LABELS[amenity],
                'latitude': facility_latitude,
                'longitude': facility_longitude,
                'phone': tags.get('contact:phone') or tags.get('phone') or '',
                'address': ', '.join(filter(None, (
                    tags.get('addr:housenumber'),
                    tags.get('addr:street'),
                    tags.get('addr:city'),
                ))),
            })

        if tags.get('highway') and element.get('type') == 'way':
            geometry = element.get('geometry') or []
            if len(geometry) < 2:
                continue
            stride = max(1, math.ceil(len(geometry) / 100))
            points = geometry[::stride]
            if points[-1] != geometry[-1]:
                points.append(geometry[-1])
            coordinates = []
            for point in points:
                try:
                    point_latitude = float(point['lat'])
                    point_longitude = float(point['lon'])
                except (KeyError, TypeError, ValueError):
                    continue
                if (
                    math.isfinite(point_latitude)
                    and math.isfinite(point_longitude)
                    and -90 <= point_latitude <= 90
                    and -180 <= point_longitude <= 180
                ):
                    coordinates.append([point_latitude, point_longitude])
            roads.append({
                'type': tags['highway'],
                'coordinates': coordinates,
            })

    city_country = (city.country or '').casefold()
    emergency_numbers = []
    if city_country in {'india', 'भारत'}:
        emergency_numbers.append({
            'number': '112',
            'label': 'National Emergency Response Support System (India)',
            'scope': 'National',
            'source': 'https://112.gov.in/',
        })

    return {
        'city': {
            'name': city.name,
            'state': city.state,
            'country': city.country,
            'latitude': latitude,
            'longitude': longitude,
        },
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'radius_meters': SEARCH_RADIUS_METERS,
        'source': 'OpenStreetMap contributors',
        'attribution': '© OpenStreetMap contributors; map data available under the Open Database License (ODbL): https://www.openstreetmap.org/copyright',
        'emergency_numbers': emergency_numbers,
        'facilities': facilities[:500],
        'roads': [road for road in roads if len(road['coordinates']) > 1][:2500],
        'safe_avoid_zones': [],
    }
