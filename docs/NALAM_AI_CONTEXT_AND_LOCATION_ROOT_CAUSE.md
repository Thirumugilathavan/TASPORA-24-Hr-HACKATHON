# NALAM AI — Context and Location Root Cause Analysis

## Date: November 13, 2026

## 1. Problem Statement

NALAM AI returned central Coimbatore hospitals regardless of which sub-locality the user asked about. When a user asked "Where is the hospital in Sulur?", the response included Rao Hospital, Ganga Hospital, Sri Ramakrishna Hospital, CMCH and GKNM Hospital — all located in central Coimbatore, not in Sulur.

Additionally, distances such as 1.0 km, 1.3 km and 2.0 km were displayed without the user providing real GPS coordinates.

## 2. Root Cause Analysis

The bug had **three distinct components**:

### Component 1: Post-Query Locality Filter Was Skipped

**File:** `app/ai/tools.py`, line ~241

**Before fix:**
```python
if clean_loc and not is_coimbatore_query:
    # filter facilities by locality
```

**Problem:** The variable `is_coimbatore_query` was `True` for any query mentioning a sub-locality within Coimbatore district (Sulur, Pollachi, Mettupalayam etc.), because these resolve to "Coimbatore" district. Since `is_coimbatore_query` was `True`, the locality filter was completely skipped, and all 33 Coimbatore facilities were returned unfiltered.

**After fix:**
```python
if clean_loc and (not is_coimbatore_query or specific_sub):
    # filter facilities by locality — runs when a sub-locality is specified
```

The new `specific_sub` variable tracks whether the user specified a sub-locality (Sulur, Pollachi, etc.) distinct from "Coimbatore" itself. The filter now runs when the query targets a specific sub-locality.

### Component 2: Distance Calculated From Reference Coordinates, Not User GPS

**File:** `app/ai/tools.py`

**Problem:** When a user said "Sulur", the system looked up Sulur's `REFERENCE_COORDINATES` (11.0267°N, 77.1264°E) and calculated distances from that point. All facilities received calculated distances, creating misleading labels like "1.0 km" and "1.3 km" that appeared to be real distances from the user's location.

**Fix:** Introduced a `user_has_gps: bool = False` parameter. The `distance_km` field is set to `None` unless the user's real GPS coordinates are available. An internal `_sort_dist_km` field is used for ranking purposes only and is never shown to the user.

### Component 3: No Sub-Locality Text Match in Post-Filter

**File:** `app/ai/tools.py`

**Problem:** Even when the locality filter ran, it only checked facility `name` and `address` fields. It did not check `block` or `locality` columns, so facilities tagged with `block: "Sulur"` would not match a "Sulur" text filter.

**Fix:** The post-query filter now checks `name`, `address`, `block`, and `locality` fields. When `specific_sub` is set, distance-only matches are excluded — a facility must match by text in at least one of these fields.

## 3. Before/After Behavior

### Before

| Query | Result |
|---|---|
| "Where is the hospital in Sulur?" | Rao Hospital (1.0 km), Ganga Hospital (1.3 km), Sri Ramakrishna Hospital (2.0 km), CMCH, GKNM Hospital |
| "Show hospitals in Pollachi" | Same central Coimbatore hospitals |
| "Government hospital in Mettupalayam" | Same central Coimbatore hospitals |

### After

| Query | Result |
|---|---|
| "Where is the hospital in Sulur?" | Only Sulur-area facilities, or honest "No verified facility records found for Sulur" with offer to show broader Coimbatore results |
| "Show hospitals in Pollachi" | Only Pollachi-area facilities |
| "Government hospital in Mettupalayam" | Only Mettupalayam government facilities |
| All queries without GPS | No distance shown (only locality name) |
| Queries with real GPS | Real calculated distances shown |

## 4. Intent Classification Fix

### Educational vs. Symptom Queries

A secondary fix was needed in `app/ai/intent_classifier.py`. The symptom detection (Priority 3) was catching educational/informational queries like "What causes severe dehydration and heat stroke?" and classifying them as `SYMPTOM_GUIDANCE` instead of `HEALTH_INFORMATION`.

**Fix:** Added an `educational_phrases` check. Queries containing phrases like "what causes", "how to prevent", "benefits of", "symptoms of" are classified as `HEALTH_INFORMATION` even if they mention symptom keywords.

## 5. Files Modified

| File | Changes |
|---|---|
| `app/ai/tools.py` | Sub-locality filter fix, distance accuracy fix, `user_has_gps` parameter |
| `app/ai/intent_classifier.py` | `SYMPTOM_WITH_FACILITY` intent, `extracted_symptom` field, educational query distinction |
| `app/ai/agent.py` | `_build_symptom_guidance()` method, Branch 3/3B/12 response fixes |

## 6. Tests Added

| Test File | Coverage |
|---|---|
| `tests/test_locality_specific_facility_retrieval.py` | Sulur, Pollachi, Mettupalayam filtering; no fake distances; GPS distance validation |
| `tests/test_symptom_guidance.py` | Fever/headache/dizziness intent classification; educational vs guidance distinction; combined symptom+facility |
| `tests/test_ai_context_switching.py` | Location switching; context inheritance; intent switching; Tamil/Tanglish queries |
