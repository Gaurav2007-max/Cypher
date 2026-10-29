# TravelTech — Smart Cultural Exploration & Tourist Safety Platform

A full-stack, responsive web application engineered in Python with Flask that enhances tourism through location-aware cultural storytelling, dynamic crowd management, hidden-gem discovery, regional cuisine exploration, transparent transport information, and a comprehensive tourist safety & emergency response system.

---

## 🌟 Key Features

### 1. Modern, Highly Visual, Mobile-First Interface
- Minimal prose, maximum high-resolution travel photography, and dynamic micro-animations (floating travel icons, radar SOS pulse, audio equalizer bars).
- Uses a consistent olive-green interface across all cities and pages, while emergency SOS controls retain a distinct red safety color.
- Destination photos are matched to their subject, with source attribution shown for the Faridabad palace hero image.
- Responsive mobile bottom navigation bar designed for quick single-hand thumb navigation while walking.

### 2. Location & Dynamic City Switching
- **Showcase City:** **Faridabad (Haryana)**, alongside **Shimla**, **Agra**, **Jaipur**, and **Varanasi**.
- Distinguishes **physical location** (detected via Geolocation API) from **virtual exploration mode** (allowing travelers to preview destinations anywhere).
- Explains why location is needed before prompting; graceful manual fallback when GPS is denied.

### 3. Location-Aware Cultural Storytelling
- Proximity engine detects when a tourist is within configurable proximity radius (configurable 10m to 200m; default 50m).
- Displays monument photo prompt to prevent confusion from GPS drift.
- **Web Speech API Text-to-Speech:** Listen to authentic cultural stories with Play, Pause, Resume, and Stop controls, adjustable playback speed, and animated audio equalizer waveform.
- Proximity demo simulation buttons allowing instant evaluation without having to walk outside.

### 4. Dynamic Crowd Management & Smart Recommendations
- Role-enforced Authority control room to set crowd levels: `Normal`, `Moderate`, `Crowded`, and `Overcrowded`.
- Configurable alert duration with automatic expiry.
- **Dynamic Alternative Recommendation Algorithm:**
  - When an attraction is Crowded or Overcrowded, automatically computes less-congested alternatives (`Normal` or `Moderate`).
  - Calculates straight-line distance and estimated travel times, and labels authority-entered crowd reports and listed hours as not live-verified.
  - Excludes alternatives that are themselves overcrowded or closed.
  - Allows tourists to subscribe to in-app notifications when crowd levels return to Normal.

### 5. Tourist Safety & Emergency Response
- **Emergency Contacts:** Supports personal emergency contacts as well as International Travel Assistance Agencies / Consulate Desks for foreign tourists.
- **Manual SOS:** Stores a server-side pending action with a 30-second cancellation window, so dispatch is not controlled by a browser timer. The worker records an incident and attempts SMTP delivery after the deadline; incident recording and email delivery are reported separately. Live SMTP requires an explicitly verified emergency-contact email.
- **Potential Fall & Impact Detection:** Enabling saved location and motion consent in Settings automatically starts monitoring across TravelTech pages after browser permissions are granted; the Safety Center retains controls to resume or stop it on the device. The conservative heuristic ignores small jolts and only prompts after a near-free-fall signal followed by a strong impact; it is not medical or guaranteed fall detection. Browsers and operating systems may pause sensor/location events when the tab is hidden, the browser is closed, or the phone is locked, so background monitoring is best-effort and cannot run with the phone powered off. Once an SOS is queued, its countdown and dispatch continue server-side.
- **10-Minute Rolling Location History Trail:** Requires saved location consent and the explicit Safety Center monitoring action. Samples older than 10 minutes are automatically purged; opting out deletes stored samples. Coordinates are snapshotted into incident records when a queued alert is processed.
- **Safety Check-in Timer:** Supports minute-based timers. On expiry, the app provides a 15-second response period and then a 30-second server-side cancellation period before queuing the alert. Users can confirm safety during either period.
- **Privacy First:** Explicit opt-in switches, coordinates never exposed to other tourists, zero credential leaks.

### 6. Curated Activities, Authentic Cuisine & Transit
- Filter local delicacies by dietary requirements: `Vegetarian`, `Gluten-Free`, `Street Food`.
- Sample heritage walks, crafts workshops, cuisine, and transport information with verification caveats; confirm prices, allergens, hours, and schedules locally.
- Route requests label OSRM-provided routes separately from estimated fallbacks. Transit routing is unavailable until a transit provider is configured.

### 7. User Roles & Strict Backend RBAC
- **Tourist:** Register, explore, virtual city switch, save places/stories, check-in timer, SOS, submit feedback.
- **Authority:** Search destinations, update crowd status with expiry timers, review tourist reports. Accounts require administrator verification before activation.
- **Administrator:** User governance, approve/revoke authority accounts, manage destinations, stories, activities and cuisine, destination verification, review feedback reports, and inspect system audit logs.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.13+, Flask 3.0.2 |
| **Database** | SQLite3 with SQLAlchemy 2.0+ (Flask-SQLAlchemy) |
| **Authentication** | Secure session cookies (`HttpOnly`, `SameSite=Lax`), Werkzeug password hashing |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons |
| **Interactive Maps** | Leaflet.js with OpenStreetMap raster tiles & OSRM routing engine |
| **Audio / TTS** | HTML5 Web Speech API (`SpeechSynthesis`) |
| **Sensors** | Browser Geolocation API, DeviceMotionEvent |
| **Testing** | pytest 8.4.2 |

---

## 🚀 Quickstart Guide

### 1. Clone & Set Up Environment
```bash
# Navigate to the project directory
cd "c:\Users\Gaurav\Desktop\Cypher 2.0"

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env` (optional, sane defaults are configured in `config.py`):
```bash
copy .env.example .env
```
Relative SQLite paths in `DATABASE_URI` are resolved from the project root, so `sqlite:///traveltech.db` uses the included database file.
Interactive and safety maps use OpenStreetMap tiles and do not require a map API key or `.env` setting.
> **Note on Email / SMTP:** `SMTP_TEST_MODE=True` records SOS incidents but does not send email. For live delivery, set `SMTP_TEST_MODE=False` and configure `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USE_TLS`, `SMTP_USERNAME`, and `SMTP_PASSWORD` in your local `.env`, then restart Flask so it reloads settings. Use a valid sender address (or leave `SMTP_DEFAULT_SENDER` unset to send from `SMTP_USERNAME`). Never commit or share SMTP credentials. A live SOS delivery should be verified with a consenting test recipient before relying on it in an emergency.

### 3. Initialize & Seed Database
Populate the database with rich, realistic sample destinations, stories, cuisines, transport options, and demo accounts:
```bash
python seed_data.py
```

### 4. Create an Administrator (Optional CLI Tool)
```bash
python create_admin.py --username admin --email admin@traveltech.gov.in --password "replace-with-a-unique-strong-password"
```

### 5. Run the Application
```bash
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

### Deploy to Render
1. Create a Render PostgreSQL database and link it to the web service. Render provides `DATABASE_URL`; the app converts it to the installed psycopg driver automatically.
2. Set `SECRET_KEY` to a generated random value and `FLASK_DEBUG=0` in the service environment. Do not copy the development `.env` into Render.
3. Use build command `pip install -r requirements.txt`.
4. Use start command `SEED_DEMO_USERS=false python seed_data.py && gunicorn --workers 1 --threads 4 run:app`. The seed step adds sample travel content only when the database is empty, excludes the published local demo accounts, and skips safely on later restarts.
5. Optionally set Render's health check path to `/health`.

The single Gunicorn worker is intentional while the safety dispatcher runs in-process. This is suitable for a demo, not a production emergency-response service; production use needs a separately operated durable worker/queue and monitoring.

### Request Protection
All state-changing form and JSON requests require a session CSRF token. The app applies per-IP rate limits to every endpoint, with tighter limits on sign-in, registration, feedback, routing, and safety actions. Limits use in-memory storage by default, which is suitable for local development or a single process only. For multiple workers or instances, set `RATELIMIT_STORAGE_URI` to a shared Redis URL so limits are consistent across processes.

---

## 🔑 Demo Accounts for Evaluation

| Role | Username | Password | Notes |
|---|---|---|---|
| **Tourist** | `alex_traveler` | `tourist123` | Faridabad profile and emergency contact; safety consents start off |
| **Authority** | `officer_sharma` | `authority123` | Approved Haryana Tourism Officer; crowd status manager |
| **Authority (Pending)** | `officer_verma` | `authority123` | Demonstrates administrator approval workflow |
| **Administrator** | `admin` | `admin123` | Superadmin console with audit logs and role controls |

> **Tip:** The Login page includes **one-click demo login buttons** that sign in as the selected role during presentations.
> Demo accounts and their published passwords are for local evaluation only. Never seed this demo database or use these accounts in a public deployment; create a unique administrator account instead.

### Keeping Secrets Out of Git
`.env`, SQLite databases, and runtime uploads are excluded by `.gitignore`. Copy `.env.example` to `.env` for local development and provide production credentials through your hosting provider's secret environment variables. Treat any credential that has appeared in a shared workspace or chat as exposed and rotate it before deployment.

---

## 🧪 Automated Test Suite

A complete automated test suite covers authentication, RBAC, crowd status expiry, recommendations, safety alert queueing, consent, contact verification, privacy boundaries, and location pruning:

```bash
python -m pytest -v
```

The automated tests verify:
- ✅ Tourist registration & authority pending-approval logic
- ✅ Session-based authentication & credential protection
- ✅ RBAC: Unauthorized tourists cannot access authority dashboard (403 Forbidden)
- ✅ RBAC: Unapproved authorities cannot dispatch crowd alerts
- ✅ Administrator approvals & user status toggling
- ✅ Crowd status updates & audit trail logging
- ✅ Automatic alert expiry after duration elapses
- ✅ Dynamic recommendation engine calculates distance/time and rejects overcrowded alternatives
- ✅ Server-side 30-second SOS dispatch, cancellation, and safe test mode logging
- ✅ Verified-contact gate for live SMTP and explicit verification confirmation
- ✅ Check-in expiry escalation, confirmation cancellation, and status checks
- ✅ Rolling 10-minute location sample posting and automatic purging of stale records
- ✅ Saved location consent and private feedback/notification listing
- ✅ Proximity stories, inactive content visibility, and admin content management
- ✅ Estimated transit fallback when no transit provider is configured

---

## 📂 Project Directory Structure

```
Cypher 2.0/
├── app/
│   ├── __init__.py              # Flask app factory, blueprints, error handlers
│   ├── config.py                # Environment & application configurations
│   ├── extensions.py            # Shared database, CSRF, and rate-limit extensions
│   ├── auth_utils.py            # RBAC decorators (@login_required, @role_required)
│   ├── models/
│   │   ├── __init__.py          # Exported model registry
│   │   ├── user.py              # User, UserProfile, EmergencyContact
│   │   ├── city.py              # City (Faridabad, Shimla, Agra, Jaipur, Varanasi)
│   │   ├── destination.py       # Destination, Story, SavedDestination, SavedStory
│   │   ├── crowd.py             # CrowdStatusRecord, CrowdSubscription
│   │   ├── activity.py          # Activity, CuisineItem
│   │   ├── transport.py         # TransportOption
│   │   ├── safety.py            # PendingSafetyAction, CheckInSession, incidents, location
│   │   ├── feedback.py          # FeedbackReport
│   │   └── audit.py             # AuditLog
│   ├── routes/
│   │   ├── auth.py              # /login, /register, /logout, /profile
│   │   ├── tourist.py           # /dashboard, /saved, /safety
│   │   ├── authority.py         # /authority/dashboard, /update-crowd, /clear-alert
│   │   ├── admin.py             # /admin/dashboard, user management, feedback moderation
│   │   ├── api_destinations.py  # /api/destinations, recommendations, proximity stories
│   │   ├── api_safety.py        # Pending SOS, check-in, consent-checked location history
│   │   ├── api_feedback.py      # /api/feedback/submit, /list
│   │   └── api_routes.py        # /api/routes/calculate (OSRM / estimated model)
│   ├── services/
│   │   ├── email_service.py     # SMTP emergency/verification mail with safe Test Mode
│   │   ├── safety_dispatch.py   # Database-backed pending-action dispatcher
│   │   ├── crowd_service.py     # Expiry checker, recommendation scoring & rationale
│   │   └── audit_service.py     # System audit trail recorder
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css        # Animations, crowd badges, audio equalizer, SOS radar
│   │   └── js/
│   │       ├── tts.js           # Web Speech API audio player with waveform visualizer
│   │       ├── safety.js        # Geolocation, SOS transmitter, fall sensor, check-in
│   │       ├── map.js           # Leaflet map pins, crowd layers, routing polyline
│   │       └── tourist.js       # Dynamic filters, alternatives modal, save toggles
│   └── templates/
│       ├── base.html            # Core layout with mobile bottom bar & floating SOS
│       ├── auth/
│       │   ├── login.html       # Visual login with 1-click demo role buttons
│       │   ├── register.html    # Registration with agency contacts & role toggle
│       │   ├── pending_approval.html
│       │   ├── 403.html
│       │   ├── 404.html
│       │   └── 500.html
│       ├── tourist/
│       │   ├── dashboard.html   # Main rich visual dashboard with map, food, transit
│       │   ├── safety.html      # Dedicated Safety Center (SOS, Trail map, Checkin)
│       │   ├── saved.html       # Saved places and offline stories
│       │   └── profile.html     # Audio speech rate, proximity radius, emergency info
│       ├── authority/
│       │   └── dashboard.html   # Authority crowd alert command room
│       └── admin/
│       ├── dashboard.html   # Administrator governance & moderation console
│       └── content.html    # Destination/story/activity/cuisine editor
├── tests/
│   ├── test_auth.py             # Authentication & RBAC test suite
│   ├── test_crowd.py            # Crowd updates, expiry & smart alternatives tests
│   ├── test_safety.py           # SOS dispatch, check-in & location trail tests
│   └── test_destinations_and_feedback.py # City switching & feedback tests
├── seed_data.py                 # Comprehensive database seeder
├── create_admin.py              # CLI administrator generator
├── requirements.txt             # Project dependencies
├── .env.example                 # Environment configuration template
└── run.py                       # Development server runner
```

---

## 🔒 Security & Privacy Guarantees

1. **Role Enforcement on Every Operation:** Authority operations (`/authority/update-crowd`, `/clear-alert`) and Admin routes (`/admin/*`) strictly verify server-side session credentials via `@role_required`. Client-side tampering is completely blocked.
2. **Request Protection:** Unsafe requests require a session CSRF token. Per-IP request limits apply globally, with stricter thresholds for authentication, feedback, route calculation, and safety actions; configure shared Redis storage for multi-worker deployments.
3. **Data Minimization:** Rolling location history samples are automatically purged beyond the 10-minute retention window during normal tracking.
4. **Emergency Transparency:** Location-history samples require saved consent and an explicit GPS action. A one-time fix may be requested after a user explicitly starts SOS. Manual SOS alerts wait 30 seconds; unattended check-ins wait for the user response window and another 30 seconds. Coordinates are never exposed to other tourists.
5. **Emergency Email Verification:** Live alerts are not sent to unverified contacts. Test mode records incidents but never sends email. SMTP acceptance does not guarantee delivery to the recipient's inbox.
6. **Dispatcher Scope:** Pending actions are stored in the database and processed by a daemon thread in the Flask process, so browser closure does not cancel them. Pending rows survive an application restart, but a process crash during SMTP dispatch can leave an action requiring manual recovery; this is not a multi-worker durable task queue. Use a dedicated worker/service for production.
7. **Safe Fallbacks:** The platform operates without external SMTP credentials in safe Test Mode or when GPS permissions are withheld, using Virtual Exploration Mode.
