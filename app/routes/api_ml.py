"""
ML Crowd Prediction API Blueprint
===================================
GET /api/ml/crowd-forecast/<dest_id>?date=YYYY-MM-DD   → 24-hour profile
GET /api/ml/crowd-weekly/<dest_id>?start=YYYY-MM-DD    → 7-day × 24 matrix
GET /api/ml/model-info                                  → model metadata
"""

from flask import Blueprint, jsonify, request, g
from app.extensions import db
from app.models.destination import Destination
from app.services.ml_service import (
    predict_daily_profile, predict_weekly_profile,
    get_model_info, CROWD_LABELS, CROWD_COLORS
)
import logging

logger = logging.getLogger(__name__)
api_ml_bp = Blueprint("api_ml", __name__, url_prefix="/api/ml")

# ── Destination category → (cat_id, base_popularity) lookup ────────────────────
# Mirrors DEST_META in generate_dataset_and_train.py
_DEST_META_LOOKUP = {
    "surajkund":         (0, 0.85),
    "nahar singh":       (0, 0.70),
    "ballabhgarh":       (0, 0.70),
    "badkhal":           (1, 0.65),
    "asola":             (1, 0.55),
    "iskcon":            (2, 0.80),
    "radha govind":      (2, 0.80),
    "dhyankaksh":        (2, 0.60),
    "town park":         (1, 0.70),
    "jakhoo":            (2, 0.85),
    "himachal state museum": (0, 0.65),
    "museum":            (0, 0.65),
    "gaiety":            (0, 0.70),
    "nahargarh":         (0, 0.85),
    "kashi vishwanath":  (2, 0.98),
    "taj mahal":         (3, 0.99),
    "mehtab bagh":       (0, 0.60),
    "ridge":             (0, 0.75),
    "christ church":     (0, 0.75),
    "potters hill":      (1, 0.50),
    "hawa mahal":        (3, 0.92),
    "panna meena":       (0, 0.60),
    "dashashwamedh":     (2, 0.95),
    "sarnath":           (2, 0.80),
    "jal mahal":         (3, 0.75),
    "amber fort":        (3, 0.90),
    "jantar mantar":     (0, 0.70),
    "agra fort":         (3, 0.88),
    "fatehpur sikri":    (3, 0.75),
    "default_monument":  (0, 0.60),
    "default_nature":    (1, 0.50),
    "default_temple":    (2, 0.65),
    "default_market":    (3, 0.55),
}

CATEGORY_DEFAULTS = {
    "monument":   (0, 0.70),
    "heritage":   (0, 0.70),
    "nature":     (1, 0.55),
    "park":       (1, 0.55),
    "temple":     (2, 0.65),
    "religious":  (2, 0.65),
    "market":     (3, 0.55),
    "food":       (3, 0.55),
}


def _resolve_dest_meta(dest: Destination) -> tuple[int, float]:
    """Map a Destination DB row → (category_id, base_popularity)."""
    name_lower = (dest.name or "").lower()

    # Try keyword matching against the lookup table
    for keyword, meta in _DEST_META_LOOKUP.items():
        if keyword in name_lower:
            return meta

    # Fall back on destination.category field
    cat_lower = (dest.category or "").lower()
    for keyword, meta in CATEGORY_DEFAULTS.items():
        if keyword in cat_lower:
            return meta

    # Generic fallback
    return (0, 0.60)


def _dest_or_404(dest_id: int):
    dest = db.session.get(Destination, dest_id)
    if not dest:
        return None, jsonify({"error": "Destination not found", "dest_id": dest_id}), 404
    return dest, None, None


# ── Routes ──────────────────────────────────────────────────────────────────────

@api_ml_bp.route("/model-info", methods=["GET"])
def model_info():
    """Return metadata about the trained ML model."""
    info = get_model_info()
    return jsonify(info)


@api_ml_bp.route("/crowd-forecast/<int:dest_id>", methods=["GET"])
def crowd_forecast(dest_id: int):
    """
    24-hour hourly crowd prediction for a destination on a given date.
    Query param: ?date=YYYY-MM-DD  (defaults to today)
    """
    dest = db.session.get(Destination, dest_id)
    if not dest:
        return jsonify({"error": "Destination not found", "dest_id": dest_id}), 404

    date_str = request.args.get("date")
    cat_id, base_pop = _resolve_dest_meta(dest)

    try:
        profile = predict_daily_profile(cat_id, base_pop, date_str)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("crowd_forecast error for dest_id=%s", dest_id)
        return jsonify({"error": "Prediction failed", "detail": str(e)}), 500

    # Attach current authority crowd status for comparison
    authority_status = dest.effective_crowd_status or "unknown"

    return jsonify({
        "dest_id": dest_id,
        "dest_name": dest.name,
        "dest_city": dest.city.name if dest.city else "Unknown",
        "date": date_str or "today",
        "authority_crowd_status": authority_status,
        "crowd_levels": profile,
        "features_used": [
            "hour_of_day", "day_of_week", "day_of_year", "month",
            "is_weekend", "is_holiday", "is_festival_season",
            "weather_code", "temperature_c", "humidity_pct",
            "rainfall_mm", "city_traffic_index",
            "dest_category", "dest_base_popularity"
        ],
        "weather_note": "Weather estimates are derived from historical monthly patterns for India, not live data.",
        "is_live_weather": False,
        "disclaimer": (
            "These are ML-predicted crowd estimates based on historical patterns. "
            "Authority-verified crowd status always takes precedence."
        ),
        "crowd_label_map": CROWD_LABELS,
        "crowd_color_map": CROWD_COLORS,
    })


@api_ml_bp.route("/crowd-weekly/<int:dest_id>", methods=["GET"])
def crowd_weekly(dest_id: int):
    """
    7-day × 24-hour crowd prediction matrix.
    Query param: ?start=YYYY-MM-DD  (defaults to today)
    """
    dest = db.session.get(Destination, dest_id)
    if not dest:
        return jsonify({"error": "Destination not found", "dest_id": dest_id}), 404

    start_str = request.args.get("start")
    cat_id, base_pop = _resolve_dest_meta(dest)

    try:
        weekly = predict_weekly_profile(cat_id, base_pop, start_str)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("crowd_weekly error for dest_id=%s", dest_id)
        return jsonify({"error": "Prediction failed", "detail": str(e)}), 500

    authority_status = dest.effective_crowd_status or "unknown"

    return jsonify({
        "dest_id": dest_id,
        "dest_name": dest.name,
        "dest_city": dest.city.name if dest.city else "Unknown",
        "start_date": start_str or "today",
        "authority_crowd_status": authority_status,
        "weekly_forecast": weekly,
        "is_live_weather": False,
        "disclaimer": (
            "These are ML-predicted crowd estimates based on historical patterns. "
            "Authority-verified crowd status always takes precedence."
        ),
        "crowd_label_map": CROWD_LABELS,
        "crowd_color_map": CROWD_COLORS,
    })

