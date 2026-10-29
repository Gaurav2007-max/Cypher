from datetime import datetime, timedelta
from hashlib import sha256
import secrets
from email.utils import parseaddr
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.extensions import db
from app.models.user import User, UserProfile, EmergencyContact, EmergencyContactVerification
from app.models.city import City
from app.models.safety import LocationSample
from app.auth_utils import login_required, get_current_user
from app.services.audit_service import AuditService
from app.services.email_service import EmailService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    user = get_current_user()
    if user:
        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'authority':
            return redirect(url_for('authority.dashboard'))
        return redirect(url_for('tourist.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if get_current_user():
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()  # username or email
        password = request.form.get('password', '')

        if not identifier or not password:
            flash('Please enter both username/email and password.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter(
            (User.username.ilike(identifier)) | (User.email.ilike(identifier))
        ).first()

        if not user or not user.check_password(password):
            flash('Invalid login credentials. Please check and try again.', 'danger')
            return render_template('auth/login.html')

        if not user.is_active:
            flash('This account has been deactivated. Please contact support.', 'danger')
            return render_template('auth/login.html')

        # Set session
        session.clear()
        session['user_id'] = user.id
        session['role'] = user.role
        session['username'] = user.username

        AuditService.log('user_login', user_id=user.id, entity_type='user', entity_id=user.id, details={'username': user.username})

        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'authority':
            return redirect(url_for('authority.dashboard'))
        else:
            return redirect(url_for('tourist.dashboard'))

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if get_current_user():
        return redirect(url_for('auth.index'))

    cities = City.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'tourist')
        full_name = request.form.get('full_name', '').strip()
        preferred_city_id = request.form.get('preferred_city_id', type=int)
        
        # Emergency contact fields (for tourists)
        contact_name = request.form.get('contact_name', '').strip()
        contact_email = request.form.get('contact_email', '').strip().lower()
        contact_phone = request.form.get('contact_phone', '').strip()
        contact_rel = request.form.get('contact_relationship', 'Family')
        is_agency = request.form.get('is_agency') == 'on'

        if not username or not email or not password:
            flash('Username, email, and password are required.', 'danger')
            return render_template('auth/register.html', cities=cities)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html', cities=cities)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html', cities=cities)

        if User.query.filter_by(username=username).first():
            flash('That username is already taken. Please choose another.', 'warning')
            return render_template('auth/register.html', cities=cities)

        if User.query.filter_by(email=email).first():
            flash('That email address is already registered.', 'warning')
            return render_template('auth/register.html', cities=cities)

        # Enforce role logic: Authority requests require admin approval
        requested_role = 'authority' if role == 'authority' else 'tourist'
        authority_approved = False  # Always require admin approval for authority

        new_user = User(
            username=username,
            email=email,
            role=requested_role,
            authority_approved=authority_approved
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        # Create Profile
        profile = UserProfile(
            user_id=new_user.id,
            full_name=full_name or username,
            preferred_city_id=preferred_city_id,
            emergency_consent=False,
            location_tracking_enabled=False,
            proximity_radius_meters=50
        )
        db.session.add(profile)

        # Create Emergency Contact if provided
        if contact_name and contact_email:
            emergency = EmergencyContact(
                user_id=new_user.id,
                name=contact_name,
                email=contact_email,
                phone=contact_phone,
                relationship=contact_rel,
                is_agency=is_agency,
                is_primary=True
            )
            db.session.add(emergency)

        db.session.commit()
        AuditService.log('user_registered', user_id=new_user.id, entity_type='user', entity_id=new_user.id, details={'role': requested_role})

        if requested_role == 'authority':
            flash('Authority account created! An administrator will review and approve your account shortly.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('Account created successfully! Please sign in to begin exploring.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/register.html', cities=cities)

@auth_bp.route('/logout')
def logout():
    user = get_current_user()
    if user:
        AuditService.log('user_logout', user_id=user.id, entity_type='user', entity_id=user.id)
    session.clear()
    flash('You have been signed out safely.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    profile = user.profile
    cities = City.query.filter_by(is_active=True).all()
    primary_contact = EmergencyContact.query.filter_by(user_id=user.id, is_primary=True).first()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        preferred_city_id = request.form.get('preferred_city_id', type=int)
        proximity_radius = request.form.get('proximity_radius', type=int) or 50
        speech_rate = request.form.get('speech_rate', type=float) or 1.0
        emergency_consent = request.form.get('emergency_consent') == 'on'
        sensor_consent = request.form.get('sensor_consent') == 'on'
        location_tracking_enabled = request.form.get('location_tracking_enabled') == 'on'
        auto_story_notifications = request.form.get('auto_story_notifications') == 'on'

        if profile:
            profile.full_name = full_name
            profile.phone = phone
            profile.preferred_city_id = preferred_city_id
            profile.proximity_radius_meters = max(10, min(500, proximity_radius))
            profile.audio_speech_rate = speech_rate
            profile.emergency_consent = emergency_consent
            profile.sensor_consent = sensor_consent
            profile.location_tracking_enabled = location_tracking_enabled
            profile.auto_story_notifications = auto_story_notifications
            if not location_tracking_enabled:
                LocationSample.query.filter_by(user_id=user.id).delete(synchronize_session=False)

        # Emergency Contact update
        contact_name = request.form.get('contact_name', '').strip()
        contact_email = request.form.get('contact_email', '').strip().lower()
        contact_phone = request.form.get('contact_phone', '').strip()
        contact_rel = request.form.get('contact_relationship', 'Family')
        is_agency = request.form.get('is_agency') == 'on'

        if contact_name and contact_email:
            if not parseaddr(contact_email)[1] or parseaddr(contact_email)[1] != contact_email:
                flash('Enter a valid emergency contact email address.', 'danger')
                return render_template('tourist/profile.html', user=user, profile=profile, cities=cities, contact=primary_contact)
            if primary_contact:
                if primary_contact.email != contact_email and primary_contact.verification:
                    db.session.delete(primary_contact.verification)
                primary_contact.name = contact_name
                primary_contact.email = contact_email
                primary_contact.phone = contact_phone
                primary_contact.relationship = contact_rel
                primary_contact.is_agency = is_agency
            else:
                primary_contact = EmergencyContact(
                    user_id=user.id,
                    name=contact_name,
                    email=contact_email,
                    phone=contact_phone,
                    relationship=contact_rel,
                    is_agency=is_agency,
                    is_primary=True
                )
                db.session.add(primary_contact)

        db.session.commit()
        flash('Your profile and safety settings have been updated.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('tourist/profile.html', user=user, profile=profile, cities=cities, contact=primary_contact)


@auth_bp.route('/profile/contact/verification', methods=['POST'])
@login_required
def send_contact_verification():
    user = get_current_user()
    contact = EmergencyContact.query.filter_by(user_id=user.id, is_primary=True).first()
    if not contact:
        flash('Save an emergency contact before requesting email verification.', 'warning')
        return redirect(url_for('auth.profile'))
    if contact.verification and contact.verification.is_verified:
        flash('This emergency contact email is already verified.', 'info')
        return redirect(url_for('auth.profile'))

    token = secrets.token_urlsafe(32)
    verification = contact.verification or EmergencyContactVerification(contact_id=contact.id)
    verification.token_hash = sha256(token.encode('utf-8')).hexdigest()
    verification.expires_at = datetime.utcnow() + timedelta(minutes=30)
    verification.verified_at = None
    db.session.add(verification)
    db.session.commit()

    verification_url = url_for('auth.verify_emergency_contact', token=token, _external=True)
    result = EmailService.send_contact_verification(contact, verification_url)
    if not result['success']:
        verification.token_hash = None
        verification.expires_at = None
        db.session.commit()
        if result['mode'] == 'test_mode':
            flash('Test mode is enabled, so no verification email was sent. Configure live SMTP to verify this contact.', 'warning')
        else:
            flash(f"Could not send verification email: {result.get('error', result['mode'])}", 'danger')
        return redirect(url_for('auth.profile'))

    flash('Verification email sent. The link expires in 30 minutes.', 'success')
    return redirect(url_for('auth.profile'))


@auth_bp.route('/contact/verify/<token>', methods=['GET', 'POST'])
def verify_emergency_contact(token):
    token_hash = sha256(token.encode('utf-8')).hexdigest()
    verification = EmergencyContactVerification.query.filter_by(token_hash=token_hash).first()
    if not verification or not verification.expires_at or verification.expires_at < datetime.utcnow():
        flash('This verification link is invalid or expired. Request a new one from your profile.', 'danger')
        return redirect(url_for('auth.login'))
    if request.method == 'GET':
        return render_template('auth/verify_contact.html', token=token)
    verification.verified_at = datetime.utcnow()
    verification.token_hash = None
    verification.expires_at = None
    db.session.commit()
    flash('Emergency contact email verified. Sign in to review your safety settings.', 'success')
    return redirect(url_for('auth.login'))
