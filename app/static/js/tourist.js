// TravelTech Tourist Dashboard Interactions

async function postJson(url, body) {
    const response = await fetch(url, {
        method: 'POST',
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : undefined
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || data.message || 'The request could not be completed.');
    }
    return data;
}

async function toggleSavedItem(url, btn, savedIcon, unsavedIcon) {
    if (btn.disabled) return null;

    btn.disabled = true;
    try {
        const data = await postJson(url);
        const icon = btn.querySelector('i');
        if (icon) {
            icon.className = data.saved ? savedIcon : unsavedIcon;
        }
        btn.setAttribute('aria-pressed', String(data.saved));
        return data;
    } catch (error) {
        alert(error.message);
        return null;
    } finally {
        btn.disabled = false;
    }
}

function toggleSaveDestination(destId, btn) {
    return toggleSavedItem(
        `/api/destinations/${destId}/save`,
        btn,
        'bi bi-heart-fill text-danger',
        'bi bi-heart text-muted'
    );
}

function toggleSaveStory(storyId, btn) {
    return toggleSavedItem(
        `/api/stories/${storyId}/save`,
        btn,
        'bi bi-bookmark-fill text-primary',
        'bi bi-bookmark text-muted'
    );
}

function openSmartAlternatives(destId) {
    const modalEl = document.getElementById('smartAlternativesModal');
    if (!modalEl) return;

    const container = document.getElementById('alternativesListContainer');
    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2 text-muted">Calculating crowd-free alternatives...</p></div>';

    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    fetch(`/api/destinations/${destId}/recommendations`)
        .then(async response => {
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Could not load alternatives.');
            return data;
        })
        .then(recs => {
            if (!recs || recs.length === 0) {
                container.innerHTML = '<div class="alert alert-info">No alternative destinations found in this area currently.</div>';
                return;
            }

            let html = `
                <div class="alert alert-warning mb-4 d-flex align-items-center">
                    <i class="bi bi-exclamation-triangle-fill fs-3 me-3 text-warning"></i>
                    <div>
                        <strong>High Congestion Detected!</strong>
                        <div class="small">Our dynamic crowd engine suggests these authentic, less-crowded cultural alternatives nearby:</div>
                    </div>
                </div>
                <div class="row g-3">
            `;

            recs.forEach(r => {
                const dest = r.destination;
                html += `
                    <div class="col-md-12">
                        <div class="card border-0 shadow-sm rounded-4 overflow-hidden">
                            <div class="row g-0">
                                <div class="col-sm-4 position-relative" style="min-height: 140px; background: linear-gradient(135deg, #dce8e7, #b8d2d0 52%, #f0d7c8);">
                                    <div class="image-fallback" aria-hidden="true"><i class="bi bi-image"></i></div>
                                    ${dest.image_url ? `<img src="${dest.image_url}" class="card-img-top position-absolute top-0 start-0 w-100 h-100" style="object-fit: cover;" alt="${dest.name}" onerror="this.classList.add('image-failed')">` : ''}
                                </div>
                                <div class="col-sm-8">
                                    <div class="card-body">
                                        <div class="d-flex justify-content-between align-items-start mb-1">
                                            <h6 class="fw-bold mb-0">${dest.name}</h6>
                                            <span class="badge badge-crowd-${r.crowd_status.toLowerCase()}">${r.crowd_status}</span>
                                        </div>
                                        <p class="text-muted small mb-2"><i class="bi bi-clock-history me-1 text-primary"></i>${r.explanation}</p>
                                        <div class="d-flex justify-content-between align-items-center mt-3">
                                            <span class="badge bg-light text-dark border">
                                                <i class="bi bi-cursor-fill me-1 text-secondary"></i>${r.distance_km} km (${r.travel_time_minutes} mins via ${r.travel_mode})
                                            </span>
                                            <button class="btn btn-sm btn-outline-primary rounded-pill px-3" onclick="window.travelMap.requestDirections(${dest.latitude}, ${dest.longitude}, '${dest.name.replace(/'/g, "\\'")}')">
                                                <i class="bi bi-compass me-1"></i>Navigate Here
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });

            html += `
                </div>
                <div class="mt-4 p-3 bg-light rounded-4 text-center">
                    <span class="small text-muted d-block mb-2">Want to visit the original destination later?</span>
                    <button class="btn btn-sm btn-outline-secondary rounded-pill" onclick="subscribeCrowdAlert(${destId})">
                        <i class="bi bi-bell me-1"></i>Notify Me When Crowd Normalizes
                    </button>
                </div>
            `;

            container.innerHTML = html;
        })
        .catch(e => {
            container.innerHTML = `<div class="alert alert-danger">Failed to load alternatives: ${e.message}</div>`;
        });
}

function subscribeCrowdAlert(destId) {
    postJson(`/api/destinations/${destId}/subscribe-crowd`)
        .then(data => {
            alert(data.message || 'Subscribed!');
        })
        .catch(error => alert(error.message));
}

function showRouteResults(destName, routeData) {
    const card = document.getElementById('routeResultCard');
    if (!card) return;

    document.getElementById('routeDestName').innerText = destName;
    document.getElementById('routeDistance').innerText = `${routeData.distance_km} km`;
    document.getElementById('routeSource').innerText = routeData.source_label;

    const modes = routeData.modes;
    document.getElementById('routeWalkTime').innerText = `${modes.walking.duration_minutes} min`;
    document.getElementById('routeDriveTime').innerText = `${modes.driving.duration_minutes} min (${modes.driving.fare_display})`;
    document.getElementById('routeTransitTime').innerText = modes.transit.available
        ? `${modes.transit.duration_minutes} min (${modes.transit.fare_display})`
        : modes.transit.description;

    card.classList.remove('d-none');
    card.scrollIntoView({ behavior: 'smooth' });
}

// Filter chips for Destinations
function filterDestinations(category, el) {
    document.querySelectorAll('.filter-dest-chip').forEach(c => c.classList.remove('active'));
    if (el) el.classList.add('active');

    const cards = document.querySelectorAll('.dest-card-item');
    cards.forEach(card => {
        const cat = card.getAttribute('data-category');
        const isHidden = card.getAttribute('data-hidden-gem') === 'true';

        if (category === 'all') {
            card.classList.remove('d-none');
        } else if (category === 'hidden') {
            card.classList.toggle('d-none', !isHidden);
        } else {
            card.classList.toggle('d-none', cat !== category);
        }
    });
}

// Filter chips for Cuisine
function filterCuisine(tag, el) {
    document.querySelectorAll('.filter-cuisine-chip').forEach(c => c.classList.remove('active'));
    if (el) el.classList.add('active');

    const cards = document.querySelectorAll('.cuisine-card-item');
    cards.forEach(card => {
        const tags = card.getAttribute('data-tags') || '';
        if (tag === 'all') {
            card.classList.remove('d-none');
        } else {
            card.classList.toggle('d-none', !tags.includes(tag));
        }
    });
}

// Proximity Simulation for Demos
function simulateProximityTo(destName, lat, lng) {
    if (window.travelMap) {
        window.travelMap.checkProximity(lat, lng);
    }
}

// User Feedback Reporting
function openFeedbackModal(destId = null, destName = '') {
    const modalEl = document.getElementById('feedbackReportModal');
    if (!modalEl) return;
    document.getElementById('feedbackDestId').value = destId || '';
    document.getElementById('feedbackDestNameDisplay').innerText = destName ? `Regarding: ${destName}` : 'General Feedback';
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
}

function submitFeedbackForm(event) {
    event.preventDefault();
    const destId = document.getElementById('feedbackDestId').value;
    const type = document.getElementById('feedbackType').value;
    const desc = document.getElementById('feedbackDescription').value;

    const submitButton = event.currentTarget.querySelector('[type="submit"]');
    submitButton.disabled = true;

    postJson('/api/feedback/submit', {
            destination_id: destId ? parseInt(destId) : null,
            feedback_type: type,
            description: desc
        })
    .then(data => {
            const modalEl = document.getElementById('feedbackReportModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            document.getElementById('feedbackForm').reset();
            alert(data.message || 'Feedback submitted!');
    })
    .catch(error => {
        alert(`Could not submit feedback: ${error.message}`);
    })
    .finally(() => {
        submitButton.disabled = false;
    });
}
