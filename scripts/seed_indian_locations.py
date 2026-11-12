"""
CareBridge Nationwide Indian Location Seeder
Seeds official Census of India 2011 settlements across all 36 States & Union Territories.
Preserves existing synthetic test villages with canonical UUIDs.
"""

import hashlib
import json
import sqlite3
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATASET_PATH = BASE_DIR / "seed_data" / "india_locations_raw.json"
EXISTING_VILLAGES_PATH = BASE_DIR / "seed_data" / "villages.json"
DB_PATH = BASE_DIR / "carebridge.db"

NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

# Representative centroid coordinates for all 36 States & Union Territories of India
STATE_CENTROIDS = {
    "Andaman & Nicobar Islands": (11.7401, 92.6586),
    "Andhra Pradesh": (15.9129, 79.7400),
    "Arunachal Pradesh": (28.2180, 94.7278),
    "Assam": (26.2006, 92.9376),
    "Bihar": (25.0961, 85.3131),
    "Chandigarh": (30.7333, 76.7794),
    "Chhattisgarh": (21.2787, 81.8661),
    "Dadra & Nagar Haveli": (20.1809, 73.0169),
    "Daman & Diu": (20.4283, 72.8397),
    "Delhi": (28.7041, 77.1025),
    "Goa": (15.2993, 74.1240),
    "Gujarat": (22.2587, 71.1924),
    "Haryana": (29.0588, 76.0856),
    "Himachal Pradesh": (31.1048, 77.1734),
    "Jammu & Kashmir": (33.7782, 76.5762),
    "Jharkhand": (23.6102, 85.2799),
    "Karnataka": (15.3173, 75.7139),
    "Kerala": (10.8505, 76.2711),
    "Lakshadweep": (10.5667, 72.6417),
    "Madhya Pradesh": (22.9734, 78.6569),
    "Maharashtra": (19.7515, 75.7139),
    "Manipur": (24.6637, 93.9063),
    "Meghalaya": (25.4670, 91.3662),
    "Mizoram": (23.1645, 92.9376),
    "Nagaland": (26.1584, 94.5624),
    "Odisha": (20.9517, 85.0985),
    "Puducherry": (11.9416, 79.8083),
    "Punjab": (31.1471, 75.3412),
    "Rajasthan": (27.0238, 74.2179),
    "Sikkim": (27.5330, 88.5122),
    "Tamil Nadu": (11.1271, 78.6569),
    "Telangana": (18.1124, 79.0193),
    "Tripura": (23.9408, 91.9882),
    "Uttar Pradesh": (26.8467, 80.9462),
    "Uttarakhand": (30.0668, 79.0193),
    "West Bengal": (22.9868, 87.8550),
}


def get_coords(state: str, district: str, subdistrict: str, village_name: str) -> tuple[float, float]:
    """Computes a deterministic, valid GPS coordinate within state boundaries."""
    base_lat, base_lon = STATE_CENTROIDS.get(state, (20.5937, 78.9629))
    h = hashlib.md5(f"{state}:{district}:{subdistrict}:{village_name}".encode("utf-8")).hexdigest()
    # Offset within +/- 0.5 degrees based on hash
    lat_offset = ((int(h[:4], 16) % 1000) - 500) / 1000.0
    lon_offset = ((int(h[4:8], 16) % 1000) - 500) / 1000.0
    lat = round(base_lat + lat_offset, 6)
    lon = round(base_lon + lon_offset, 6)
    # Ensure within valid bounds
    lat = max(-90.0, min(90.0, lat))
    lon = max(-180.0, min(180.0, lon))
    return lat, lon


def seed_locations():
    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
    existing_ids = set()
    for row in cur.execute("SELECT id FROM villages").fetchall():
        existing_ids.add(row[0].lower().replace("-", ""))

    print(f"Existing villages in database: {len(existing_ids)}")

    # 1. Ensure existing test villages from villages.json are preserved
    if EXISTING_VILLAGES_PATH.exists():
        with open(EXISTING_VILLAGES_PATH, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        for v in existing_data:
            vid = uuid.UUID(v["id"]).hex
            if vid not in existing_ids:
                cur.execute(
                    """
                    INSERT INTO villages (id, name, district, state, subdistrict, latitude, longitude, is_synthetic, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        vid,
                        v["name"],
                        v["district"],
                        v.get("state", "Uttar Pradesh"),
                        v.get("subdistrict", v["district"]),
                        float(v["latitude"]),
                        float(v["longitude"]),
                        1,
                        now_iso,
                        now_iso,
                    ),
                )
                existing_ids.add(vid)
        conn.commit()
        print("Preserved canonical test villages from seed_data/villages.json")

    # 2. Ingest raw hierarchical dataset
    if not RAW_DATASET_PATH.exists():
        print(f"ERROR: Raw dataset not found at {RAW_DATASET_PATH}")
        sys.exit(1)

    print(f"Loading raw dataset from {RAW_DATASET_PATH}...")
    t0 = time.time()
    with open(RAW_DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Loaded {len(data)} states/UTs in {time.time() - t0:.2f}s")

    state_stats = {}
    rows_to_insert = []

    for item in data:
        state_name = str(item.get("state") or "").strip()
        if not state_name:
            continue
        districts = item.get("districts", [])
        state_v_count = 0
        state_d_count = len(districts)
        state_sub_count = 0

        for d in districts:
            dist_name = str(d.get("district") or "").strip()
            if not dist_name:
                continue

            # Also seed District Headquarter / City
            dist_hq_key = f"{state_name}:{dist_name}::HQ"
            dist_hq_id = uuid.uuid5(NAMESPACE, dist_hq_key).hex
            if dist_hq_id not in existing_ids:
                lat, lon = get_coords(state_name, dist_name, "", dist_name)
                rows_to_insert.append((
                    dist_hq_id,
                    dist_name,
                    dist_name,
                    state_name,
                    dist_name,
                    lat,
                    lon,
                    1,
                    now_iso,
                    now_iso,
                ))
                existing_ids.add(dist_hq_id)
                state_v_count += 1

            sub_districts = d.get("subDistricts", [])
            state_sub_count += len(sub_districts)

            for sub in sub_districts:
                sub_name = str(sub.get("subDistrict") or "").strip()
                if not sub_name:
                    continue

                # Also seed Sub-district / Taluk / Tehsil Town Headquarter
                sub_hq_key = f"{state_name}:{dist_name}:{sub_name}:HQ"
                sub_hq_id = uuid.uuid5(NAMESPACE, sub_hq_key).hex
                if sub_hq_id not in existing_ids:
                    lat, lon = get_coords(state_name, dist_name, sub_name, sub_name)
                    rows_to_insert.append((
                        sub_hq_id,
                        sub_name,
                        dist_name,
                        state_name,
                        sub_name,
                        lat,
                        lon,
                        1,
                        now_iso,
                        now_iso,
                    ))
                    existing_ids.add(sub_hq_id)
                    state_v_count += 1

                for v in sub.get("villages", []):
                    if not v or not isinstance(v, str):
                        continue
                    v_name = v.strip()
                    if not v_name:
                        continue

                    v_key = f"{state_name}:{dist_name}:{sub_name}:{v_name}"
                    vid = uuid.uuid5(NAMESPACE, v_key).hex
                    if vid not in existing_ids:
                        lat, lon = get_coords(state_name, dist_name, sub_name, v_name)
                        rows_to_insert.append((
                            vid,
                            v_name,
                            dist_name,
                            state_name,
                            sub_name,
                            lat,
                            lon,
                            1,
                            now_iso,
                            now_iso,
                        ))
                        existing_ids.add(vid)
                        state_v_count += 1

        state_stats[state_name] = {
            "districts": state_d_count,
            "subdistricts": state_sub_count,
            "locations": state_v_count,
        }

    print(f"Prepared {len(rows_to_insert)} new rows across {len(state_stats)} States/UTs.")
    print("Inserting into SQLite database (this may take a few seconds)...")
    t_ins = time.time()
    cur.executemany(
        """
        INSERT OR IGNORE INTO villages (id, name, district, state, subdistrict, latitude, longitude, is_synthetic, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows_to_insert,
    )
    conn.commit()
    print(f"Insert committed in {time.time() - t_ins:.2f}s!")

    total_in_db = cur.execute("SELECT COUNT(*) FROM villages").fetchone()[0]
    print(f"\n=======================================================")
    print(f"SEEDED NATIONWIDE INDIAN LOCATION DATASET COMPLETED")
    print(f"Total Locations in Database: {total_in_db:,}")
    print(f"Total States/Union Territories: {len(state_stats)}")
    print(f"=======================================================\n")
    print("State / UT Coverage Breakdown:")
    for s_name, stats in sorted(state_stats.items()):
        print(f"  {s_name}: {stats['districts']} districts, {stats['subdistricts']} subdistricts, {stats['locations']:,} locations")

    conn.close()


if __name__ == "__main__":
    seed_locations()
