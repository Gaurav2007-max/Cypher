import json
from flask import request
from app.extensions import db
from app.models.audit import AuditLog

class AuditService:
    @staticmethod
    def log(action, user_id=None, entity_type=None, entity_id=None, details=None):
        try:
            ip = request.remote_addr if request else '127.0.0.1'
        except Exception:
            ip = '127.0.0.1'

        details_json = json.dumps(details) if isinstance(details, (dict, list)) else str(details or '')

        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details_json=details_json,
            ip_address=ip
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry

