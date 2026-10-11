import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import datetime

try:
    from src.data_fetcher import ZurichParkDataFetcher
    from src.predictor import PredictiveParkingModel
    from src.optimizer import ParkingOptimizer
except ModuleNotFoundError:
    from data_fetcher import ZurichParkDataFetcher
    from predictor import PredictiveParkingModel
    from optimizer import ParkingOptimizer

st.set_page_config(page_title="ParkRadar AG - Live Engine", layout="wide", page_icon="🚗")

# Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1e222d;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #00d26a;
    }
</style>
""", unsafe_allow_html=True)

st.title("🅿️ ParkRadar AG — Smart Parking Live Engine (Zürich)")
st.caption("Echtzeit-Aggregation von Schweizer Open Data, ML-Belegungsprognosen & dynamischer Preis-Optimierer")

# Backend Komponenten laden
@st.cache_resource
def load_models():
    return ZurichParkDataFetcher(), PredictiveParkingModel()

fetcher, predictor = load_models()
facilities = fetcher.fetch_live_data()

# Sidebar: Zielort-Eingabe
st.sidebar.header("📍 Ziel-Präferenzen")
dest_name = st.sidebar.selectbox(
    "Zielort in Zürich auswählen:",
    ["Zürich HB / Bahnhofstrasse", "Opernhaus / Bellevue", "Paradeplatz", "Hardbrücke / Zürich West"]
)

DEST_COORDS = {
    "Zürich HB / Bahnhofstrasse": (47.3769, 8.5380),
    "Opernhaus / Bellevue": (47.3653, 8.5471),
    "Paradeplatz": (47.3697, 8.5389),
    "Hardbrücke / Zürich West": (47.3854, 8.5173),
}
dest_lat, dest_lon = DEST_COORDS[dest_name]

park_hours = st.sidebar.slider("Geplante Parkdauer (Stunden):", 0.5, 8.0, 2.0, 0.5)
has_event = st.sidebar.checkbox("Grossveranstaltung / Feiertag", False)

# 1. KPIs
col1, col2, col3, col4 = st.columns(4)
total_free = sum(f.free_spaces for f in facilities)
total_cap = sum(f.total_spaces for f in facilities)
avg_occ = (1.0 - (total_free / total_cap)) * 100

col1.metric("Freie Parkhausplätze", f"{total_free:,}", f"{len(facilities)} Parkhäuser")
col2.metric("Durchschn. Auslastung", f"{avg_occ:.1f} %", "-2.1% ggü. Vorstunde")

# ML Prognose Strassenparkplätze
street_pred = predictor.predict_street_parking(dest_lat, dest_lon, datetime.now(), has_event)
col3.metric("Freie Blaue Zone Chance", f"{street_pred['probability_free']*100:.0f} %", street_pred["level"])
col4.metric("Ø Parksuchverkehr Zeit", f"{street_pred['expected_search_time_min']} Min.", "Potenzial für ParkRadar")

st.markdown("---")

# 2. Ranking & Empfehlung
st.subheader("💡 Optimaler ParkRadar-Vorschlag")
ranked = ParkingOptimizer.rank_options((dest_lat, dest_lon), facilities, park_hours)
best = ranked[0]

c_best1, c_best2, c_best3 = st.columns(3)
with c_best1:
    st.success(f"🏆 Top-Empfehlung: **{best['facility'].name}**")
    st.write(f"🚶 **{best['walk_min']} Min.** Gehdistanz ({best['distance_m']} m)")
with c_best2:
    st.info(f"💰 Gesamtkosten: **CHF {best['total_cost_chf']:.2f}** ({best['facility'].hourly_rate_chf:.2f} CHF/h)")
    st.write(f"🟢 **{best['facility'].free_spaces} Plätze frei** ({best['facility'].occupancy_rate*100:.1f}% belegt)")
with c_best3:
    st.warning("🌱 ESG Green-Impact")
    co2_saved = round(best['walk_min'] * 0.12, 2)
    st.write(f"**~{co2_saved} kg CO₂** gespart durch direkte Navigation ohne Suchverkehr.")

# 3. Interaktive Karte (Freie OpenStreetMap / Stadia Tiles ohne Key-Lock)
st.subheader("🗺️ Live-Verfügbarkeitskarte & Navigation")

m = folium.Map(
    location=[dest_lat, dest_lon], 
    zoom_start=14, 
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="&copy; OpenStreetMap contributors"
)

# Zielort Marker
folium.Marker(
    [dest_lat, dest_lon],
    popup=f"<b>Zielort:</b> {dest_name}",
    tooltip="Zieladresse",
    icon=folium.Icon(color="darkblue", icon="flag", prefix="fa")
).add_to(m)

# Gehlinie zur Top-Empfehlung zeichnen
best_facility = best["facility"]
folium.PolyLine(
    locations=[[dest_lat, dest_lon], [best_facility.latitude, best_facility.longitude]],
    color="#007bff",
    weight=3,
    dash_array="6",
    tooltip=f"Fussweg zur Top-Option: {best['walk_min']} Min."
).add_to(m)

# Alle Parkhäuser einzeichnen
for item in ranked:
    f = item["facility"]
    # Farbschema: Grün = viel frei, Gelb = mittlere Belegung, Rot = fast voll
    color = "#28a745" if f.occupancy_rate < 0.75 else ("#ffc107" if f.occupancy_rate < 0.90 else "#dc3545")
    
    folium.CircleMarker(
        location=[f.latitude, f.longitude],
        radius=7 + min(15, f.free_spaces // 30),
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.85,
        tooltip=f"<b>{f.name}</b><br>Frei: {f.free_spaces}/{f.total_spaces} ({f.occupancy_rate*100:.0f}% belegt)<br>Tarif: CHF {f.hourly_rate_chf:.2f}/h<br>Gehdistanz: {item['walk_min']} Min."
    ).add_to(m)

st_folium(m, width=1100, height=520)