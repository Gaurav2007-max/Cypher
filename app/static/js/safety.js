// TravelTech Tourist Safety & Emergency Controller

const FALL_IMPACT_THRESHOLD = 28;

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
        this.lastFreefallAt = null;
        this.lastFallDetectedAt = null;
        this.alertAudioContext = null;
        this.alertSignalInterval = null;
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
                this.stopSafetyMonitoring(false);
            } else if (event.key === 'traveltech-sensor-consent' && event.newValue === 'false') {
                this.stopSafetyMonitoring(false);
            } else if (event.key === 'traveltech-safety-monitoring' && event.newValue === 'false') {
                this.stopSafetyMonitoring(false);
            } else if (event.key === 'traveltech-safety-monitoring' && event.newValue === 'true') {
                this.resumeSafetyMonitoring();
            }
        });
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.isSafetyMonitoringEnabled() &&
                this.hasMotionConsent() && this.hasLocationConsent() &&
                !this.motionListening) {
                this.resumeSafetyMonitoring();
            }
        });
        if (document.getElementById('checkinCountdownDisplay')) {
            this.checkActiveCheckin();
        }
        this.initMotionSensor();
        if (this.isSafetyMonitoringEnabled()) {
            this.resumeSafetyMonitoring();
        }
    }

    isSafetyMonitoringEnabled() {
        try {
            return localStorage.getItem('traveltech-safety-monitoring') !== 'false' &&
                this.hasMotionConsent() && this.hasLocationConsent();
        } catch (error) {
            console.error('Could not read the safety monitoring preference:', error);
            return this.hasMotionConsent() && this.hasLocationConsent();
        }
    }

    hasMotionConsent() {
        return document.body.dataset.sensorConsent === 'true';
    }

    hasLocationConsent() {
        return document.body.dataset.locationConsent === 'true';
    }

    resumeSafetyMonitoring() {
        if (!this.hasMotionConsent() || !this.hasLocationConsent()) {
            this.stopSafetyMonitoring(false);
            return;
        }

        if (!('DeviceMotionEvent' in window)) {
            const status = document.getElementById('motionSensorStatus');
            if (status) status.textContent = 'Motion sensors are not supported by this browser or device.';
            this.updateMonitoringControls(false);
            return;
        }

        if (typeof window.DeviceMotionEvent?.requestPermission === 'function' &&
            !this.hasGrantedMotionPermission()) {
            const status = document.getElementById('motionSensorStatus');
            const button = document.getElementById('enableMotionDetection');
            if (status) status.textContent = 'Automatic monitoring is enabled. Grant motion access once in this browser to start sensing.';
            if (button) {
                button.hidden = false;
                button.disabled = false;
            }
            return;
        }

        this.attachMotionSensor();
        this.requestLocationPermission().then(coords => {
            if (!coords) {
                this.stopMotionSensor();
                this.updateMonitoringControls(false);
                const status = document.getElementById('motionSensorStatus');
                if (status) status.textContent = 'Location access is unavailable. Tap enable to resume safety monitoring.';
                return;
            }
            this.updateMonitoringControls(true);
        });
    }

    async enableSafetyMonitoring(button, status) {
        if (!this.hasMotionConsent() || !this.hasLocationConsent()) {
            status.textContent = 'Enable location and motion consent in your profile before starting safety monitoring.';
            return;
        }
        button.disabled = true;
        status.textContent = 'Requesting motion and location access...';
        this.primeAlertOutput();

        if (!await this.enableMotionSensor()) {
            button.disabled = false;
            return;
        }

        const coords = await this.requestLocationPermission();
        if (!coords) {
            this.stopMotionSensor();
            status.textContent = 'Location permission is needed for safety monitoring. Allow it in your browser and try again.';
            button.disabled = false;
            return;
        }

        try {
            localStorage.setItem('traveltech-safety-monitoring', 'true');
        } catch (error) {
            this.stopMotionSensor();
            this.stopContinuousTracking();
            status.textContent = 'Could not save this monitoring preference in browser storage.';
            console.error('Could not save the safety monitoring preference:', error);
            button.disabled = false;
            return;
        }

        status.textContent = 'Automatic safety monitoring is active while this browser allows sensors and location access.';
        this.updateMonitoringControls(true);
    }

    hasGrantedMotionPermission() {
        try {
            return localStorage.getItem('traveltech-motion-permission') === 'granted';
        } catch (error) {
            console.error('Could not read the motion permission state:', error);
            return false;
        }
    }

    stopSafetyMonitoring(clearPreference = true) {
        if (clearPreference) {
            try {
                localStorage.setItem('traveltech-safety-monitoring', 'false');
            } catch (error) {
                console.error('Could not save the safety monitoring preference:', error);
            }
        }
        this.stopMotionSensor();
        this.stopContinuousTracking();
        this.currentCoords = null;
        this.updateMonitoringControls(false);
        const status = document.getElementById('motionSensorStatus');
        if (status) status.textContent = 'Safety monitoring is off. Enable it here to resume.';
    }

    updateMonitoringControls(active) {
        const enableButton = document.getElementById('enableMotionDetection');
        const stopButton = document.getElementById('stopSafetyMonitoring');
        if (enableButton) enableButton.hidden = active;
        if (stopButton) stopButton.hidden = !active;
    }

    // Explains location permission to tourist before prompting
    requestLocationPermission(callback) {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser.');
            if (callback) callback(null);
            return Promise.resolve(null);
        }

        return new Promise(resolve => {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    this.currentCoords = {
                        latitude: pos.coords.latitude,
                        longitude: pos.coords.longitude,
                        accuracy: pos.coords.accuracy
                    };
                    this.isTracking = true;
                    if (this.hasLocationConsent()) {
                        this.sendLocationSample(this.currentCoords);
                        this.startContinuousTracking();
                    }
                    if (callback) callback(this.currentCoords);
                    resolve(this.currentCoords);
                },
                (err) => {
                    console.warn('Location permission denied or unavailable:', err.message);
                    if (callback) callback(null);
                    resolve(null);
                },
                { enableHighAccuracy: true, timeout: 8000, maximumAge: 10000 }
            );
        });
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
        this.primeAlertOutput();
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

    simulateFallAlert() {
        this.primeAlertOutput();
        this.promptFallAlert();
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
            this.stopAlertSignal();
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
            this.stopAlertSignal();
            alert(error.message);
            return;
        }
        this.startAlertSignal();
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
        this.stopAlertSignal();
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

    primeAlertOutput() {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextClass) return;
        try {
            if (!this.alertAudioContext) this.alertAudioContext = new AudioContextClass();
            if (this.alertAudioContext.state === 'suspended') {
                this.alertAudioContext.resume().catch(error => {
                    console.warn('Could not enable emergency alert audio:', error);
                });
            }
        } catch (error) {
            console.warn('Emergency alert audio is unavailable:', error);
        }
    }

    playAlertTone() {
        if (!this.alertAudioContext || this.alertAudioContext.state !== 'running') return;
        try {
            const oscillator = this.alertAudioContext.createOscillator();
            const gain = this.alertAudioContext.createGain();
            const now = this.alertAudioContext.currentTime;
            oscillator.type = 'sawtooth';
            oscillator.frequency.setValueAtTime(880, now);
            oscillator.frequency.setValueAtTime(660, now + 0.18);
            gain.gain.setValueAtTime(0.0001, now);
            gain.gain.exponentialRampToValueAtTime(0.18, now + 0.04);
            gain.gain.setValueAtTime(0.18, now + 0.28);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.42);
            oscillator.connect(gain);
            gain.connect(this.alertAudioContext.destination);
            oscillator.start(now);
            oscillator.stop(now + 0.43);
        } catch (error) {
            console.warn('Could not play the emergency alert tone:', error);
        }
    }

    startAlertSignal() {
        if (this.alertSignalInterval !== null) return;
        const signal = () => {
            if (navigator.vibrate) {
                try {
                    navigator.vibrate([500, 180, 500, 180, 800]);
                } catch (error) {
                    console.warn('Device vibration is unavailable:', error);
                }
            }
            this.playAlertTone();
        };
        signal();
        this.alertSignalInterval = window.setInterval(signal, 2500);
    }

    stopAlertSignal() {
        if (this.alertSignalInterval !== null) {
            window.clearInterval(this.alertSignalInterval);
            this.alertSignalInterval = null;
        }
        if (navigator.vibrate) {
            try {
                navigator.vibrate(0);
            } catch (error) {
                console.warn('Could not stop device vibration:', error);
            }
        }
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

        if (!this.hasLocationConsent()) {
            status.textContent = 'Enable location tracking consent in your profile to start combined safety monitoring.';
            enableButton.hidden = true;
            return;
        }

        status.textContent = 'Motion sensing is off until you enable it here.';
        enableButton.addEventListener('click', () => this.enableSafetyMonitoring(enableButton, status));
    }

    async enableMotionSensor() {
        if (this.motionListening) return true;

        try {
            const motionEvent = window.DeviceMotionEvent;
            if (typeof motionEvent.requestPermission === 'function' &&
                !this.hasGrantedMotionPermission()) {
                const permission = await motionEvent.requestPermission();
                if (permission !== 'granted') {
                    const status = document.getElementById('motionSensorStatus');
                    if (status) status.textContent = 'Motion sensor permission was not granted. Allow it in your browser settings to use fall alerts.';
                    return false;
                }
                try {
                    localStorage.setItem('traveltech-motion-permission', 'granted');
                } catch (error) {
                    console.error('Could not save the motion permission state:', error);
                }
            }

            this.attachMotionSensor();
            return true;
        } catch (error) {
            console.error('Could not enable the motion sensor:', error);
            const status = document.getElementById('motionSensorStatus');
            if (status) status.textContent = 'Could not enable motion sensing. Check browser permissions and try again.';
            return false;
        }
    }

    attachMotionSensor() {
        if (this.motionListening) return;
        window.addEventListener('devicemotion', this.handleMotionEvent);
        this.motionListening = true;
        const status = document.getElementById('motionSensorStatus');
        if (status) status.textContent = 'Automatic monitoring is active. Fall alerts require a free-fall followed by a strong impact.';
    }

    stopMotionSensor() {
        if (!this.motionListening) return;
        window.removeEventListener('devicemotion', this.handleMotionEvent);
        this.motionListening = false;
        this.lastFreefallAt = null;
    }

    handleMotion(event) {
        const accel = event.accelerationIncludingGravity;
        if (!accel) return;
        if (!this.motionDataReceived) {
            this.motionDataReceived = true;
            const status = document.getElementById('motionSensorStatus');
            if (status) status.textContent = 'Motion sensor is receiving data. Small movements are ignored; alerts require a free-fall and strong impact pattern.';
        }

        const x = accel.x || 0;
        const y = accel.y || 0;
        const z = accel.z || 0;
        const magnitude = Math.sqrt(x*x + y*y + z*z);
        const now = Date.now();

        if (magnitude < 4.5) {
            this.lastFreefallAt = now;
        } else if (magnitude > FALL_IMPACT_THRESHOLD && this.lastFreefallAt !== null && now - this.lastFreefallAt <= 1200) {
            this.lastFreefallAt = null;
            if (this.lastFallDetectedAt !== null && now - this.lastFallDetectedAt < 30000) return;
            this.lastFallDetectedAt = now;
            console.warn('Possible high-impact fall pattern detected. Magnitude:', magnitude);
            this.promptFallAlert();
        }
        if (this.lastFreefallAt !== null && now - this.lastFreefallAt > 1200) {
            this.lastFreefallAt = null;
        }
    }

    // Fall alert prompt with visible countdown
    promptFallAlert() {
        if (this.fallCountdownInterval) return; // Already prompting

        const modalEl = document.getElementById('fallAlertModal');
        if (!modalEl) {
            console.error('Fall alert UI is missing; cannot safely show the cancellation prompt.');
            return;
        }

        const modal = new bootstrap.Modal(modalEl);
        modal.show();
        this.startAlertSignal();

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
        this.stopAlertSignal();
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
