from datetime import datetime
from sqlalchemy import inspect, text

from flask import Flask, jsonify, render_template, request, session
from app.config import Config
from app.extensions import csrf, db, limiter
from app.auth_utils import get_current_user


def get_site_theme(city_name, month=None):
    month = month or datetime.now().month
    if city_name and city_name.strip().casefold() == 'shimla' and month in (12, 1, 2):
        return 'winter'
    return 'olive'


def create_app(config_class=Config):
    flask_app = Flask(__name__)
    flask_app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(flask_app)
    csrf.init_app(flask_app)
    limiter.init_app(flask_app)

    # Context processors for templates
    @flask_app.context_processor
    def inject_global_variables():
        user = get_current_user()
        selected_city = None
        if user and user.is_tourist:
            from app.models.city import City

            city_id = session.get('selected_city_id')
            if not city_id and user.profile:
                city_id = user.profile.preferred_city_id
            if city_id:
                selected_city = db.session.get(City, city_id)

        return {
            'current_user': user,
            'is_logged_in': user is not None,
            'user_role': user.role if user else None,
            'site_theme': get_site_theme(selected_city.name if selected_city else None)
        }

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.tourist import tourist_bp
    from app.routes.authority import authority_bp
    from app.routes.admin import admin_bp
    from app.routes.api_destinations import api_dest_bp
    from app.routes.api_safety import api_safety_bp
    from app.routes.api_feedback import api_feedback_bp
    from app.routes.api_routes import api_routes_bp
    from app.routes.api_ml import api_ml_bp
    from app.services.safety_dispatch import start_safety_scheduler

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(tourist_bp)
    flask_app.register_blueprint(authority_bp)
    flask_app.register_blueprint(admin_bp)
    flask_app.register_blueprint(api_dest_bp)
    flask_app.register_blueprint(api_safety_bp)
    flask_app.register_blueprint(api_feedback_bp)
    flask_app.register_blueprint(api_routes_bp)
    flask_app.register_blueprint(api_ml_bp)

    # Error handlers
    @flask_app.errorhandler(403)
    def forbidden_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Access forbidden.'}), 403
        return render_template('auth/403.html'), 403

    @flask_app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'API endpoint or resource not found.'}), 404
        return render_template('auth/404.html'), 404

    @flask_app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'An internal server error occurred.'}), 500
        return render_template('auth/500.html'), 500

    @flask_app.errorhandler(429)
    def rate_limit_error(error):
        response = error.get_response()
        if request.path.startswith('/api/'):
            response.set_data(jsonify({'error': 'Too many requests. Please try again later.'}).get_data())
            response.content_type = 'application/json'
        return response

    @flask_app.get('/health')
    def health_check():
        try:
            db.session.execute(text('SELECT 1'))
        except Exception:
            db.session.rollback()
            flask_app.logger.exception('Render health check could not reach the database.')
            return jsonify({'status': 'unhealthy'}), 503
        return jsonify({'status': 'ok'})

    # Create tables
    with flask_app.app_context():
        import app.models  # ensure models are registered
        db.create_all()
        story_columns = {column['name'] for column in inspect(db.engine).get_columns('stories')}
        if 'is_active' not in story_columns:
            db.session.execute(text(
                'ALTER TABLE stories ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE'
            ))
            db.session.commit()
        action_columns = {
            column['name'] for column in inspect(db.engine).get_columns('pending_safety_actions')
        }
        if 'dispatch_error' not in action_columns:
            db.session.execute(text(
                'ALTER TABLE pending_safety_actions ADD COLUMN dispatch_error VARCHAR(255)'
            ))
            db.session.commit()
        db.session.execute(text(
            'CREATE TABLE IF NOT EXISTS app_migrations '
            '(name VARCHAR(100) PRIMARY KEY, applied_at TIMESTAMP NOT NULL)'
        ))
        migrated = db.session.execute(
            text("SELECT name FROM app_migrations WHERE name = 'explicit_safety_consents_v1'")
        ).first()
        if not migrated:
            db.session.execute(text(
                'UPDATE user_profiles SET location_tracking_enabled = FALSE, emergency_consent = FALSE'
            ))
            db.session.execute(text('DELETE FROM location_samples'))
            db.session.execute(text(
                "INSERT INTO app_migrations (name, applied_at) VALUES "
                "('explicit_safety_consents_v1', :applied_at)"
            ), {'applied_at': datetime.utcnow()})
            db.session.commit()
        provenance_migration = db.session.execute(
            text("SELECT name FROM app_migrations WHERE name = 'sample_data_provenance_v1'")
        ).first()
        if not provenance_migration:
            applied_at = datetime.utcnow()
            db.session.execute(text(
                "UPDATE destinations SET source_attribution = 'Unverified sample data', "
                "last_verified_at = NULL WHERE source_attribution IN "
                "('Archaeological Survey of India & Haryana Tourism', "
                "'Haryana State Heritage Board', 'Haryana Forest & Wildlife Department', "
                "'Conservation Foundation & Eco-Tourism Cell', 'ISKCON Cultural Board')"
            ))
            db.session.execute(text(
                "UPDATE destinations SET crowd_status = 'Normal', crowd_explanation = NULL, "
                "crowd_expires_at = NULL, crowd_updated_at = :applied_at "
                "WHERE (crowd_explanation IN ("
                "'Surajkund Crafts Fair weekend rush. Parking full and ticket queue exceeds 40 minutes.', "
                "'Peak weekend international tourist influx. Security queue 55 mins.', "
                "'Quiet green spaces, zero waiting lines.', "
                "'Family visitors along the promenade.', "
                "'Pristine quiet nature trail.', "
                "'Pleasant visiting conditions, uncrowded royal galleries.', "
                "'Evening Ganga Aarti crowd gathering; heavy congestion on approach lanes.', "
                "'Peaceful meditative atmosphere.') "
                "OR name IN ('The Ridge & Christ Church', 'Hawa Mahal (Palace of Winds)')) "
                "AND crowd_updated_by_id IS NULL "
                "OR crowd_explanation = 'Surajkund Crafts Fair weekend rush. Parking full and ticket queue exceeds 40 minutes.'"
            ), {'applied_at': applied_at})
            db.session.execute(text(
                "UPDATE activities SET price_source = 'Sample data; verify locally', "
                "last_verified_at = NULL "
                "WHERE price_source = 'Sample data; verify with the local operator'"
            ))
            db.session.execute(text(
                "UPDATE cuisine_items SET verified_status = 'sample', user_rating = NULL, "
                "allergen_info = 'Not verified; ask the vendor' "
                "WHERE verified_status = 'sample'"
            ))
            db.session.execute(text(
                "DELETE FROM crowd_status_records WHERE explanation = "
                "'Surajkund Crafts Fair weekend rush. Parking full.'"
            ))
            db.session.execute(text(
                "DELETE FROM feedback_reports WHERE title = 'Parking Gate Notice' AND "
                "description = 'South parking gate is closed due to fair maintenance. Tourists should enter via North Gate 2.'"
            ))
            db.session.execute(text(
                "INSERT INTO app_migrations (name, applied_at) VALUES "
                "('sample_data_provenance_v1', :applied_at)"
            ), {'applied_at': applied_at})
            db.session.commit()

    start_safety_scheduler(flask_app)
    return flask_app
