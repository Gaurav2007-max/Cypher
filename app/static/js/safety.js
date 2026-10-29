// TravelTech Tourist Safety & Emergency Controller

class SafetyManager {
    constructor() {
        this.currentCoords = null;
        this.watchId = null;
        this.fallCountdownInterval = null;
        this.checkinCountdownInterval = null;
        this.fallSecondsRemaining = 15;
        this.checkinSecondsRemaining = 0;
        this.lastSampleTime = 0;
        this.isTracking = false;
        this.motionListening = false;
        this.motionDataReceived = false;
        this.handleMotionEvent = (event) => this.handleMotion(event);
        this.lastAccelMagnitude = 9.8;
        this.sosCountdownInterval = null;
        this.sosCountdownDeadline = null;
        this.pendingSosPayload = null;
        this.pendingSosActionId = null;
        this.sosSubmitting = false;
        this.sosTriggerElement = null;
        this.checkinExpiryInterval = null;
        this.checkinExpiryAction = null;
    }

    init() {
        window.addEventListener('storage', event => {
            if (event.key === 'traveltech-location-consent' && event.newValue === 'false') {
                this.stopContinuousTracking();
                this.currentCoords = null;
            }
        });
        if (document.getElementById('checkinCountdownDisplay')) {
            this.checkActiveCheckin();
        }
        this.initMotionSensor();
    }

    // Explains location permission to tourist before prompting
    requestLocationPermission(callback) {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser.');
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                this.currentCoords = {
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                    accuracy: pos.coords.accuracy
                };
                this.isTracking = true;
                if (document.body.dataset.locationConsent === 'true') {
                    this.sendLocationSample(this.currentCoords);
                    this.startContinuousTracking();
                }
                if (callback) callback(this.currentCoords);
            },
            (err) => {
                console.warn("Location permission denied or unavailable:", err.message);
                if (callback) callback(null);
            },
            { enableHighAccuracy: true, timeout: 8000, maximumAge: 10000 }
        );
    }

    startContinuousTracking() {
        if (!navigator.geolocation || this.watchId !== null || document.body.dataset.locationConsent !== 'true') return;
        this.watchId = navigator.geolocation.watchPosition(
            (pos) => {
                this.currentCoords = {
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                    accuracy: pos.coords.accuracy
                };
                
                // Rate limit sample posting to every 15 seconds
                const now = Date.now();
                if (now - this.lastSampleTime > 15000) {
                    this.lastSampleTime = now;
                    this.sendLocationSample(this.currentCoords);
                }

                // Check proximity for stories if map is active
                if (window.travelMap && window.travelMap.checkProximity) {
                    window.travelMap.checkProximity(pos.coords.latitude, pos.coords.longitude);
                }
            },
            (err) => console.warn("Watch position error:", err),
            { enableHighAccuracy: true, maximumAge: 10000, timeout: 10000 }
        );
    }

    stopContinuousTracking() {
        if (this.watchId !== null && navigator.geolocation) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
        this.isTracking = false;
    }

    sendLocationSample(coords) {
        fetch('/api/safety/location-sample', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(coords)
        })
            .then(async response => {
                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.error || 'Location sample was rejected.');
                }
            })
            .catch(error => console.error('Could not record location sample:', error));
    }

    // Manual SOS
    triggerManualSOS() {
        if (this.pendingSosPayload || this.sosSubmitting) return;
        const payload = {
            latitude: this.currentCoords ? this.currentCoords.latitude : null,
            longitude: this.currentCoords ? this.currentCoords.longitude : null,
            accuracy: this.currentCoords ? this.currentCoords.accuracy : null,
            incident_type: 'sos_manual'
        };
        this.beginSosCountdown(payload);

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    if (this.pendingSosPayload === payload) {
                        payload.latitude = pos.coords.latitude;
                        payload.longitude = pos.coords.longitude;
                        payload.accuracy = pos.coords.accuracy;
                        if (this.pendingSosActionId) this.updatePendingSosLocation(payload);
                    }
                },
                () => {},
                { timeout: 5000 }
            );
        }
    }

    executeSosPost(payload) {
        if (this.pendingSosPayload || this.sosSubmitting) return;
        this.beginSosCountdown(payload);
    }

    async beginSosCountdown(payload) {
        const overlay = document.getElementById('sosCountdownOverlay');
        if (!overlay) {
            console.error('SOS countdown UI is missing; refusing to send without the 30-second cancellation window.');
            alert('SOS could not be started because the safety countdown is unavailable. Please reload the page and try again.');
            return;
        }

        this.pendingSosPayload = payload;
        this.sosTriggerElement = document.activeElement;
        try {
            const response = await fetch('/api/safety/sos/prepare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Could not start the emergency countdown.');
            if (this.pendingSosPayload !== payload) return;
            this.pendingSosActionId = data.action.id;
            this.sosCountdownDeadline = Date.parse(data.action.dispatch_at);
        } catch (error) {
            this.pendingSosPayload = null;
            this.sosTriggerElement = null;
            alert(error.message);
            return;
        }
        overlay.hidden = false;
        document.body.classList.add('sos-countdown-active');
        this.updateSosCountdown();
        const cancelButton = document.getElementById('cancelSosCountdown');
        if (cancelButton) cancelButton.focus();
        this.sosCountdownInterval = window.setInterval(() => this.updateSosCountdown(), 200);
    }

    updateSosCountdown() {
        if (!this.pendingSosPayload || !this.sosCountdownDeadline) return;
        const secondsRemaining = Math.max(0, Math.ceil((this.sosCountdownDeadline - Date.now()) / 1000));
        const display = document.getElementById('sosCountdownNumber');
        if (display) display.textContent = String(secondsRemaining);
        document.querySelectorAll('[data-sos-trigger]').forEach(button => {
            button.disabled = true;
            button.setAttribute('aria-disabled', 'true');
        });

        if (secondsRemaining === 0) {
            if (this.sosCountdownInterval !== null) {
                window.clearInterval(this.sosCountdownInterval);
                this.sosCountdownInterval = null;
            }
            const title = document.getElementById('sosCountdownTitle');
            if (title) title.textContent = 'Alert is being processed';
            const description = document.getElementById('sosCountdownDescription');
            if (description) description.textContent = 'The server is processing the queued alert. SMTP acceptance or failure will be reported when complete.';
            this.pollPendingSosAction();
        }
    }

    async cancelSosCountdown() {
        if (!this.pendingSosActionId || this.sosSubmitting) return;
        this.sosSubmitting = true;
        try {
            const response = await fetch(`/api/safety/actions/${this.pendingSosActionId}/cancel`, { method: 'POST' });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'The alert could not be cancelled.');
            this.clearSosCountdown();
        } catch (error) {
            alert(error.message);
            this.sosSubmitting = false;
            return;
        }
        this.sosSubmitting = false;
        const feedback = document.getElementById('sosCountdownStatus');
        if (feedback) feedback.textContent = 'SOS cancelled. No alert was sent.';
        if (this.sosTriggerElement && this.sosTriggerElement.isConnected) {
            this.sosTriggerElement.focus();
        }
        this.sosTriggerElement = null;
        alert('SOS cancelled. No emergency alert was sent.');
    }

    clearSosCountdown() {
        if (this.sosCountdownInterval !== null) {
            window.clearInterval(this.sosCountdownInterval);
            this.sosCountdownInterval = null;
        }
        this.sosCountdownDeadline = null;
        this.pendingSosPayload = null;
        this.pendingSosActionId = null;
        const overlay = document.getElementById('sosCountdownOverlay');
        if (overlay) overlay.hidden = true;
        document.body.classList.remove('sos-countdown-active');
        document.querySelectorAll('[data-sos-trigger]').forEach(button => {
            button.disabled = false;
            button.removeAttribute('aria-disabled');
        });
    }

    updatePendingSosLocation(payload) {
        fetch(`/api/safety/actions/${this.pendingSosActionId}/location`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then(async response => {
                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.error || 'Queued alert location was rejected.');
                }
            })
            .catch(error => console.error('Could not update queued SOS location:', error));
    }

    pollPendingSosAction() {
        if (!this.pendingSosActionId || this.sosSubmitting) return;
        this.sosSubmitting = true;
        fetch(`/api/safety/actions/${this.pendingSosActionId}`)
            .then(async response => {
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Could not check emergency alert status.');
                return data;
            })
            .then(data => {
                if (data.action.status === 'dispatched' && data.incident) {
                    this.clearSosCountdown();
                    this.showSosOutcome(data.incident);
                } else if (data.action.status === 'cancelled') {
                    this.clearSosCountdown();
                    alert('SOS cancelled; no alert was sent.');
                } else if (data.action.status === 'failed') {
                    this.clearSosCountdown();
                    alert(data.action.error || 'Alert processing failed. Contact emergency services directly.');
                } else {
                    window.setTimeout(() => this.pollPendingSosAction(), 1000);
                }
            })
            .catch(error => {
                console.error('Could not check queued SOS status:', error);
                window.setTimeout(() => this.pollPendingSosAction(), 2000);
            })
            .finally(() => {
                this.sosSubmitting = false;
            });
    }

    showSosOutcome(incident) {
        if (incident.email_sent && incident.email_delivery_status === 'live_smtp') {
            alert(`SOS incident #${incident.id} was accepted by the SMTP server for ${incident.email_recipient}. Final inbox delivery is not confirmed.`);
        } else {
            alert(`SOS incident #${incident.id} was recorded, but email was not sent.\nStatus: ${incident.email_delivery_status}\nRecipient: ${incident.email_recipient || 'No emergency contact'}\nCheck the server log for diagnostics.`);
        }
        window.location.reload();
    }

    // Motion Sensor & Fall Detection Heuristic
    initMotionSensor() {
        const enableButton = document.getElementById('enableMotionDetection');
        const status = document.getElementById('motionSensorStatus');
        if (!enableButton || !status) return;

        if (enableButton.dataset.sensorConsent !== 'true') {
            status.textContent = 'Motion sensing is off. Enable sensor consent in your profile to continue.';
            enableButton.hidden = true;
            return;
        }

        if (!('DeviceMotionEvent' in window)) {
            status.textContent = 'Motion sensors are not supported by this browser or device.';
            enableButton.disabled = true;
            return;
        }

        if (!window.isSecureContext) {
            status.textContent = 'Motion sensor access requires HTTPS or localhost.';
            enableButton.disabled = true;
            return;
        }

        status.textContent = 'Motion sensing is off until you enable it here.';
        enableButton.addEventListener('click', () => this.enableMotionSensor(enableButton, status));
    }

    async enableMotionSensor(button, status) {
        if (this.motionListening) return;
        button.disabled = true;
        status.textContent = 'Requesting motion sensor access...';

        try {
            const motionEvent = window.DeviceMotionEvent;
            if (typeof motionEvent.requestPermission === 'function') {
                const permission = await motionEvent.requestPermission();
                if (permission !== 'granted') {
                    status.textContent = 'Motion sensor permission was not granted. Allow it in your browser settings to use fall alerts.';
                    button.disabled = false;
                    return;
                }
            }

            window.addEventListener('devicemotion', this.handleMotionEvent);
            this.motionListening = true;
            button.hidden = true;
            status.textContent = 'Permission granted. Waiting for motion data from the device...';
        } catch (error) {
            console.error('Could not enable the motion sensor:', error);
            status.textContent = 'Could not enable motion sensing. Check browser permissions and try again.';
            button.disabled = false;
        }
    }

    handleMotion(event) {
        const accel = event.accelerationIncludingGravity;
        if (!accel) return;
        if (!this.motionDataReceived) {
            this.motionDataReceived = true;
            const status = document.getElementById('motionSensorStatus');
            if (status) status.textContent = 'Motion sensor is receiving data. Fall detection is using an impact heuristic.';
        }

        const x = accel.x || 0;
        const y = accel.y || 0;
        const z = accel.z || 0;
        const magnitude = Math.sqrt(x*x + y*y + z*z);

        // Heuristic: sudden peak impact (> 28 m/s^2, roughly ~2.8g)
        if (magnitude > 28.0 && this.lastAccelMagnitude < 18.0) {
            console.warn("Possible fall shock detected! Mag:", magnitude);
            this.promptFallAlert();
        }
        this.lastAccelMagnitude = magnitude;
    }

    // Fall alert prompt with visible countdown
    promptFallAlert() {
        if (this.fallCountdownInterval) return; // Already prompting

        const modalEl = document.getElementById('fallAlertModal');
        if (!modalEl) {
            // If modal not in DOM, simulate fallback
            return;
        }

        const modal = new bootstrap.Modal(modalEl);
        modal.show();

        this.fallSecondsRemaining = 15;
        const countSpan = document.getElementById('fallCountdownNumber');
        if (countSpan) countSpan.innerText = this.fallSecondsRemaining;

        this.fallCountdownInterval = setInterval(() => {
            this.fallSecondsRemaining--;
            if (countSpan) countSpan.innerText = this.fallSecondsRemaining;

            if (this.fallSecondsRemaining <= 0) {
                clearInterval(this.fallCountdownInterval);
                this.fallCountdownInterval = null;
                modal.hide();
                // User did not respond! Trigger emergency procedure
                this.executeSosPost({
                    latitude: this.currentCoords ? this.currentCoords.latitude : null,
                    longitude: this.currentCoords ? this.currentCoords.longitude : null,
                    accuracy: this.currentCoords ? this.currentCoords.accuracy : null,
                    incident_type: 'fall_detected'
                });
            }
        }, 1000);
    }

    cancelFallAlert() {
        if (this.fallCountdownInterval) {
            clearInterval(this.fallCountdownInterval);
            this.fallCountdownInterval = null;
        }
        const modalEl = document.getElementById('fallAlertModal');
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }
    }

    // Safety Check-In Timer
    startCheckIn(durationMinutes, notes = 'Routine Check-In') {
        fetch('/api/safety/checkin/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ duration_minutes: durationMinutes, notes: notes })
        })
        .then(async response => {
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Could not start the safety check-in.');
            return data;
        })
        .then(data => {
            if (data.status === 'started') {
                alert(`Safety Check-in Timer activated for ${durationMinutes} minutes.`);
                this.runCheckinCountdown(data.session.remaining_seconds);
                window.location.reload();
            }
        })
        .catch(error => alert(error.message));
    }

    confirmCheckInSafe() {
        fetch('/api/safety/checkin/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(async response => {
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || data.message || 'Could not confirm your check-in.');
            return data;
        })
        .then(data => {
            if (this.checkinExpiryInterval) {
                clearInterval(this.checkinExpiryInterval);
                this.checkinExpiryInterval = null;
            }
            const overlay = document.getElementById('checkinExpiryOverlay');
            if (overlay) overlay.hidden = true;
            alert(data.message || 'Safety confirmed!');
            window.location.reload();
        })
        .catch(error => alert(error.message));
    }

    requestCheckInHelp() {
        fetch('/api/safety/checkin/help', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(async response => {
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Could not queue the emergency alert.');
            return data;
        })
        .then(data => {
            this.checkinExpiryAction = data.action;
            this.updateCheckinExpiryCountdown();
        })
        .catch(error => alert(error.message));
    }

    checkActiveCheckin() {
        fetch('/api/safety/checkin/status')
            .then(async response => {
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Could not load check-in status.');
                return data;
            })
            .then(data => {
                if (data.has_active && data.session) {
                    this.runCheckinCountdown(data.session.remaining_seconds, data.action);
                }
            })
            .catch(error => console.error('Could not load active check-in:', error));
    }

    runCheckinCountdown(totalSeconds, action = null) {
        this.checkinSecondsRemaining = totalSeconds;
        const display = document.getElementById('checkinCountdownDisplay');
        if (!display) return;

        if (this.checkinCountdownInterval) clearInterval(this.checkinCountdownInterval);
        const deadline = Date.now() + Math.max(0, totalSeconds) * 1000;

        this.checkinCountdownInterval = setInterval(() => {
            this.checkinSecondsRemaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
            if (this.checkinSecondsRemaining <= 0) {
                clearInterval(this.checkinCountdownInterval);
                this.checkinCountdownInterval = null;
                display.innerText = "00:00 (Expired)";
                this.openCheckinExpiry(action);
                return;
            }

            const mins = Math.floor(this.checkinSecondsRemaining / 60);
            const secs = this.checkinSecondsRemaining % 60;
            display.innerText = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }, 1000);
    }

    openCheckinExpiry(action) {
        const overlay = document.getElementById('checkinExpiryOverlay');
        if (!overlay) return;
        this.checkinExpiryAction = action;
        overlay.hidden = false;
        document.body.classList.add('sos-countdown-active');
        const helpButton = document.getElementById('requestCheckinHelpButton');
        const status = document.getElementById('checkinExpiryStatus');
        if (!action) {
            if (helpButton) helpButton.hidden = true;
            if (status) status.textContent = 'Emergency consent is disabled; no automatic alert is queued. Review Safety Settings to enable emergency contact alerts.';
            document.getElementById('checkinExpiryCountdown').textContent = '--';
            return;
        }
        if (helpButton) helpButton.hidden = false;
        this.updateCheckinExpiryCountdown();
        if (this.checkinExpiryInterval) clearInterval(this.checkinExpiryInterval);
        this.checkinExpiryInterval = window.setInterval(() => this.updateCheckinExpiryCountdown(), 1000);
    }

    updateCheckinExpiryCountdown() {
        if (!this.checkinExpiryAction) return;
        const remaining = Math.max(0, Math.ceil((Date.parse(this.checkinExpiryAction.dispatch_at) - Date.now()) / 1000));
        const display = document.getElementById('checkinExpiryCountdown');
        const status = document.getElementById('checkinExpiryStatus');
        if (display) display.textContent = String(remaining);
        if (status) {
            status.textContent = remaining > 30
                ? `Confirm you are safe within ${remaining - 30} seconds.`
                : `Emergency alert queued; it will be processed in ${remaining} seconds. You can still confirm you are safe.`;
        }
        if (remaining === 0) this.pollCheckinAction();
    }

    pollCheckinAction() {
        if (!this.checkinExpiryAction || this.checkinPollInFlight) return;
        this.checkinPollInFlight = true;
        fetch(`/api/safety/actions/${this.checkinExpiryAction.id}`)
            .then(async response => {
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Could not check the check-in alert.');
                return data;
            })
            .then(data => {
                if (data.action.status === 'dispatched' && data.incident) {
                    if (this.checkinExpiryInterval) clearInterval(this.checkinExpiryInterval);
                    this.checkinExpiryInterval = null;
                    this.showSosOutcome(data.incident);
                } else if (data.action.status === 'cancelled') {
                    const status = document.getElementById('checkinExpiryStatus');
                    if (status) status.textContent = 'Alert cancelled.';
                } else if (data.action.status === 'failed') {
                    if (this.checkinExpiryInterval) clearInterval(this.checkinExpiryInterval);
                    this.checkinExpiryInterval = null;
                    const status = document.getElementById('checkinExpiryStatus');
                    if (status) status.textContent = data.action.error || 'Alert processing failed. Contact emergency services directly.';
                } else {
                    window.setTimeout(() => this.pollCheckinAction(), 1000);
                }
            })
            .catch(error => {
                console.error('Could not check the check-in alert:', error);
                window.setTimeout(() => this.pollCheckinAction(), 2000);
            })
            .finally(() => {
                this.checkinPollInFlight = false;
            });
    }
}

window.travelSafety = new SafetyManager();
document.addEventListener('DOMContentLoaded', () => {
    window.travelSafety.init();
});
