"""
CareBridge Healthcare Facilities Importer
Imports official Government of India healthcare facilities from INDIA_HEALTH_FACILITIES_NIC.geojson
into the CareBridge facilities registry.
Idempotent, validated, and batched.
"""

import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "carebridge.db"

# Possible paths for GeoJSON file
POSSIBLE_GEOJSON_PATHS = [
    Path(r"C:\Users\ssara\Desktop\INDIA_HEALTH_FACILITIES_NIC.geojson"),
    BASE_DIR / "seed_data" / "INDIA_HEALTH_FACILITIES_NIC.geojson",
    Path(os.path.expanduser("~/Desktop/INDIA_HEALTH_FACILITIES_NIC.geojson")),
]

NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

# Government facility types tracked by National Informatics Centre (NIC)
GOV_LAYERS = {
    "sub_center": "Sub-Centre",
    "primary_health_centre": "Primary Health Centre (PHC)",
    "community_health_centre": "Community Health Centre (CHC)",
    "taluk_hospital": "Taluk Sub-District Hospital",
    "district_hospital": "District Hospital",
}


def find_geojson() -> Path:
    for p in POSSIBLE_GEOJSON_PATHS:
        if p.exists() and p.is_file():
            return p
    raise FileNotFoundError(
        f"INDIA_HEALTH_FACILITIES_NIC.geojson not found in searched locations: {[str(p) for p in POSSIBLE_GEOJSON_PATHS]}"
    )


def import_facilities():
    geojson_path = find_geojson()
    print(f"================================================================")
    print(f"CAREBRIDGE HEALTHCARE FACILITIES IMPORT")
    print(f"Source file: {geojson_path}")
    print(f"Target DB:   {DB_PATH}")
    print(f"================================================================\n")

    t0 = time.time()
    print("Reading and parsing GeoJSON (this may take ~1-2 seconds)...")
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"Loaded {len(features):,} features in {time.time() - t0:.2f}s.\n")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Track existing IDs in DB to accurately report new vs duplicates
    existing_ids = set()
    for row in cur.execute("SELECT id FROM facilities").fetchall():
        existing_ids.add(row[0].lower().replace("-", ""))
    print(f"Pre-existing facilities in database: {len(existing_ids):,}")

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

    imported_count = 0
    duplicate_count = 0
    invalid_count = 0
    skipped_count = 0

    batch = []
    BATCH_SIZE = 5000

    type_counts = {}
    state_counts = {}

    t_import_start = time.time()

    for idx, feat in enumerate(features):
        if not feat or not isinstance(feat, dict):
            skipped_count += 1
            continue

        geom = feat.get("geometry")
        if not geom or not isinstance(geom, dict):
            invalid_count += 1
            continue

        coords = geom.get("coordinates")
        if not coords or len(coords) < 2:
            invalid_count += 1
            continue

        try:
            lon = float(coords[0])
            lat = float(coords[1])
        except (ValueError, TypeError):
            invalid_count += 1
            continue

        # Strict coordinate validation
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            invalid_count += 1
            continue

        props = feat.get("properties") or {}
        raw_name = str(props.get("name") or "").strip()
        if not raw_name:
            raw_name = "Government Health Center"

        raw_type = str(props.get("type") or "PHC").strip().upper()
        if not raw_type:
            raw_type = "PHC"

        place = str(props.get("place") or "").strip()
        district = str(props.get("district") or "").strip()
        state = str(props.get("state") or "").strip()
        layer = str(props.get("layer") or "").strip().lower()
        source = str(props.get("source") or "nic").strip().lower()
        source_id = str(props.get("source_id") or f"{idx}")

        # Construct authentic address
        address_parts = [p for p in [place, district, state] if p]
        address = ", ".join(address_parts) if address_parts else f"{raw_name}, {district}"
        if len(address) > 500:
            address = address[:497] + "..."

        # Determine ownership based on official NIC layer metadata
        if layer in GOV_LAYERS or raw_type in ("PHC", "CHC", "SCE", "THO", "DHO"):
            ownership = "Government"
        else:
            ownership = "Unknown"

        # Deterministic UUID5 for idempotent re-runs
        dedup_key = f"nic:{source_id}:{raw_name}:{round(lat, 6)}:{round(lon, 6)}"
        fac_uuid = uuid.uuid5(NAMESPACE, dedup_key)
        fac_id_hex = fac_uuid.hex

        if fac_id_hex in existing_ids:
            duplicate_count += 1
            continue

        contact_meta = {
            "place": place,
            "layer": layer,
            "source": source,
            "source_id": source_id,
            "nic_village_id": props.get("village_id"),
            "ownership_category": ownership,
            "verified_by": "National Informatics Centre (NIC)",
        }

        # Truncate strings to schema boundaries
        clean_name = raw_name[:255]
        clean_type = raw_type[:50]
        clean_district = district[:255]
        clean_state = state[:100]
        clean_subdistrict = place[:255]

        batch.append((
            fac_id_hex,
            clean_name,
            clean_type,
            address,
            None,  # village_id
            clean_district,
            clean_state,
            clean_subdistrict,
            round(lat, 6),
            round(lon, 6),
            ownership,
            source,
            source_id,
            json.dumps(contact_meta),
            now_iso,
            now_iso,
        ))

        existing_ids.add(fac_id_hex)
        imported_count += 1

        type_counts[clean_type] = type_counts.get(clean_type, 0) + 1
        state_counts[clean_state] = state_counts.get(clean_state, 0) + 1

        if len(batch) >= BATCH_SIZE:
            cur.executemany(
                """
                INSERT OR IGNORE INTO facilities (
                    id, name, facility_type, address, village_id, district, state,
                    subdistrict, latitude, longitude, ownership, source, source_id,
                    contact_details, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )
            conn.commit()
            batch = []
            print(f"  Processed {imported_count:,} facilities...")

    if batch:
        cur.executemany(
            """
            INSERT OR IGNORE INTO facilities (
                id, name, facility_type, address, village_id, district, state,
                subdistrict, latitude, longitude, ownership, source, source_id,
                contact_details, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )
        conn.commit()

    conn.close()
    dt = time.time() - t_import_start

    print(f"\n================================================================")
    print(f"IMPORT COMPLETE IN {dt:.2f}s")
    print(f"Total Facilities Successfully Imported: {imported_count:,}")
    print(f"Duplicate Records Skipped:              {duplicate_count:,}")
    print(f"Invalid / Malformed Records:            {invalid_count:,}")
    print(f"Empty Records Skipped:                  {skipped_count:,}")
    print(f"================================================================\n")

    print("Breakdown by Facility Type:")
    for ft, cnt in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ft}: {cnt:,}")

    print("\nTop 10 States:")
    for st, cnt in sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {st or 'Unknown'}: {cnt:,}")


if __name__ == "__main__":
    import_facilities()
