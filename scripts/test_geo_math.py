import json
import math
import time

def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

# Test patient location (e.g. Pune, Maharashtra: lat=18.5204, lon=73.8567)
p_lat, p_lon = 18.5204, 73.8567
radius_km = 10.0

path = r"C:\Users\ssara\Desktop\INDIA_HEALTH_FACILITIES_NIC.geojson"
t0 = time.time()
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Loaded GeoJSON in {time.time() - t0:.2f}s")
features = data.get("features", [])

nearby = []
for feat in features:
    coords = feat.get("geometry", {}).get("coordinates")
    if not coords or len(coords) < 2:
        continue
    lon, lat = float(coords[0]), float(coords[1])
    # Fast bounding box check
    if abs(lat - p_lat) > (radius_km / 111.0):
        continue
    if abs(lon - p_lon) > (radius_km / (111.0 * math.cos(math.radians(p_lat)))):
        continue
    dist = haversine(p_lat, p_lon, lat, lon)
    if dist <= radius_km:
        props = feat.get("properties") or {}
        nearby.append((props.get("name"), props.get("type"), round(dist, 2), dist, lat, lon))

nearby.sort(key=lambda x: (x[3], x[0]))

print(f"Found {len(nearby)} facilities within {radius_km} km of Pune ({p_lat}, {p_lon}):")
for name, ftype, dist_round, dist_exact, lat, lon in nearby[:10]:
    print(f"  {dist_round:.2f} km | {ftype} | {name} ({lat}, {lon})")

