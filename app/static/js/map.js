// TravelTech Leaflet Interactive Map & Proximity Engine

class TravelMap {
    constructor(elementId = 'mainMap') {
        this.elementId = elementId;
        this.map = null;
        this.markers = [];
        this.userMarker = null;
        this.routeLayer = null;
        this.notifiedStoryIds = new Set();
        this.cityCenter = [28.4089, 77.3178]; // Default Faridabad
    }

    init(cityLat, cityLng, zoom = 13) {
        if (!document.getElementById(this.elementId)) return;
        this.cityCenter = [cityLat, cityLng];

        this.map = L.map(this.elementId, {
            center: this.cityCenter,
            zoom: zoom,
            zoomControl: true
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(this.map);
    }

    getCrowdColor(status) {
        switch (status) {
            case 'Normal': return '#137333';
            case 'Moderate': return '#B06000';
            case 'Crowded': return '#D9381E';
            case 'Overcrowded': return '#C5221F';
            default: return '#00A699';
        }
    }

    loadDestinations(destinations) {
        this.clearMarkers();

        destinations.forEach(dest => {
            const color = this.getCrowdColor(dest.crowd_status);
            const isOvercrowded = dest.crowd_status === 'Overcrowded';

            // Custom SVG Pin Icon
            const iconHtml = `
                <div style="
                    background: ${color};
                    width: 34px;
                    height: 34px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    border: 3px solid white;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    font-size: 15px;
                    ${isOvercrowded ? 'animation: radarPulse 1.5s infinite;' : ''}
                ">
                    <i class="bi ${dest.is_hidden_gem ? 'bi-gem' : 'bi-geo-alt-fill'}"></i>
                </div>
            `;

            const customIcon = L.divIcon({
                html: iconHtml,
                className: 'custom-map-pin',
                iconSize: [34, 34],
                iconAnchor: [17, 34],
                popupAnchor: [0, -34]
            });

            const marker = L.marker([dest.latitude, dest.longitude], { icon: customIcon }).addTo(this.map);

            let popupContent = `
                <div style="max-width: 260px; font-family: inherit;">
                    ${dest.image_url ? `<img src="${dest.image_url}" style="width: 100%; height: 110px; object-fit: cover; border-radius: 8px 8px 0 0; margin-bottom: 8px;" alt="${dest.name}" />` : ''}
                    <h6 style="margin-bottom: 4px; font-weight: 700;">${dest.name}</h6>
                    <div style="margin-bottom: 8px;">
                        <span class="badge badge-crowd-${dest.crowd_status.toLowerCase()}">${dest.crowd_status}</span>
                        ${dest.is_hidden_gem ? '<span class="badge bg-warning text-dark"><i class="bi bi-gem me-1"></i>Hidden Gem</span>' : ''}
                    </div>
                    <p style="font-size: 0.8rem; color: #555; margin-bottom: 8px;">${dest.description.substring(0, 85)}...</p>
                    <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                        <button class="btn btn-sm btn-outline-danger" onclick="window.travelMap.requestDirections(${dest.latitude}, ${dest.longitude}, '${dest.name.replace(/'/g, "\\'")}')">
                            <i class="bi bi-compass me-1"></i>Directions
                        </button>
                        ${isOvercrowded || dest.crowd_status === 'Crowded' ? `
                            <button class="btn btn-sm btn-danger" onclick="window.openSmartAlternatives(${dest.id})">
                                <i class="bi bi-shuffle me-1"></i>Avoid Crowd
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;

            marker.bindPopup(popupContent);
            this.markers.push(marker);
        });

        // Fit bounds if markers exist
        if (this.markers.length > 0) {
            const group = new L.featureGroup(this.markers);
            this.map.fitBounds(group.getBounds().pad(0.2));
        }
    }

    clearMarkers() {
        this.markers.forEach(m => this.map.removeLayer(m));
        this.markers = [];
    }

    setUserLocation(lat, lng) {
        if (!this.map) return;

        if (this.userMarker) {
            this.userMarker.setLatLng([lat, lng]);
        } else {
            const userIconHtml = `
                <div style="
                    background: #1A73E8;
                    width: 22px;
                    height: 22px;
                    border-radius: 50%;
                    border: 3px solid white;
                    box-shadow: 0 0 0 8px rgba(26, 115, 232, 0.3);
                "></div>
            `;
            const icon = L.divIcon({
                html: userIconHtml,
                className: 'user-location-pin',
                iconSize: [22, 22],
                iconAnchor: [11, 11]
            });
            this.userMarker = L.marker([lat, lng], { icon: icon }).addTo(this.map);
            this.userMarker.bindTooltip("You are here", { permanent: false, direction: 'top' });
        }
    }

    checkProximity(lat, lng) {
        this.setUserLocation(lat, lng);

        fetch('/api/stories/proximity', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ latitude: lat, longitude: lng })
        })
        .then(r => r.json())
        .then(data => {
            if (data.in_proximity && data.story) {
                const storyId = data.story.id;
                // Only notify once per session unless tourist moves away and comes back
                if (!this.notifiedStoryIds.has(storyId)) {
                    this.notifiedStoryIds.add(storyId);
                    this.triggerStoryModal(data.destination, data.story, data.distance_meters);
                }
            }
        })
        .catch(e => console.error("Proximity check failed:", e));
    }

    triggerStoryModal(destination, story, distance) {
        const modalEl = document.getElementById('proximityStoryModal');
        if (!modalEl) return;

        document.getElementById('proxStoryTitle').innerText = story.title;
        document.getElementById('proxStoryPlace').innerText = destination.name;
        document.getElementById('proxStoryDist').innerText = `${distance}m away`;
        document.getElementById('proxStoryImage').src = story.image_url || destination.image_url;
        document.getElementById('proxStoryContent').innerText = story.content;
        document.getElementById('proxStoryFunFact').innerText = story.fun_facts || '';

        const playBtn = document.getElementById('proxStoryPlayBtn');
        if (playBtn) {
            playBtn.onclick = () => {
                window.travelTTS.speak(story.audio_text || story.content, story.title);
            };
        }

        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }

    requestDirections(destLat, destLng, destName) {
        let origLat = this.cityCenter[0];
        let origLon = this.cityCenter[1];

        if (this.userMarker) {
            const pos = this.userMarker.getLatLng();
            origLat = pos.lat;
            origLon = pos.lng;
        }

        fetch('/api/routes/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                origin_lat: origLat,
                origin_lon: origLon,
                dest_lat: destLat,
                dest_lon: destLng,
                mode: 'driving'
            })
        })
        .then(async response => {
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Could not calculate this route.');
            return data;
        })
        .then(data => {
            if (data.geometry) {
                if (this.routeLayer) this.map.removeLayer(this.routeLayer);

                // Leaflet GeoJSON takes [lat, lng] inside coordinates, but GeoJSON standard is [lon, lat]
                const latLngs = data.geometry.coordinates.map(pt => [pt[1], pt[0]]);
                this.routeLayer = L.polyline(latLngs, {
                    color: '#FF5A5F',
                    weight: 6,
                    opacity: 0.85,
                    dashArray: '1, 8',
                    lineCap: 'round'
                }).addTo(this.map);

                this.map.fitBounds(this.routeLayer.getBounds().pad(0.3));

                // Open Route Info Card in UI
                window.showRouteResults(destName, data);
            } else {
                throw new Error('No route was returned for this destination.');
            }
        })
        .catch(error => alert(`Could not load directions: ${error.message}`));
    }
}

window.travelMap = new TravelMap();
