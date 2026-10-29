from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.extensions import db
from app.models.city import City
from app.models.destination import Destination
from app.models.crowd import CrowdStatusRecord
from app.models.feedback import FeedbackReport
from app.auth_utils import role_required, get_current_user
from app.services.crowd_service import CrowdService
from app.services.audit_service import AuditService

authority_bp = Blueprint('authority', __name__, url_prefix='/authority')

@authority_bp.route('/dashboard')
@role_required('authority')
def dashboard():
    user = get_current_user()
    CrowdService.check_and_expire_alerts()

    search_query = request.args.get('q', '').strip()
    city_filter = request.args.get('city_id', type=int)

    dest_query = Destination.query.filter_by(is_active=True)
    if city_filter:
        dest_query = dest_query.filter_by(city_id=city_filter)
    if search_query:
        dest_query = dest_query.filter(Destination.name.ilike(f'%{search_query}%'))

    destinations = dest_query.order_by(Destination.name.asc()).all()
    cities = City.query.filter_by(is_active=True).all()

    # Active alerts
    active_alerts = Destination.query.filter(
        Destination.crowd_status.in_(['Crowded', 'Overcrowded'])
    ).order_by(Destination.crowd_updated_at.desc()).all()

    # Recent crowd history
    recent_history = CrowdStatusRecord.query.order_by(CrowdStatusRecord.created_at.desc()).limit(20).all()

    # Relevant tourist feedback reports
    feedback_reports = FeedbackReport.query.filter(
        FeedbackReport.status.in_(['pending', 'reviewed'])
    ).order_by(FeedbackReport.created_at.desc()).limit(15).all()

    return render_template(
        'authority/dashboard.html',
        user=user,
        destinations=destinations,
        cities=cities,
        active_alerts=active_alerts,
        recent_history=recent_history,
        feedback_reports=feedback_reports,
        search_query=search_query,
        city_filter=city_filter
    )

@authority_bp.route('/update-crowd', methods=['POST'])
@role_required('authority')
def update_crowd():
    user = get_current_user()
    dest_id = request.form.get('destination_id', type=int)
    new_status = request.form.get('status', 'Normal')
    duration_minutes = request.form.get('duration_minutes', type=int) or 120
    explanation = request.form.get('explanation', '').strip()

    valid_statuses = ['Normal', 'Moderate', 'Crowded', 'Overcrowded']
    if new_status not in valid_statuses:
        flash('Invalid crowd status selected.', 'danger')
        return redirect(url_for('authority.dashboard'))

    dest = Destination.query.get(dest_id)
    if not dest:
        flash('Destination not found.', 'danger')
        return redirect(url_for('authority.dashboard'))

    prev_status = dest.crowd_status
    dest.crowd_status = new_status
    dest.crowd_explanation = explanation
    dest.crowd_updated_at = datetime.utcnow()
    dest.crowd_updated_by_id = user.id

    if new_status in ['Crowded', 'Overcrowded'] and duration_minutes > 0:
        dest.crowd_expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
    else:
        dest.crowd_expires_at = None

    # Record history
    history_record = CrowdStatusRecord(
        destination_id=dest.id,
        status=new_status,
        previous_status=prev_status,
        duration_minutes=duration_minutes if new_status in ['Crowded', 'Overcrowded'] else 0,
        explanation=explanation,
        expires_at=dest.crowd_expires_at,
        updated_by_id=user.id
    )
    db.session.add(history_record)
    db.session.commit()

    # If cleared back to Normal/Moderate, notify subscribers
    if new_status in ['Normal', 'Moderate'] and prev_status in ['Crowded', 'Overcrowded']:
        CrowdService.notify_subscribers(dest.id, f"Good news! {dest.name} crowd status has returned to {new_status}.")

    AuditService.log(
        action='crowd_status_update',
        user_id=user.id,
        entity_type='destination',
        entity_id=dest.id,
        details={
            'destination': dest.name,
            'previous_status': prev_status,
            'new_status': new_status,
            'duration_minutes': duration_minutes,
            'explanation': explanation
        }
    )

    flash(f"Crowd status for '{dest.name}' successfully updated to {new_status}.", 'success')
    return redirect(url_for('authority.dashboard'))

@authority_bp.route('/clear-alert/<int:dest_id>', methods=['POST'])
@role_required('authority')
def clear_alert(dest_id):
    user = get_current_user()
    dest = Destination.query.get_or_404(dest_id)
    prev_status = dest.crowd_status

    dest.crowd_status = 'Normal'
    dest.crowd_explanation = 'Alert cleared by authority.'
    dest.crowd_expires_at = None
    dest.crowd_updated_at = datetime.utcnow()
    dest.crowd_updated_by_id = user.id

    history_record = CrowdStatusRecord(
        destination_id=dest.id,
        status='Normal',
        previous_status=prev_status,
        duration_minutes=0,
        explanation='Alert cleared manually by authority',
        expires_at=None,
        updated_by_id=user.id
    )
    db.session.add(history_record)
    db.session.commit()

    CrowdService.notify_subscribers(dest.id, f"{dest.name} crowd status has normalized back to Normal.")

    AuditService.log(
        action='crowd_alert_cleared',
        user_id=user.id,
        entity_type='destination',
        entity_id=dest.id,
        details={'destination': dest.name, 'previous_status': prev_status}
    )

    flash(f"Crowd alert for '{dest.name}' has been cleared.", 'info')
    return redirect(url_for('authority.dashboard'))

