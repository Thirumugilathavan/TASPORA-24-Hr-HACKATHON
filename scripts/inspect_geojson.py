import json
from collections import Counter

path = r"C:\Users\ssara\Desktop\INDIA_HEALTH_FACILITIES_NIC.geojson"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

features = data.get("features", [])
types_counter = Counter()
layers_counter = Counter()
states_counter = Counter()

for feat in features:
    props = feat.get("properties") or {}
    types_counter[props.get("type")] += 1
    layers_counter[props.get("layer")] += 1
    states_counter[props.get("state")] += 1

print("Facility Types:")
for t, cnt in types_counter.most_common():
    print(f"  {t}: {cnt:,}")

print("\nLayers:")
for l, cnt in layers_counter.most_common():
    print(f"  {l}: {cnt:,}")

print(f"\nTotal States in facilities dataset: {len(states_counter)}")
print("Top 10 States by facility count:")
for s, cnt in states_counter.most_common(10):
    print(f"  {s}: {cnt:,}")
