from functools import wraps
from flask import session, redirect, url_for, request, jsonify, abort
from app.models.user import User

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_active:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required. Please log in.'}), 401
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or not user.is_active:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required.'}), 401
                return redirect(url_for('auth.login'))
            
            # Special check for authority: must be approved by admin
            if user.role == 'authority' and not user.authority_approved and 'authority' in allowed_roles:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Your authority account is awaiting administrator approval.'}), 403
                return render_pending_approval_notice()

            if user.role not in allowed_roles and not user.is_admin:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Access forbidden: Insufficient permissions.'}), 403
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def render_pending_approval_notice():
    from flask import render_template
    return render_template('auth/pending_approval.html'), 403

