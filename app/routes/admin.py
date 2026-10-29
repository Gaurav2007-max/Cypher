from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.extensions import db
from app.models.user import User
from app.models.city import City
from app.models.destination import Destination, Story
from app.models.activity import Activity, CuisineItem
from app.models.feedback import FeedbackReport
from app.models.audit import AuditLog
from app.auth_utils import role_required, get_current_user
from app.services.audit_service import AuditService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


CONTENT_MODELS = {
    'destinations': Destination,
    'stories': Story,
    'activities': Activity,
    'cuisine': CuisineItem
}


@admin_bp.route('/content/<kind>', methods=['GET', 'POST'])
@role_required('admin')
def manage_content(kind):
    model = CONTENT_MODELS.get(kind)
    if model is None:
        return jsonify({'error': 'Unknown content type.'}), 404

    if request.method == 'POST':
        current = get_current_user()
        item_id = request.form.get('id', type=int)
        item = model.query.get(item_id) if item_id else model()
        if item_id and not item:
            return jsonify({'error': 'Content item not found.'}), 404
        try:
            if kind == 'destinations':
                city_id = int(request.form.get('city_id', ''))
                latitude, longitude = float(request.form.get('latitude', '')), float(request.form.get('longitude', ''))
                if not City.query.get(city_id) or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    raise ValueError('Select a valid city and coordinate pair.')
                item.city_id = city_id
                item.name = request.form.get('name', '').strip()
                item.category = request.form.get('category', 'heritage').strip()
                item.description = request.form.get('description', '').strip()
                item.latitude, item.longitude = latitude, longitude
                item.image_url = request.form.get('image_url', '').strip() or None
                item.historical_significance = request.form.get('historical_significance', '').strip() or None
                item.opening_hours = request.form.get('opening_hours', '').strip() or None
                item.accessibility_info = request.form.get('accessibility_info', '').strip() or None
                item.source_attribution = request.form.get('source_attribution', '').strip() or 'Unverified sample data'
                item.is_hidden_gem = request.form.get('is_hidden_gem') == 'on'
            elif kind == 'stories':
                destination_id = int(request.form.get('destination_id', ''))
                if not Destination.query.get(destination_id):
                    raise ValueError('Select a valid destination.')
                item.destination_id = destination_id
                item.title = request.form.get('title', '').strip()
                item.content = request.form.get('content', '').strip()
                item.audio_text = request.form.get('audio_text', '').strip() or None
                item.language = request.form.get('language', 'en').strip()
                item.image_url = request.form.get('image_url', '').strip() or None
            elif kind == 'activities':
                city_id = int(request.form.get('city_id', ''))
                destination_id = request.form.get('destination_id', type=int)
                if not City.query.get(city_id) or (destination_id and not Destination.query.get(destination_id)):
                    raise ValueError('Select a valid city and optional destination.')
                item.city_id = city_id
                item.destination_id = destination_id or None
                item.name = request.form.get('name', '').strip()
                item.category = request.form.get('category', 'experience').strip()
                item.description = request.form.get('description', '').strip()
                item.price_range = request.form.get('price_range', 'Unverified').strip()
                item.typical_duration = request.form.get('typical_duration', '').strip()
                item.recommended_time = request.form.get('recommended_time', '').strip()
                item.safety_precautions = request.form.get('safety_precautions', '').strip() or None
                item.price_source = request.form.get('price_source', 'Sample data; verify locally').strip()
            else:
                city_id = int(request.form.get('city_id', ''))
                if not City.query.get(city_id):
                    raise ValueError('Select a valid city.')
                item.city_id = city_id
                item.name = request.form.get('name', '').strip()
                item.description = request.form.get('description', '').strip()
                item.cultural_background = request.form.get('cultural_background', '').strip() or None
                item.dietary_tags = request.form.get('dietary_tags', '').strip()
                item.allergen_info = request.form.get('allergen_info', 'Not verified; ask the vendor').strip()
                item.price_range = request.form.get('price_range', 'Unverified').strip()
                item.famous_spots = request.form.get('famous_spots', '').strip() or None
                item.image_url = request.form.get('image_url', '').strip() or None
                item.verified_status = request.form.get('verified_status', 'sample')
                rating = request.form.get('user_rating', '').strip()
                item.user_rating = float(rating) if rating else None
                if item.user_rating is not None and not 0 <= item.user_rating <= 5:
                    raise ValueError('Rating must be between 0 and 5.')
            if not getattr(item, 'name', getattr(item, 'title', '')).strip() and kind != 'stories':
                raise ValueError('A name is required.')
            if kind == 'stories' and (not item.title or not item.content):
                raise ValueError('Story title and content are required.')
            if kind == 'destinations' and not item.description:
                raise ValueError('Destination description is required.')
            if kind == 'activities' and not item.description:
                raise ValueError('Activity description is required.')
            if kind == 'cuisine' and not item.description:
                raise ValueError('Cuisine description is required.')
        except (TypeError, ValueError) as error:
            flash(str(error), 'danger')
            return redirect(url_for('admin.manage_content', kind=kind, id=item_id) if item_id else url_for('admin.manage_content', kind=kind))

        db.session.add(item)
        db.session.commit()
        AuditService.log(
            action=f'{kind}_{"updated" if item_id else "created"}',
            user_id=current.id,
            entity_type=kind,
            entity_id=item.id,
            details={'name': getattr(item, 'name', getattr(item, 'title', ''))}
        )
        flash('Content saved.', 'success')
        return redirect(url_for('admin.manage_content', kind=kind))

    items = model.query.order_by(model.id.desc()).all()
    item_id = request.args.get('id', type=int)
    selected = model.query.get(item_id) if item_id else None
    return render_template(
        'admin/content.html',
        kind=kind,
        items=items,
        item=selected,
        cities=City.query.order_by(City.name.asc()).all(),
        destinations=Destination.query.order_by(Destination.name.asc()).all(),
        user=get_current_user()
    )


@admin_bp.route('/content/<kind>/<int:item_id>/toggle', methods=['POST'])
@role_required('admin')
def toggle_content(kind, item_id):
    model = CONTENT_MODELS.get(kind)
    if model is None:
        return jsonify({'error': 'Unknown content type.'}), 404
    item = model.query.get_or_404(item_id)
    item.is_active = not item.is_active
    db.session.commit()
    current = get_current_user()
    AuditService.log(
        action=f'{kind}_{"activated" if item.is_active else "deactivated"}',
        user_id=current.id,
        entity_type=kind,
        entity_id=item.id
    )
    flash('Content visibility updated.', 'success')
    return redirect(url_for('admin.manage_content', kind=kind))


@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    user = get_current_user()
    
    # Counts
    total_users = User.query.count()
    tourists_count = User.query.filter_by(role='tourist').count()
    authorities_count = User.query.filter_by(role='authority').count()
    pending_authorities = User.query.filter_by(role='authority', authority_approved=False).all()
    destinations_count = Destination.query.count()
    pending_feedbacks = FeedbackReport.query.filter_by(status='pending').all()

    # Lists
    all_users = User.query.order_by(User.created_at.desc()).limit(25).all()
    all_destinations = Destination.query.order_by(Destination.city_id, Destination.name).all()
    cities = City.query.all()
    audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(30).all()

    return render_template(
        'admin/dashboard.html',
        user=user,
        total_users=total_users,
        tourists_count=tourists_count,
        authorities_count=authorities_count,
        pending_authorities=pending_authorities,
        destinations_count=destinations_count,
        pending_feedbacks=pending_feedbacks,
        all_users=all_users,
        all_destinations=all_destinations,
        cities=cities,
        audit_logs=audit_logs
    )

@admin_bp.route('/approve-authority/<int:user_id>', methods=['POST'])
@role_required('admin')
def approve_authority(user_id):
    current = get_current_user()
    target_user = User.query.get_or_404(user_id)
    target_user.authority_approved = True
    db.session.commit()

    AuditService.log('authority_approved', user_id=current.id, entity_type='user', entity_id=target_user.id, details={'username': target_user.username})
    flash(f"Authority access approved for '{target_user.username}'.", 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/revoke-authority/<int:user_id>', methods=['POST'])
@role_required('admin')
def revoke_authority(user_id):
    current = get_current_user()
    target_user = User.query.get_or_404(user_id)
    target_user.authority_approved = False
    db.session.commit()

    AuditService.log('authority_revoked', user_id=current.id, entity_type='user', entity_id=target_user.id, details={'username': target_user.username})
    flash(f"Authority access revoked for '{target_user.username}'.", 'warning')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/reject-authority/<int:user_id>', methods=['POST'])
@role_required('admin')
def reject_authority(user_id):
    current = get_current_user()
    target_user = User.query.get_or_404(user_id)
    if target_user.role != 'authority' or target_user.authority_approved:
        flash('Only pending authority applications can be declined.', 'danger')
        return redirect(url_for('admin.dashboard'))

    target_user.is_active = False
    db.session.commit()

    AuditService.log('authority_application_rejected', user_id=current.id, entity_type='user', entity_id=target_user.id, details={'username': target_user.username})
    flash(f"Authority application for '{target_user.username}' has been declined and the account deactivated.", 'warning')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/toggle-user-status/<int:user_id>', methods=['POST'])
@role_required('admin')
def toggle_user_status(user_id):
    current = get_current_user()
    target_user = User.query.get_or_404(user_id)
    if target_user.id == current.id:
        flash("You cannot deactivate your own admin account.", 'danger')
        return redirect(url_for('admin.dashboard'))

    target_user.is_active = not target_user.is_active
    db.session.commit()

    status_str = "activated" if target_user.is_active else "deactivated"
    AuditService.log(f'user_{status_str}', user_id=current.id, entity_type='user', entity_id=target_user.id, details={'username': target_user.username})
    flash(f"User '{target_user.username}' has been {status_str}.", 'info')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/verify-destination/<int:dest_id>', methods=['POST'])
@role_required('admin')
def verify_destination(dest_id):
    current = get_current_user()
    dest = Destination.query.get_or_404(dest_id)
    dest.last_verified_at = datetime.utcnow()
    dest.source_attribution = request.form.get('source_attribution', dest.source_attribution)
    db.session.commit()

    AuditService.log('destination_verified', user_id=current.id, entity_type='destination', entity_id=dest.id, details={'destination': dest.name})
    flash(f"Destination '{dest.name}' data marked as verified today.", 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/resolve-feedback/<int:report_id>', methods=['POST'])
@role_required('admin')
def resolve_feedback(report_id):
    current = get_current_user()
    report = FeedbackReport.query.get_or_404(report_id)
    status = request.form.get('status', 'resolved')
    notes = request.form.get('admin_notes', '').strip()

    report.status = status
    report.admin_notes = notes
    report.reviewed_by_id = current.id
    report.reviewed_at = datetime.utcnow()
    db.session.commit()

    AuditService.log('feedback_updated', user_id=current.id, entity_type='feedback', entity_id=report.id, details={'status': status, 'notes': notes})
    flash(f"Feedback report #{report.id} marked as {status}.", 'success')
    return redirect(url_for('admin.dashboard'))
