"""
tests/test_ml.py
=================
Tests for the ML crowd prediction service and Flask API endpoints.
"""
import pytest
from app import create_app
from app.config import Config


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
    RATELIMIT_ENABLED = False


@pytest.fixture(scope="module")
def client():
    app = create_app(TestingConfig)
    with app.test_client() as c:
        with app.app_context():
            from app.extensions import db
            from seed_data import seed
            db.create_all()
            seed(app=app)
        yield c


@pytest.fixture(scope="module")
def auth_client(client):
    """Client pre-logged-in as tourist alex_traveler."""
    client.post("/login", data={"username": "alex_traveler", "password": "tourist123"},
                follow_redirects=True)
    return client


# ── ml_service unit tests ──────────────────────────────────────────────────────

class TestMLService:
    def test_weekly_forecast_runs_model_in_one_batch(self, monkeypatch):
        from app.services import ml_service

        class BatchModel:
            predict_proba_calls = 0
            classes_ = [0, 1, 2, 3, 4]

            def predict_proba(self, features):
                self.predict_proba_calls += 1
                assert len(features) == 168
                return [[0, 0, 1, 0, 0]] * len(features)

        model = BatchModel()
        metadata = {
            "features": [
                "dest_category", "dest_base_popularity", "hour_of_day",
                "day_of_week", "day_of_year", "month", "is_weekend",
                "is_holiday", "is_festival_season", "weather_code",
                "temperature_c", "humidity_pct", "rainfall_mm",
                "city_traffic_index",
            ],
            "accuracy": 0.7,
            "cv_accuracy": 0.6,
        }
        monkeypatch.setattr(ml_service, "_load_model", lambda: (model, metadata))
        ml_service._weekly_profile_cached.cache_clear()

        forecast = ml_service.predict_weekly_profile(0, 0.7, "2031-10-01")

        assert len(forecast["days"]) == 7
        assert model.predict_proba_calls == 1

    def test_import_without_crash(self):
        """Importing ml_service must not raise even if model file is absent."""
        from app.services import ml_service  # noqa
        assert ml_service is not None

    def test_predict_crowd_returns_valid_dict(self):
        from app.services.ml_service import predict_crowd
        result = predict_crowd(
            dest_category=0, dest_base_popularity=0.75,
            hour=10, dow=1, doy=100, month=10,
            weather_code=1, temp=26.0, humidity=60.0,
            rainfall=0.0, traffic=55.0
        )
        assert isinstance(result, dict)
        assert "level" in result
        assert "label" in result
        assert "probability" in result
        assert "color" in result
        assert "data_source" in result
        assert 0 <= result["level"] <= 4
        assert result["label"] in {"None", "Low", "Moderate", "High", "Overcrowded"}
        assert 0.0 <= result["probability"] <= 1.0
        assert result["data_source"] in {"ml_model", "heuristic_fallback"}

    def test_predict_crowd_extreme_rain(self):
        """Heavy rain should tend to reduce crowd (level ≤ High in most cases)."""
        from app.services.ml_service import predict_crowd
        result = predict_crowd(
            dest_category=0, dest_base_popularity=0.50,
            hour=14, dow=3, doy=180, month=7,
            weather_code=4,   # heavy_rain
            temp=18.0, humidity=95.0,
            rainfall=60.0, traffic=20.0
        )
        assert 0 <= result["level"] <= 4  # valid range regardless

    def test_daily_profile_returns_24_hours(self):
        from app.services.ml_service import predict_daily_profile
        profile = predict_daily_profile(0, 0.80, date_str="2025-10-15")
        assert len(profile) == 24
        for entry in profile:
            assert "hour" in entry
            assert "level" in entry
            assert 0 <= entry["hour"] <= 23

    def test_daily_profile_default_date(self):
        """predict_daily_profile with no date must still return 24 items."""
        from app.services.ml_service import predict_daily_profile
        profile = predict_daily_profile(2, 0.95, date_str=None)
        assert len(profile) == 24

    def test_weekly_profile_returns_7_days(self):
        from app.services.ml_service import predict_weekly_profile
        weekly = predict_weekly_profile(0, 0.70, start_date_str="2025-10-01")
        assert "days" in weekly
        assert len(weekly["days"]) == 7
        for day in weekly["days"]:
            assert len(day["hours"]) == 24

    def test_weekly_summary_keys(self):
        from app.services.ml_service import predict_weekly_profile
        weekly = predict_weekly_profile(1, 0.60)
        assert "summary" in weekly
        summary = weekly["summary"]
        assert "avg_level" in summary
        assert "peak_day" in summary
        assert "peak_hour" in summary

    def test_get_model_info(self):
        from app.services.ml_service import get_model_info
        info = get_model_info()
        assert "available" in info
        if info["available"]:
            assert "accuracy" in info
            assert "model_type" in info
            assert info["model_type"] == "RandomForestClassifier"


# ── API endpoint tests ─────────────────────────────────────────────────────────

class TestMLAPI:
    def test_model_info_endpoint(self, client):
        r = client.get("/api/ml/model-info")
        assert r.status_code == 200
        data = r.get_json()
        assert "available" in data

    def test_crowd_forecast_returns_24_hours(self, client):
        """GET /api/ml/crowd-forecast/1 must return 24 crowd_levels entries."""
        r = client.get("/api/ml/crowd-forecast/1")
        assert r.status_code == 200
        data = r.get_json()
        assert "crowd_levels" in data
        assert len(data["crowd_levels"]) == 24
        # Verify structure of first entry
        first = data["crowd_levels"][0]
        assert "hour" in first
        assert "level" in first
        assert "label" in first

    def test_crowd_forecast_with_date_param(self, client):
        r = client.get("/api/ml/crowd-forecast/1?date=2025-10-15")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data["crowd_levels"]) == 24

    def test_crowd_weekly_returns_7_days(self, client):
        """GET /api/ml/crowd-weekly/1 must return 7 days each with 24 hours."""
        r = client.get("/api/ml/crowd-weekly/1")
        assert r.status_code == 200
        data = r.get_json()
        wf = data.get("weekly_forecast", {})
        days = wf.get("days", [])
        assert len(days) == 7
        for day in days:
            assert len(day["hours"]) == 24

    def test_invalid_dest_id_returns_404(self, client):
        r = client.get("/api/ml/crowd-forecast/99999")
        assert r.status_code == 404
        data = r.get_json()
        assert "error" in data

    def test_weekly_invalid_dest_returns_404(self, client):
        r = client.get("/api/ml/crowd-weekly/99999")
        assert r.status_code == 404

    def test_response_includes_disclaimer(self, client):
        r = client.get("/api/ml/crowd-forecast/1")
        data = r.get_json()
        assert "disclaimer" in data
        assert "ML" in data["disclaimer"] or "estimate" in data["disclaimer"]

    def test_response_is_live_weather_false(self, client):
        r = client.get("/api/ml/crowd-forecast/1")
        data = r.get_json()
        assert data.get("is_live_weather") is False

    def test_crowd_forecast_dest2(self, client):
        """Test with second destination to ensure different meta is resolved."""
        r = client.get("/api/ml/crowd-forecast/2")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data["crowd_levels"]) == 24

    def test_forecast_data_source_field(self, client):
        """Each crowd_level entry must include data_source."""
        r = client.get("/api/ml/crowd-forecast/1")
        data = r.get_json()
        first = data["crowd_levels"][0]
        assert first.get("data_source") in {"ml_model", "heuristic_fallback"}
