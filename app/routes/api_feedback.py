from flask import Blueprint, request, jsonify
from app.extensions import db
from app.extensions import limiter
from app.models.feedback import FeedbackReport
from app.models.destination import Destination
from app.auth_utils import login_required, get_current_user
from app.services.audit_service import AuditService

api_feedback_bp = Blueprint('api_feedback', __name__, url_prefix='/api/feedback')

@api_feedback_bp.route('/submit', methods=['POST'])
@login_required
@limiter.limit('5 per hour')
def submit_feedback():
    user = get_current_user()
    data = request.get_json() or {}

    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    destination_id = data.get('destination_id')
    feedback_type = data.get('feedback_type', 'general')
    title = data.get('title', '')
    description = data.get('description', '')

    if destination_id is not None:
        try:
            destination_id = int(destination_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'Destination ID must be an integer.'}), 400
        if not Destination.query.filter_by(id=destination_id, is_active=True).first():
            return jsonify({'error': 'Destination was not found.'}), 404
    if not isinstance(feedback_type, str) or feedback_type not in {
        'inaccurate_info', 'outdated_price', 'wrong_hours', 'transport_issue',
        'closed_location', 'safety_concern', 'wrong_story', 'general'
    }:
        return jsonify({'error': 'Unsupported feedback type.'}), 400
    if not isinstance(title, str) or not isinstance(description, str):
        return jsonify({'error': 'Feedback title and description must be text.'}), 400
    title = title.strip()
    description = description.strip()

    if not description:
        return jsonify({'error': 'Description is required'}), 400
    if len(title) > 150:
        return jsonify({'error': 'Feedback title must be 150 characters or fewer.'}), 400

    report = FeedbackReport(
        user_id=user.id,
        destination_id=destination_id if destination_id else None,
        feedback_type=feedback_type,
        title=title,
        description=description,
        status='pending'
    )
    db.session.add(report)
    db.session.commit()

    dest_name = report.destination.name if report.destination else 'General'
    AuditService.log('feedback_submitted', user_id=user.id, entity_type='feedback', entity_id=report.id, details={'type': feedback_type, 'target': dest_name})

    return jsonify({
        'status': 'success',
        'message': 'Thank you! Your feedback has been received and routed to authorities for verification.',
        'report_id': report.id
    })

@api_feedback_bp.route('/list', methods=['GET'])
@login_required
def list_feedback():
    user = get_current_user()
    query = FeedbackReport.query
    if not user.is_admin:
        query = query.filter_by(user_id=user.id)
    reports = query.order_by(FeedbackReport.created_at.desc()).limit(50).all()
    return jsonify([r.to_dict() for r in reports])
