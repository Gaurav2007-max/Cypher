"""
TravelTech ML Service
=====================
Loads the trained RandomForest crowd-prediction model and exposes:
  - predict_crowd(...)          → single prediction dict
  - predict_daily_profile(...)  → 24-hour hourly list
  - predict_weekly_profile(...) → 7-day × 24-hour matrix
Falls back gracefully to heuristic estimates when the model file is missing.
"""

import os
import json
import pickle
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
_BASE_DIR   = Path(__file__).resolve().parents[2]   # project root
_MODEL_PATH = _BASE_DIR / "ml" / "crowd_model.pkl"
_META_PATH  = _BASE_DIR / "ml" / "model_meta.json"

# ── Singletons ─────────────────────────────────────────────────────────────────
_model    = None
_meta     = None
_loaded   = False

# ── Static look-up tables (mirrors generate_dataset_and_train.py) ──────────────
WEATHER_CODES = [
    "sunny", "partly_cloudy", "cloudy", "rain",
    "heavy_rain", "fog", "haze", "cold_clear", "hot", "humid_hot"
]

MONTH_WEATHER = {
    1:  ("cold_clear", 10.0, 45, 0),
    2:  ("partly_cloudy", 18.0, 55, 0),
    3:  ("sunny", 28.0, 50, 0),
    4:  ("sunny", 33.0, 45, 0),
    5:  ("hot", 42.0, 40, 0),
    6:  ("rain", 32.0, 80, 15),
    7:  ("rain", 29.0, 88, 25),
    8:  ("rain", 28.0, 88, 22),
    9:  ("rain", 30.0, 80, 12),
    10: ("partly_cloudy", 26.0, 60, 0),
    11: ("fog", 18.0, 65, 0),
    12: ("cold_clear", 12.0, 50, 0),
}

CITY_TRAFFIC = {
    0:5, 1:3, 2:2, 3:2, 4:3, 5:8, 6:25, 7:65, 8:80,
    9:70, 10:55, 11:60, 12:65, 13:60, 14:55, 15:60,
    16:70, 17:85, 18:90, 19:75, 20:50, 21:30, 22:18, 23:10
}

INDIAN_HOLIDAYS = {
    (1,26),(3,25),(4,14),(4,21),(5,1),(8,15),
    (10,2),(10,12),(10,23),(10,24),(11,1),(11,15),
    (12,25),(1,14),(3,8),(4,9),(8,19),(11,5),
}

FESTIVAL_MONTHS = [10, 11, 12, 1, 2]

CROWD_LABELS = {0: "None", 1: "Low", 2: "Moderate", 3: "High", 4: "Overcrowded"}
CROWD_COLORS = {
    0: "#28a745",  # green
    1: "#5cb85c",  # light-green
    2: "#f0ad4e",  # amber
    3: "#fd7e14",  # orange
    4: "#dc3545",  # red
}


def _load_model():
    """Lazy-load model and meta; safe to call multiple times."""
    global _model, _meta, _loaded
    if _loaded:
        return _model, _meta

    _loaded = True
    if _MODEL_PATH.exists() and _META_PATH.exists():
        try:
            with open(_MODEL_PATH, "rb") as f:
                _model = pickle.load(f)
            with open(_META_PATH, "r") as f:
                _meta = json.load(f)
            logger.info("ML crowd model loaded successfully (acc=%.2f%%)",
                        _meta.get("accuracy", 0) * 100)
        except Exception as e:
            logger.warning("Failed to load ML model: %s — using heuristic fallback", e)
            _model = None
            _meta  = None
    else:
        logger.warning("ML model not found at %s — using heuristic fallback", _MODEL_PATH)

    return _model, _meta


def _weather_for_month(month: int):
    """Return (weather_code_int, temp_c, humidity_pct, rainfall_mm) for a month."""
    wtype, temp, hum, rain = MONTH_WEATHER.get(month, ("sunny", 28.0, 55, 0))
    code = WEATHER_CODES.index(wtype) if wtype in WEATHER_CODES else 0
    return code, temp, hum, rain


def _traffic_for_hour(hour: int, is_weekend: bool) -> float:
    base = CITY_TRAFFIC.get(hour, 30)
    if is_weekend:
        base = base * 0.6 + 15
    return float(np.clip(base, 0, 100))


def _heuristic_crowd(dest_category: int, dest_base_popularity: float,
                     hour: int, dow: int, doy: int, month: int,
                     weather_code: int, temp: float, humidity: float,
                     rainfall: float, traffic: float,
                     day_of_month: int | None = None) -> dict:
    """Simple scoring heuristic — used when model is not available."""
    is_weekend     = int(dow >= 5)
    is_holiday     = int((month, day_of_month or datetime.now().day) in INDIAN_HOLIDAYS)
    is_festival    = int(month in FESTIVAL_MONTHS)
    is_peak_hour   = int(9 <= hour <= 18)

    score = dest_base_popularity * 5.0
    score += is_festival * 0.8
    score += is_peak_hour * 1.8
    score += is_weekend * 1.0
    score += is_holiday * 2.0
    score -= rainfall / 20.0
    score -= max(0, (temp - 38) / 10)
    score += (traffic / 80.0) * 0.6

    level = 0
    if score < 2.0:   level = 0
    elif score < 3.5: level = 1
    elif score < 5.0: level = 2
    elif score < 6.5: level = 3
    else:             level = 4

    return {
        "level": int(level),
        "label": CROWD_LABELS[level],
        "probability": round(min(0.55 + dest_base_popularity * 0.2, 0.75), 2),
        "color": CROWD_COLORS[level],
        "data_source": "heuristic_fallback",
    }


def predict_crowd(dest_category: int, dest_base_popularity: float,
                  hour: int, dow: int, doy: int, month: int,
                  weather_code: int, temp: float, humidity: float,
                  rainfall: float, traffic: float, day_of_month: int | None = None) -> dict:
    """
    Predict crowd level for a single (dest, time, weather, traffic) combination.

    Returns:
        {level: int 0-4, label: str, probability: float,
         color: str, data_source: 'ml_model'|'heuristic_fallback'}
    """
    model, meta = _load_model()
    # Calendar features must come from the forecast date, not the server's current date.
    day_of_month = day_of_month or datetime.now().day
    is_holiday = int((month, day_of_month) in INDIAN_HOLIDAYS)

    if model is None:
        return _heuristic_crowd(dest_category, dest_base_popularity, hour, dow, doy,
                                month, weather_code, temp, humidity, rainfall, traffic, day_of_month)

    features = meta["features"]
    X = [[
        dest_category, dest_base_popularity,
        hour, dow, doy, month,
        int(dow >= 5),
        is_holiday,
        int(month in FESTIVAL_MONTHS),
        weather_code, temp, humidity, rainfall, traffic
    ]]

    # Build feature vector in correct order
    feat_map = {
        "dest_category": dest_category,
        "dest_base_popularity": dest_base_popularity,
        "hour_of_day": hour,
        "day_of_week": dow,
        "day_of_year": doy,
        "month": month,
        "is_weekend": int(dow >= 5),
        "is_holiday": is_holiday,
        "is_festival_season": int(month in FESTIVAL_MONTHS),
        "weather_code": weather_code,
        "temperature_c": temp,
        "humidity_pct": humidity,
        "rainfall_mm": rainfall,
        "city_traffic_index": traffic,
    }
    X = [[feat_map[f] for f in features]]

    try:
        import pandas as pd
        X_df = pd.DataFrame([[feat_map[f] for f in features]], columns=features)
        level = int(model.predict(X_df)[0])
        proba = model.predict_proba(X_df)[0]
        probability = float(proba[level])
    except Exception as e:
        logger.error("ML predict failed: %s", e)
        return _heuristic_crowd(dest_category, dest_base_popularity, hour, dow, doy,
                                month, weather_code, temp, humidity, rainfall, traffic, day_of_month)

    return {
        "level": level,
        "label": CROWD_LABELS[level],
        "probability": round(probability, 3),
        "color": CROWD_COLORS[level],
        "data_source": "ml_model",
        "model_accuracy": meta.get("accuracy", 0),
        "model_cv_accuracy": meta.get("cv_accuracy", 0),
    }


def predict_daily_profile(dest_category: int, dest_base_popularity: float,
                           date_str: str | None = None) -> list[dict]:
    """
    Return 24 hourly predictions for a given date (defaults to today).

    Returns: list of 24 dicts with keys hour, level, label, probability, color
    """
    if date_str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("date must use YYYY-MM-DD format") from exc
    else:
        dt = datetime.now()

    month  = dt.month
    dow    = dt.weekday()
    doy    = dt.timetuple().tm_yday
    wcode, temp, hum, rain = _weather_for_month(month)
    is_weekend = dow >= 5

    profile = []
    for hour in range(24):
        traffic = _traffic_for_hour(hour, is_weekend)
        pred = predict_crowd(
            dest_category, dest_base_popularity,
            hour, dow, doy, month,
            wcode, temp, hum, rain, traffic, day_of_month=dt.day
        )
        pred["hour"] = hour
        pred["hour_label"] = f"{hour:02d}:00"
        profile.append(pred)

    return profile


def predict_weekly_profile(dest_category: int, dest_base_popularity: float,
                            start_date_str: str | None = None) -> dict:
    """
    Return a 7-day × 24-hour matrix starting from start_date (defaults to today).

    Returns: {
        days: [ {date, day_name, hours: [24 prediction dicts]} × 7 ],
        summary: { avg_level, peak_day, peak_hour }
    }
    """
    if start_date_str:
        try:
            start = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("start must use YYYY-MM-DD format") from exc
    else:
        start = datetime.now().replace(hour=0, minute=0, second=0)

    days_data = []
    all_levels = []

    for d in range(7):
        dt = start + timedelta(days=d)
        month  = dt.month
        dow    = dt.weekday()
        doy    = dt.timetuple().tm_yday
        wcode, temp, hum, rain = _weather_for_month(month)
        is_weekend = dow >= 5

        hours_data = []
        for hour in range(24):
            traffic = _traffic_for_hour(hour, is_weekend)
            pred = predict_crowd(
                dest_category, dest_base_popularity,
                hour, dow, doy, month,
                wcode, temp, hum, rain, traffic, day_of_month=dt.day
            )
            pred["hour"] = hour
            pred["hour_label"] = f"{hour:02d}:00"
            hours_data.append(pred)
            all_levels.append(pred["level"])

        days_data.append({
            "date": dt.strftime("%Y-%m-%d"),
            "day_name": dt.strftime("%A"),
            "day_short": dt.strftime("%a"),
            "hours": hours_data,
        })

    # Summary stats
    avg_level = round(float(np.mean(all_levels)), 2)
    peak_flat_idx = int(np.argmax(all_levels))
    peak_day  = days_data[peak_flat_idx // 24]["day_name"]
    peak_hour = peak_flat_idx % 24

    model, meta = _load_model()
    data_source = "ml_model" if model else "heuristic_fallback"

    return {
        "days": days_data,
        "summary": {
            "avg_level": avg_level,
            "avg_label": CROWD_LABELS[round(avg_level)],
            "peak_day": peak_day,
            "peak_hour": peak_hour,
            "peak_hour_label": f"{peak_hour:02d}:00",
        },
        "data_source": data_source,
        "model_accuracy": meta.get("accuracy", 0) if meta else 0,
        "model_cv_accuracy": meta.get("cv_accuracy", 0) if meta else 0,
    }


def get_model_info() -> dict:
    """Return metadata about the loaded model."""
    model, meta = _load_model()
    if meta:
        return {
            "available": True,
            "model_type": meta.get("model_type", "RandomForestClassifier"),
            "accuracy": meta.get("accuracy", 0),
            "cv_accuracy": meta.get("cv_accuracy", 0),
            "trained_at": meta.get("trained_at", "unknown"),
            "n_features": len(meta.get("features", [])),
            "classes": meta.get("classes", []),
        }
    return {
        "available": False,
        "note": "Model not trained yet — using heuristic fallback",
    }
