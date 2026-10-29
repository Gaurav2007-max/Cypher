// TravelTech Web Speech API Text-to-Speech Engine with Audio Visualizer

class TravelTTS {
    constructor() {
        this.synth = window.speechSynthesis;
        this.currentUtterance = null;
        this.isPlaying = false;
        this.isPaused = false;
        this.speechRate = 1.0;
        this.activeCardId = null;
    }

    setSpeechRate(rate) {
        this.speechRate = parseFloat(rate) || 1.0;
    }

    speak(text, title = 'Audio Story', targetElementId = null) {
        if (!('speechSynthesis' in window)) {
            alert('Text-to-Speech is not supported in this browser. Please read the story text.');
            return;
        }

        // If currently speaking this same element, toggle pause/resume
        if (this.isPlaying && this.activeCardId === targetElementId) {
            if (this.isPaused) {
                this.resume();
            } else {
                this.pause();
            }
            return;
        }

        // Cancel previous speech
        this.stop();

        this.currentUtterance = new SpeechSynthesisUtterance(text);
        this.currentUtterance.rate = this.speechRate;
        this.currentUtterance.pitch = 1.0;
        this.currentUtterance.lang = 'en-IN'; // Indian English voice preferred for local cultural authenticity

        // Find best voice
        const voices = this.synth.getVoices();
        const preferredVoice = voices.find(v => v.lang.includes('en-IN') || v.name.includes('India')) ||
                               voices.find(v => v.lang.startsWith('en'));
        if (preferredVoice) {
            this.currentUtterance.voice = preferredVoice;
        }

        this.activeCardId = targetElementId;

        this.currentUtterance.onstart = () => {
            this.isPlaying = true;
            this.isPaused = false;
            this.updatePlayerUI(true, false);
            this.showFloatingPlayer(title);
        };

        this.currentUtterance.onend = () => {
            this.reset();
        };

        this.currentUtterance.onerror = (e) => {
            console.error('Speech synthesis error:', e);
            this.reset();
        };

        this.synth.speak(this.currentUtterance);
    }

    pause() {
        if (this.synth.speaking && !this.isPaused) {
            this.synth.pause();
            this.isPaused = true;
            this.updatePlayerUI(true, true);
        }
    }

    resume() {
        if (this.synth.speaking && this.isPaused) {
            this.synth.resume();
            this.isPaused = false;
            this.updatePlayerUI(true, false);
        }
    }

    togglePlayback() {
        if (this.isPaused) {
            this.resume();
        } else {
            this.pause();
        }
    }

    stop() {
        if (this.synth) {
            this.synth.cancel();
        }
        this.reset();
    }

    reset() {
        this.isPlaying = false;
        this.isPaused = false;
        this.updatePlayerUI(false, false);
        this.hideFloatingPlayer();
        this.activeCardId = null;
    }

    updatePlayerUI(playing, paused) {
        document.querySelectorAll('.audio-visualizer').forEach(el => {
            if (playing && !paused) {
                el.classList.add('audio-playing');
            } else {
                el.classList.remove('audio-playing');
            }
        });

        // Update play/pause buttons
        if (this.activeCardId) {
            const btn = document.getElementById(`btn-audio-${this.activeCardId}`);
            if (btn) {
                const icon = btn.querySelector('i');
                if (icon) {
                    icon.className = (!playing || paused) ? 'bi bi-play-fill' : 'bi bi-pause-fill';
                }
            }

        }

        const floatingToggle = document.querySelector('#floatingAudioBar [onclick*="togglePlayback"]');
        if (floatingToggle) {
            const icon = floatingToggle.querySelector('i');
            if (icon) {
                icon.className = playing && !paused ? 'bi bi-pause-fill' : 'bi bi-play-fill';
            }
            const label = playing && !paused ? 'Pause story audio' : 'Resume story audio';
            floatingToggle.setAttribute('aria-label', label);
            floatingToggle.title = label;
        }
    }

    showFloatingPlayer(title) {
        let player = document.getElementById('floatingAudioBar');
        if (!player) return;
        document.getElementById('floatingAudioTitle').innerText = title;
        player.classList.remove('d-none');
    }

    hideFloatingPlayer() {
        let player = document.getElementById('floatingAudioBar');
        if (player) player.classList.add('d-none');
    }
}

window.travelTTS = new TravelTTS();
