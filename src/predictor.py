import numpy as np
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime
from typing import Dict, Any

class PredictiveParkingModel:
    """
    ML-Vorhersagemodell für die Wahrscheinlichkeit freier Parkplätze in Strassenzügen (Blau/Weiss).
    Features: Stunde, Wochentag, Distanz zum Zentrum (HB), Event-Flag, Regen-Flag.
    """
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=40, random_state=42)
        self._train_baseline()

    def _train_baseline(self):
        # Synthetischer Trainingsdatensatz basierend auf Zürcher Verkehrsmustern
        np.random.seed(42)
        n_samples = 2500

        hours = np.random.randint(0, 24, n_samples)
        weekdays = np.random.randint(0, 7, n_samples)
        dist_hb = np.random.uniform(0.2, 5.0, n_samples)  # km zum HB
        is_event = np.random.choice([0, 1], n_samples, p=[0.85, 0.15])

        # Wahrscheinlichkeit berechnen (Ground Truth Synthese)
        # Nachts hoch, Rushhour im Zentrum sehr gering, Distanz erhöht Chance
        p_free = 0.85 - (0.45 * np.exp(-((hours - 14) ** 2) / 25.0))
        p_free -= 0.15 * (weekdays < 5)  # Werktags voller
        p_free += 0.08 * dist_hb
        p_free -= 0.20 * is_event
        p_free = np.clip(p_free + np.random.normal(0, 0.05, n_samples), 0.05, 0.95)

        X = np.column_stack([hours, weekdays, dist_hb, is_event])
        y = p_free
        self.model.fit(X, y)

    def predict_street_parking(self, target_lat: float, target_lon: float, 
                               timestamp: datetime = None, is_event: bool = False) -> Dict[str, Any]:
        if timestamp is None:
            timestamp = datetime.now()

        # Distanz zum HB Zürich (47.3781, 8.5401)
        lat_hb, lon_hb = 47.3781, 8.5401
        dist_km = np.sqrt(((target_lat - lat_hb) * 111.0)**2 + 
                          ((target_lon - lon_hb) * 75.0)**2)

        features = np.array([[timestamp.hour, timestamp.weekday(), dist_km, int(is_event)]])
        prob_free = float(self.model.predict(features)[0])

        # Wahrscheinlichkeitsstufe für UI
        if prob_free > 0.70:
            level = "HOCH (Gute Chancen)"
            color = "#28a745"
        elif prob_free > 0.40:
            level = "MITTEL (Suchverkehr wahrscheinlich)"
            color = "#ffc107"
        else:
            level = "GERING (Überlastet, Parkhaus empfohlen)"
            color = "#dc3545"

        return {
            "probability_free": round(prob_free, 2),
            "expected_search_time_min": max(2, int((1.0 - prob_free) * 16)),
            "level": level,
            "badge_color": color,
            "distance_to_center_km": round(dist_km, 2)
        }