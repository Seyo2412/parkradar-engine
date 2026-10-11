import pytest
from datetime import datetime
from src.data_fetcher import ZurichParkDataFetcher
from src.predictor import PredictiveParkingModel
from src.optimizer import ParkingOptimizer

def test_data_fetcher():
    fetcher = ZurichParkDataFetcher()
    facilities = fetcher.fetch_live_data()
    assert len(facilities) > 0, "Mindestens ein Parkhaus muss geladen werden"
    first = facilities[0]
    assert 0.0 <= first.occupancy_rate <= 1.0, "Auslastungsrate muss zwischen 0 und 1 liegen"
    assert first.free_spaces >= 0, "Freie Plätze dürfen nicht negativ sein"

def test_ml_predictor():
    predictor = PredictiveParkingModel()
    pred = predictor.predict_street_parking(47.3769, 8.5380, datetime.now(), is_event=False)
    assert 0.0 <= pred["probability_free"] <= 1.0, "Wahrscheinlichkeit muss zwischen 0 und 1 liegen"
    assert pred["expected_search_time_min"] >= 0, "Suchzeit darf nicht negativ sein"
    assert "level" in pred

def test_optimizer():
    fetcher = ZurichParkDataFetcher()
    facilities = fetcher.fetch_live_data()
    ranked = ParkingOptimizer.rank_options((47.3769, 8.5380), facilities, duration_hours=2.0)
    assert len(ranked) == len(facilities)
    assert ranked[0]["score"] <= ranked[-1]["score"], "Ergebnis muss nach Score aufsteigend sortiert sein"