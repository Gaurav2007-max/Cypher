"""
TravelTech ML Crowd Prediction Engine
======================================
Generates a rich synthetic tourist-crowd dataset inspired by:
  - Kaggle: "Tourist Footfall & Footprint India" patterns
  - Kaggle: "Weather impact on tourism" datasets
  - Google Popular Times open research

Features used:
  hour_of_day (0-23), day_of_week (0=Mon..6=Sun), day_of_year (1-365),
  month (1-12), is_weekend, is_holiday (Indian public holidays),
  is_festival_season, weather_condition (encoded), temperature_c,
  humidity_pct, rainfall_mm, city_traffic_index (0-100),
  destination_category (encoded), destination_base_popularity (0-1)

Target: crowd_level  0=None  1=Low  2=Moderate  3=High  4=Overcrowded
"""

import os, json, pickle
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DEST_META = {
    # (category_id, base_popularity 0-1, peak_months, peak_hours_start, peak_hours_end)
    "Surajkund Ancient Amphitheater & Reservoir": (0, 0.85, [2, 10, 11, 12], 9, 18),
    "Raja Nahar Singh Palace (Ballabhgarh Fort)":  (0, 0.70, [10, 11, 12, 1], 10, 17),
    "Badkhal Lake & Eco Biodiversity Ridge":        (1, 0.65, [10, 11, 12, 1], 6, 18),
    "Asola Bhatti Sanctuary — Peacock Hidden Lake": (1, 0.55, [10, 11, 1, 2], 6, 17),
    "Sri Sri Radha Govind Temple (ISKCON Faridabad)":(2, 0.80, [1,2,7,8,9,10], 4, 21),
    "Taj Mahal & Yamuna Riverfront":                (3, 0.99, list(range(1,13)), 6, 18),
    "Mehtab Bagh (Moonlight Garden)":               (0, 0.60, [10,11,12,1,2], 6, 18),
    "The Ridge & Christ Church":                    (0, 0.75, [5,6,7,8], 8, 18),
    "Potters Hill Cedar Eco Forest":                (1, 0.50, [4,5,6,7], 8, 17),
    "Hawa Mahal (Palace of Winds)":                 (3, 0.92, list(range(1,13)), 8, 18),
    "Panna Meena ka Kund (Hidden Stepwell)":        (0, 0.60, [10,11,12,1,2], 6, 17),
    "Dashashwamedh Ghat & Ganga Aarti":             (2, 0.95, list(range(1,13)), 5, 22),
    "Sarnath Deer Park & Dhamek Stupa":             (2, 0.80, [10,11,12,1,2], 6, 18),
}

WEATHER_MAP = {
    "sunny":   (32.0, 50, 0),
    "partly_cloudy": (28.0, 60, 0),
    "cloudy":  (24.0, 72, 2),
    "rain":    (21.0, 88, 18),
    "heavy_rain": (18.0, 95, 55),
    "fog":     (14.0, 90, 0),
    "haze":    (26.0, 70, 0),
    "cold_clear": (10.0, 45, 0),
    "hot":     (42.0, 40, 0),
    "humid_hot": (37.0, 82, 0),
}

MONTH_WEATHER = {
    1:  ["cold_clear","fog","partly_cloudy"],
    2:  ["partly_cloudy","sunny","cold_clear"],
    3:  ["sunny","haze","partly_cloudy"],
    4:  ["sunny","hot","haze"],
    5:  ["hot","humid_hot","haze"],
    6:  ["rain","humid_hot","cloudy"],
    7:  ["rain","heavy_rain","cloudy"],
    8:  ["rain","heavy_rain","cloudy"],
    9:  ["rain","partly_cloudy","cloudy"],
    10: ["partly_cloudy","sunny","cold_clear"],
    11: ["fog","cold_clear","partly_cloudy"],
    12: ["cold_clear","fog","partly_cloudy"],
}

INDIAN_HOLIDAYS = {
    (1,26), (3,25), (4,14), (4,21), (5,1), (8,15),
    (10,2), (10,12), (10,23), (10,24), (11,1), (11,15),
    (12,25), (1,14), (3,8), (4,9), (8,19), (11,5),
}

FESTIVAL_MONTHS = [10, 11, 12, 1, 2]

CITY_TRAFFIC = {  # hour -> base traffic index
    0:5, 1:3, 2:2, 3:2, 4:3, 5:8, 6:25, 7:65, 8:80,
    9:70, 10:55, 11:60, 12:65, 13:60, 14:55, 15:60,
    16:70, 17:85, 18:90, 19:75, 20:50, 21:30, 22:18, 23:10
}

def generate_dataset(n_rows_per_dest=3000):
    records = []
    np.random.seed(42)
    dest_names = list(DEST_META.keys())

    for dest_name, (cat_id, base_pop, peak_months, ph_start, ph_end) in DEST_META.items():
        for _ in range(n_rows_per_dest):
            dt = datetime(2022, 1, 1) + timedelta(
                days=int(np.random.randint(0, 730)),
                hours=int(np.random.randint(0, 24))
            )
            hour = dt.hour
            dow = dt.weekday()
            doy = dt.timetuple().tm_yday
            month = dt.month
            is_weekend = int(dow >= 5)
            is_holiday = int((month, dt.day) in INDIAN_HOLIDAYS)
            is_festival = int(month in FESTIVAL_MONTHS)
            is_peak_month = int(month in peak_months)
            is_peak_hour = int(ph_start <= hour <= ph_end)

            weather_type = np.random.choice(MONTH_WEATHER[month])
            base_temp, base_hum, base_rain = WEATHER_MAP[weather_type]
            temp = float(np.clip(np.random.normal(base_temp, 3), -5, 50))
            humidity = float(np.clip(np.random.normal(base_hum, 8), 10, 100))
            rainfall = max(0.0, float(np.random.exponential(base_rain) if base_rain > 0 else 0))
            weather_code = list(WEATHER_MAP.keys()).index(weather_type)

            base_traffic = CITY_TRAFFIC.get(hour, 30)
            # Weekend traffic pattern differs: lower morning rush, higher midday
            if is_weekend:
                base_traffic = base_traffic * 0.6 + 15
            traffic = float(np.clip(np.random.normal(base_traffic, 12), 0, 100))

            # --- Crowd score formula ---
            score = base_pop * 5.0          # 0-5
            score += is_peak_month * 1.2
            score += is_peak_hour * 1.8
            score += is_weekend * 1.0
            score += is_holiday * 2.0
            score += is_festival * 0.8
            score -= (rainfall / 20.0)       # rain reduces visitors
            score -= max(0, (temp - 38) / 10) # extreme heat penalty
            score += (traffic / 80.0) * 0.6  # traffic slightly correlates
            score += np.random.normal(0, 0.6) # noise

            # Map to 0-4 crowd level
            if score < 2.0:
                crowd = 0  # None
            elif score < 3.5:
                crowd = 1  # Low
            elif score < 5.0:
                crowd = 2  # Moderate
            elif score < 6.5:
                crowd = 3  # High
            else:
                crowd = 4  # Overcrowded

            records.append({
                "dest_name": dest_name,
                "dest_category": cat_id,
                "dest_base_popularity": base_pop,
                "hour_of_day": hour,
                "day_of_week": dow,
                "day_of_year": doy,
                "month": month,
                "is_weekend": is_weekend,
                "is_holiday": is_holiday,
                "is_festival_season": is_festival,
                "weather_code": weather_code,
                "temperature_c": round(temp, 1),
                "humidity_pct": round(humidity, 1),
                "rainfall_mm": round(rainfall, 2),
                "city_traffic_index": round(traffic, 1),
                "crowd_level": crowd
            })

    df = pd.DataFrame(records)
    print(f"Dataset generated: {len(df)} rows x {len(df.columns)} columns")
    print("Crowd distribution:\n", df["crowd_level"].value_counts().sort_index())
    return df


def train_model(df):
    FEATURES = [
        "dest_category", "dest_base_popularity",
        "hour_of_day", "day_of_week", "day_of_year", "month",
        "is_weekend", "is_holiday", "is_festival_season",
        "weather_code", "temperature_c", "humidity_pct", "rainfall_mm",
        "city_traffic_index"
    ]
    X = df[FEATURES]
    y = df["crowd_level"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print("\nTraining Random Forest Crowd Predictor...")
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=14,
        min_samples_split=6,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    print(f"\nTest Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred,
          target_names=["None","Low","Moderate","High","Overcrowded"]))

    cv_scores = cross_val_score(rf, X, y, cv=5, scoring="accuracy")
    print(f"5-Fold CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Feature importances
    feat_imp = sorted(zip(FEATURES, rf.feature_importances_),
                      key=lambda x: -x[1])
    print("\nTop Feature Importances:")
    for name, imp in feat_imp[:8]:
        print(f"  {name:35s}: {imp:.4f}")

    return rf, FEATURES, acc, float(cv_scores.mean())


def save_artifacts(model, features, acc, cv_acc):
    os.makedirs("ml", exist_ok=True)

    with open("ml/crowd_model.pkl", "wb") as f:
        pickle.dump(model, f)
    print("Saved: ml/crowd_model.pkl")

    meta = {
        "features": features,
        "classes": ["None", "Low", "Moderate", "High", "Overcrowded"],
        "weather_codes": list(WEATHER_MAP.keys()),
        "accuracy": round(acc, 4),
        "cv_accuracy": round(cv_acc, 4),
        "dest_meta": {k: {"category": v[0], "base_popularity": v[1],
                          "peak_months": v[2]}
                      for k, v in DEST_META.items()},
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "model_type": "RandomForestClassifier",
        "n_estimators": 200,
        "note": "Trained on synthetically generated tourist-crowd dataset modeled after Indian tourism patterns."
    }
    with open("ml/model_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print("Saved: ml/model_meta.json")


if __name__ == "__main__":
    df = generate_dataset(n_rows_per_dest=3000)
    df.to_csv("ml/crowd_training_dataset.csv", index=False)
    print("Saved: ml/crowd_training_dataset.csv")

    model, features, acc, cv_acc = train_model(df)
    save_artifacts(model, features, acc, cv_acc)
    print(f"\nAll done! Model accuracy: {acc:.2%}, CV: {cv_acc:.2%}")

