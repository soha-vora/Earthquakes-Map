# =============================
# Combined Earthquake Map (Natural + Human-Induced)
# =============================

import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import MarkerCluster

# -----------------------------
# Step 1: Fetch 24-hour USGS Earthquakes
# -----------------------------
usgs_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
response = requests.get(usgs_url)
data = response.json()

usgs_records = []
for f in data["features"]:
    props = f["properties"]
    coords = f["geometry"]["coordinates"]
    if not coords or props.get("mag") is None:
        continue
    usgs_records.append({
        "place": props.get("place"),
        "magnitude": props.get("mag"),
        "depth_km": coords[2],
        "time": pd.to_datetime(props["time"], unit='ms'),
        "geometry": Point(coords[0], coords[1])
    })

usgs_gdf = gpd.GeoDataFrame(usgs_records, crs="EPSG:4326")

# -----------------------------
# Step 2: Load Human-Induced Earthquakes
# -----------------------------
csv_file = r"C:\Users\sohav\OneDrive\Desktop\realtime-environmental-gis\HiQuake_v2025.09.17.xlsx - HiQuake.csv"
df_induced = pd.read_csv(csv_file)

from shapely.geometry import Point
df_induced.columns = df_induced.columns.str.strip()
df_induced["Latitude (approximate)"] = pd.to_numeric(df_induced["Latitude (approximate)"], errors='coerce')
df_induced["Longitude (approximate)"] = pd.to_numeric(df_induced["Longitude (approximate)"], errors='coerce')

print(df_induced.columns.tolist())

geometry = [Point(xy) for xy in zip(df_induced["Longitude (approximate)"], 
                                    df_induced["Latitude (approximate)"])]
gdf_induced = gpd.GeoDataFrame(df_induced, geometry=geometry)
gdf_induced = gdf_induced.dropna(subset=["Latitude (approximate)", "Longitude (approximate)"])
gdf_induced.set_crs(epsg=4326, inplace=True)
for idx, row in gdf_induced.iterrows():
    print(f"Row {idx}: Longitude={row['Longitude (approximate)']}, Latitude={row['Latitude (approximate)']}")

print(gdf_induced.head())

# -----------------------------
# Step 3: Create Folium Map
# -----------------------------
m = folium.Map(location=[20, 0], zoom_start=2, tiles="OpenStreetMap")

# -----------------------------
# Step 4: Add Natural Earthquakes (USGS)
# -----------------------------
usgs_cluster = MarkerCluster(name="Natural Earthquakes (24h)").add_to(m)
for idx, row in usgs_gdf.iterrows():
    color = 'red' if row['magnitude'] >= 5 else 'orange' if row['magnitude'] >= 3 else 'yellow'
    radius = 3 + row['magnitude']*2
    popup = f"<b>{row['place']}</b><br>Magnitude: {row['magnitude']}<br>Depth: {row['depth_km']} km<br>Time: {row['time']}"
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=radius,
        color=color,
        fill=True,
        fill_opacity=0.7,
        popup=popup
    ).add_to(usgs_cluster)

# -----------------------------
# Step 5: Add Human-Induced Earthquakes
# -----------------------------
induced_cluster = MarkerCluster(name="Human-Induced Earthquakes").add_to(m)
for idx, row in gdf_induced.iterrows():
    mag = row.get("Observed maximum magnitude (Mmax)", 0)
    radius = 3 + mag if pd.notnull(mag) else 3

    popup = f"<b>Project:</b> {row.get('Project name', 'N/A')}<br>"
    popup += f"<b>Maximum magnitude:</b> {row.get('Observed maximum magnitude (Mmax)', 'N/A')}<br>"
    num_quakes = row.get('Number of recorded earthquakes', None)
    if pd.notnull(num_quakes):
        try:
            num_display = int(float(num_quakes))
            popup += f"<b>Number of Recorded Quakes:</b> {num_display}<br>"
        except (ValueError, TypeError):
            pass
    popup += f"<b>Earthquake cause:</b> {row.get('Earthquake cause (main class)', 'N/A')}<br>"
    popup += f"<b>Tectonic Setting:</b> {row.get('Tectonic setting', 'N/A')}"

    folium.CircleMarker(
        location=[row['Latitude (approximate)'], row['Longitude (approximate)']],
        radius=radius,
        color='purple',
        fill=True,
        fill_opacity=0.7,
        popup=popup
    ).add_to(induced_cluster)

# -----------------------------
# Step 6: Add Legend
# -----------------------------
legend_html = """
<div style="
    position: fixed; 
    bottom: 40px; right: 40px; width: 230px; 
    background-color: white; 
    border: 2px solid grey; 
    z-index: 9999; 
    font-size: 14px;
    padding: 10px;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
">
<b>🧭 Earthquake Legend</b><br>
<span style="color:red;">●</span> Natural ≥5.0 magnitude<br>
<span style="color:orange;">●</span> Natural 3.0–4.9 magnitude<br>
<span style="color:yellow;">●</span> Natural &lt;3.0 magnitude<br>
<span style="color:purple;">●</span> Human-Induced<br>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# -----------------------------
# Step 7: Add Layer Control
# -----------------------------
folium.LayerControl(collapsed=False).add_to(m)

# -----------------------------
# Step 8: Save Map
# -----------------------------
map_file = "combined_earthquake_map.html"
m.save(map_file)
print(f"✅ Map saved to {map_file}")