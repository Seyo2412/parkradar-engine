from typing import List, Dict, Any
from geopy.distance import geodesic
try:
    from src.data_fetcher import ParkingFacility
except ModuleNotFoundError:
    from data_fetcher import ParkingFacility

class ParkingOptimizer:
    """
    Berechnet die kosten- und distanzoptimale Parkempfehlung.
    """
    WALK_SPEED_KMH = 4.5  # Durchschnittliche Gehgeschwindigkeit

    @classmethod
    def rank_options(cls, destination: tuple, facilities: List[ParkingFacility], 
                     duration_hours: float = 2.0) -> List[Dict[str, Any]]:
        ranked = []

        for f in facilities:
            dist_km = geodesic(destination, (f.latitude, f.longitude)).kilometers
            walk_min = (dist_km / cls.WALK_SPEED_KMH) * 60.0
            total_cost = f.hourly_rate_chf * duration_hours

            # Scoring-Formel: Niedriger = Besser
            # Gewichtet Kosten, Gehdistanz und Verfügbarkeit (Strafe wenn fast voll)
            availability_penalty = 15.0 if f.free_spaces < 10 else (5.0 if f.free_spaces < 30 else 0.0)
            score = (total_cost * 1.5) + (walk_min * 1.0) + availability_penalty

            ranked.append({
                "facility": f,
                "distance_m": int(dist_km * 1000),
                "walk_min": round(walk_min, 1),
                "total_cost_chf": round(total_cost, 2),
                "score": round(score, 1)
            })

        return sorted(ranked, key=lambda x: x["score"])