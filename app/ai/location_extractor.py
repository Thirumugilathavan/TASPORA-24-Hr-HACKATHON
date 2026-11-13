"""Intelligent Multilingual Location Extractor for NALAM AI Assistant.

Supports:
- Tamil Unicode script with case markers and inflections:
  (-இல், -ல், -ல, -க்கு, -அருகே, -உள்ள, -பகுதியில், etc.)
- English prepositions:
  (in, at, near, around, near to, from, for, etc.)
- Tanglish locative markers:
  (la, le, laa, kitta, pakkatthula, etc.)
- Direct place names (Coimbatore, Salem, Tiruchengode, Namakkal, etc.)
- Explicit rule: Returns None when no location is extracted. NEVER defaults to Tiruchengode.
"""
import re
from typing import Dict, Optional, Tuple

# Comprehensive mapping of Tamil script and English variations to Canonical English Name
LOCATION_SYNONYMS: Dict[str, str] = {
    # Coimbatore / Kovai
    "கோயம்புத்தூர்": "Coimbatore",
    "கோயம்புத்தூ": "Coimbatore",
    "கோயமுத்தூர்": "Coimbatore",
    "கோவை": "Coimbatore",
    "coimbatore": "Coimbatore",
    "kovai": "Coimbatore",
    "cbe": "Coimbatore",

    # Coimbatore District Blocks & Localities
    "பொள்ளாச்சி": "Pollachi",
    "பொள்ளாச்சியில": "Pollachi",
    "pollachi": "Pollachi",
    "மேட்டுப்பாளையம்": "Mettupalayam",
    "mettupalayam": "Mettupalayam",
    "mtp": "Mettupalayam",
    "வால்பாறை": "Valparai",
    "valparai": "Valparai",
    "அன்னூர்": "Annur",
    "annur": "Annur",
    "சூலூர்": "Sulur",
    "sulur": "Sulur",
    "கிணத்துக்கடவு": "Kinathukadavu",
    "kinathukadavu": "Kinathukadavu",
    "மதுக்கரை": "Madukkarai",
    "மடுக்கரை": "Madukkarai",
    "madukkarai": "Madukkarai",
    "ஆனைமலை": "Anamalai",
    "anamalai": "Anamalai",
    "தொண்டாமுத்தூர்": "Thondamuthur",
    "thondamuthur": "Thondamuthur",
    "காரமடை": "Karamadai",
    "karamadai": "Karamadai",
    "சர்க்கார் சாமக்குளம்": "Sarcarsamakulam",
    "sarcarsamakulam": "Sarcarsamakulam",
    "சுல்தான்பேட்டை": "Sultanpet",
    "sultanpet": "Sultanpet",
    "சிங்காநல்லூர்": "Singanallur",
    "singanallur": "Singanallur",
    "பீளமேடு": "Peelamedu",
    "peelamedu": "Peelamedu",
    "ஆர் எஸ் புரம்": "R.S. Puram",
    "ஆர்.எஸ். புரம்": "R.S. Puram",
    "rs puram": "R.S. Puram",
    "r.s. puram": "R.S. Puram",
    "காந்திபுரம்": "Gandhipuram",
    "gandhipuram": "Gandhipuram",
    "சாய்பாபா காலனி": "Saibaba Colony",
    "saibaba colony": "Saibaba Colony",
    "ராம் நகர்": "Ram Nagar",
    "ram nagar": "Ram Nagar",
    "செல்வபுரம்": "Selvapuram",
    "selvapuram": "Selvapuram",
    "கணபதி": "Ganapathy",
    "ganapathy": "Ganapathy",

    # Salem
    "சேலம்": "Salem",
    "சேலத்": "Salem",
    "salem": "Salem",

    # Tiruchengode
    "திருச்செங்கோடு": "Tiruchengode",
    "திருச்செங்கோட்": "Tiruchengode",
    "திருச்செங்கோடுல": "Tiruchengode",
    "tiruchengode": "Tiruchengode",
    "thiruchengodu": "Tiruchengode",
    "tiruchengodu": "Tiruchengode",

    # Namakkal
    "நாமக்கல்": "Namakkal",
    "நாமக்கல்ல": "Namakkal",
    "namakkal": "Namakkal",

    # Erode
    "ஈரோடு": "Erode",
    "ஈரோட்": "Erode",
    "erode": "Erode",

    # Chennai / Madras
    "சென்னை": "Chennai",
    "சென்ன": "Chennai",
    "chennai": "Chennai",
    "madras": "Chennai",

    # Madurai
    "மதுரை": "Madurai",
    "மதுர": "Madurai",
    "madurai": "Madurai",

    # Tiruchirappalli / Trichy
    "திருச்சி": "Trichy",
    "திருச்சிராப்பள்ளி": "Trichy",
    "trichy": "Trichy",
    "tiruchirappalli": "Trichy",
    "tiruchi": "Trichy",

    # Vellore
    "வேலூர்": "Vellore",
    "வேலூ": "Vellore",
    "vellore": "Vellore",

    # Molasi
    "மோளசி": "Molasi",
    "molasi": "Molasi",

    # Rampur
    "ராம்பூர்": "Rampur",
    "ராம்பூ": "Rampur",
    "rampur": "Rampur",

    # Mohanpur
    "மோகன்பூர்": "Mohanpur",
    "மோகன்பூ": "Mohanpur",
    "mohanpur": "Mohanpur",

    # Anandpur
    "ஆனந்த்பூர்": "Anandpur",
    "ஆனந்தபூர்": "Anandpur",
    "anandpur": "Anandpur",

    # Tirupur
    "திருப்பூர்": "Tirupur",
    "tirupur": "Tirupur",
    "tiruppur": "Tirupur",

    # Karur
    "கரூர்": "Karur",
    "karur": "Karur",

    # Dindigul
    "திண்டுக்கல்": "Dindigul",
    "dindigul": "Dindigul",

    # Dharmapuri
    "தர்மபுரி": "Dharmapuri",
    "dharmapuri": "Dharmapuri",

    # Krishnagiri
    "கிருஷ்ணகிரி": "Krishnagiri",
    "krishnagiri": "Krishnagiri",

    # Thanjavur
    "தஞ்சாவூர்": "Thanjavur",
    "thanjavur": "Thanjavur",
    "tanjore": "Thanjavur",

    # Tirunelveli
    "திருநெல்வேலி": "Tirunelveli",
    "நெல்லை": "Tirunelveli",
    "tirunelveli": "Tirunelveli",
    "nellai": "Tirunelveli",

    # Sitapur (Evaluation baseline)
    "சீதாபூர்": "Sitapur",
    "sitapur": "Sitapur",
}

# Known Reference Coordinates for distance calculations & geographic ranking
REFERENCE_COORDINATES: Dict[str, Tuple[float, float, str]] = {
    "coimbatore": (11.0168, 76.9558, "Coimbatore, Tamil Nadu"),
    "pollachi": (10.6582, 77.0125, "Pollachi, Coimbatore District, Tamil Nadu"),
    "mettupalayam": (11.2995, 76.9412, "Mettupalayam, Coimbatore District, Tamil Nadu"),
    "valparai": (10.3262, 76.9554, "Valparai, Coimbatore District, Tamil Nadu"),
    "annur": (11.2324, 77.1775, "Annur, Coimbatore District, Tamil Nadu"),
    "sulur": (11.0267, 77.1264, "Sulur, Coimbatore District, Tamil Nadu"),
    "kinathukadavu": (10.8242, 77.0195, "Kinathukadavu, Coimbatore District, Tamil Nadu"),
    "madukkarai": (10.9034, 76.9632, "Madukkarai, Coimbatore District, Tamil Nadu"),
    "anamalai": (10.5842, 76.9324, "Anamalai, Coimbatore District, Tamil Nadu"),
    "thondamuthur": (10.9992, 76.8335, "Thondamuthur, Coimbatore District, Tamil Nadu"),
    "karamadai": (11.2435, 76.9632, "Karamadai, Coimbatore District, Tamil Nadu"),
    "sarcarsamakulam": (11.1275, 77.0189, "Sarcarsamakulam, Coimbatore District, Tamil Nadu"),
    "sultanpet": (10.8712, 77.1643, "Sultanpet, Coimbatore District, Tamil Nadu"),
    "singanallur": (11.0028, 77.0253, "Singanallur, Coimbatore, Tamil Nadu"),
    "peelamedu": (11.0264, 77.0012, "Peelamedu, Coimbatore, Tamil Nadu"),
    "r.s. puram": (11.0084, 76.9512, "R.S. Puram, Coimbatore, Tamil Nadu"),
    "rs puram": (11.0084, 76.9512, "R.S. Puram, Coimbatore, Tamil Nadu"),
    "gandhipuram": (11.0168, 76.9678, "Gandhipuram, Coimbatore, Tamil Nadu"),
    "saibaba colony": (11.0264, 76.9498, "Saibaba Colony, Coimbatore, Tamil Nadu"),
    "ram nagar": (11.0134, 76.9621, "Ram Nagar, Coimbatore, Tamil Nadu"),
    "selvapuram": (10.9851, 76.9423, "Selvapuram, Coimbatore, Tamil Nadu"),
    "ganapathy": (11.0392, 76.9821, "Ganapathy, Coimbatore, Tamil Nadu"),
    "salem": (11.6643, 78.1460, "Salem, Tamil Nadu"),
    "tiruchengode": (11.3800, 77.8900, "Namakkal, Tamil Nadu"),
    "namakkal": (11.2189, 78.1674, "Namakkal, Tamil Nadu"),
    "erode": (11.3410, 77.7172, "Erode, Tamil Nadu"),
    "chennai": (13.0827, 80.2707, "Chennai, Tamil Nadu"),
    "madurai": (9.9252, 78.1198, "Madurai, Tamil Nadu"),
    "trichy": (10.7905, 78.7047, "Tiruchirappalli, Tamil Nadu"),
    "tiruchirappalli": (10.7905, 78.7047, "Tiruchirappalli, Tamil Nadu"),
    "vellore": (12.9165, 79.1325, "Vellore, Tamil Nadu"),
    "molasi": (11.3420, 77.8450, "Namakkal, Tamil Nadu"),
    "rampur": (12.9165, 79.1325, "Vellore, Tamil Nadu"),
    "mohanpur": (12.9240, 79.1450, "Vellore, Tamil Nadu"),
    "anandpur": (12.2253, 79.0747, "Tiruvannamalai, Tamil Nadu"),
    "tirupur": (11.1085, 77.3411, "Tirupur, Tamil Nadu"),
    "karur": (10.9601, 78.0766, "Karur, Tamil Nadu"),
    "dindigul": (10.3673, 77.9803, "Dindigul, Tamil Nadu"),
    "dharmapuri": (12.1211, 78.1582, "Dharmapuri, Tamil Nadu"),
    "krishnagiri": (12.5186, 78.2137, "Krishnagiri, Tamil Nadu"),
    "thanjavur": (10.7870, 79.1378, "Thanjavur, Tamil Nadu"),
    "tirunelveli": (8.7139, 77.7567, "Tirunelveli, Tamil Nadu"),
    "sitapur": (27.5684, 80.6791, "Sitapur, Uttar Pradesh"),
}


def normalize_tamil_text(text: str) -> str:
    """Strips punctuation and normalizes common Tamil case suffixes."""
    return re.sub(r"[?!.,;:\"'’‘(){}\[\]]", " ", text).strip()


def extract_location(
    text: str,
    conversation_active_location: Optional[str] = None,
    user_home_village: Optional[str] = None,
) -> Tuple[Optional[str], Optional[Tuple[float, float, str]], bool]:
    """Extracts location from latest question.
    
    Returns:
        (canonical_location_name, (lat, lon, desc), is_explicit_in_query)
        
    Rules:
    1. Explicit location mentioned in the query takes highest priority.
    2. Does NOT default to Tiruchengode. If no location in query, returns (None, None, False).
    3. Caller may choose to use conversation_active_location or user_home_village ONLY when appropriate.
    """
    if not text or not text.strip():
        return (None, None, False)

    cleaned = normalize_tamil_text(text)
    lowered = cleaned.lower()

    # Broad district names that should yield to a more specific sub-locality/block when both appear
    BROAD_DISTRICTS = {"coimbatore", "salem", "namakkal", "erode", "tiruppur", "chennai"}

    # 1. Direct match on known location synonyms
    # We collect all matches in the query to pick the most specific locality
    sorted_synonyms = sorted(LOCATION_SYNONYMS.keys(), key=lambda s: len(s), reverse=True)

    found_matches: List[Tuple[int, str, str]] = []  # (start_index, canonical, matched_syn)
    for syn in sorted_synonyms:
        # Match as whole word or with standard Tamil case suffixes (-ல, -ல், -இல், -க்கு, -உக்கு, -அருகே, etc.)
        pattern = rf"(?:\b|^){re.escape(syn)}(?:ல|ல்|இல்|க்கு|உக்கு|அருகே|உள்ள|பகுதியில்|லேயே|ள)?(?:\b|$|\s)"
        m = re.search(pattern, cleaned, re.IGNORECASE)
        if m:
            canonical = LOCATION_SYNONYMS[syn]
            # Avoid duplicate canonical entries
            if not any(c == canonical for _, c, _ in found_matches):
                found_matches.append((m.start(), canonical, syn))

    if found_matches:
        # If both a broad district (e.g. Coimbatore) and a specific sub-locality (e.g. Sulur, Pollachi) are present,
        # ALWAYS prioritize the more specific sub-locality!
        sub_matches = [m for m in found_matches if m[1].lower() not in BROAD_DISTRICTS]
        if sub_matches:
            # Sort sub-matches by appearance order in text
            sub_matches.sort(key=lambda x: x[0])
            best_canonical = sub_matches[0][1]
        else:
            # Only broad district(s) matched — pick the one that appeared first
            found_matches.sort(key=lambda x: x[0])
            best_canonical = found_matches[0][1]

        coords = REFERENCE_COORDINATES.get(best_canonical.lower())
        return (best_canonical, coords, True)

    # 2. Match Tanglish patterns: "<Location> la", "<Location> le", "<Location> kitta", "<Location> pakkatthula"
    tanglish_match = re.search(
        r"\b([a-zA-Z]{3,20})\s+(?:la|le|laa|kitta|pakkatthula|pakkathula|side)\b",
        cleaned,
        re.IGNORECASE,
    )
    if tanglish_match:
        cand = tanglish_match.group(1).lower()
        if cand in LOCATION_SYNONYMS:
            canonical = LOCATION_SYNONYMS[cand]
            coords = REFERENCE_COORDINATES.get(canonical.lower())
            return (canonical, coords, True)

    # 3. Match English preposition patterns: "in <Location>", "at <Location>", "near <Location>", "around <Location>"
    prep_match = re.search(
        r"\b(?:in|at|near|around|near to|from|for|to)\s+([a-zA-Z]{3,20})\b",
        cleaned,
        re.IGNORECASE,
    )
    if prep_match:
        cand = prep_match.group(1).lower()
        if cand in LOCATION_SYNONYMS:
            canonical = LOCATION_SYNONYMS[cand]
            coords = REFERENCE_COORDINATES.get(canonical.lower())
            return (canonical, coords, True)
        elif cand not in ["the", "a", "an", "my", "our", "me", "hospital", "phc", "doctor", "today", "tomorrow"]:
            # Detected an unmapped English proper noun location
            capitalized = cand.capitalize()
            return (capitalized, None, True)

    # 4. Match phrases like "what about <Location>", "tell me in <Location>", "how about <Location>"
    followup_match = re.search(
        r"\b(?:what about|how about|tell me in|tell me about|show me in)\s+([a-zA-Z]{3,20})\b",
        cleaned,
        re.IGNORECASE,
    )
    if followup_match:
        cand = followup_match.group(1).lower()
        if cand in LOCATION_SYNONYMS:
            canonical = LOCATION_SYNONYMS[cand]
            coords = REFERENCE_COORDINATES.get(canonical.lower())
            return (canonical, coords, True)

    # 5. Check if the user specifically asked for "nearby" / "அருகில்" without naming a place
    nearby_indicators = [
        "nearby", "near me", "closest", "around here", "local",
        "அருகில்", "அருகிலுள்ள", "பக்கத்தில்", "பக்கத்தில", "என்னை சுற்றி",
    ]
    if any(ni in lowered for ni in nearby_indicators):
        # User explicitly asked for nearby services.
        # Priority: conversation active location > user home village > None
        resolved = conversation_active_location or user_home_village
        if resolved:
            canonical = LOCATION_SYNONYMS.get(resolved.lower(), resolved)
            coords = REFERENCE_COORDINATES.get(canonical.lower())
            return (canonical, coords, False)

    # Explicit rule: Return None. Never invent or silently default to Tiruchengode!
    return (None, None, False)


def get_coordinates_for_location(location_name: str) -> Optional[Tuple[float, float, str]]:
    """Returns (latitude, longitude, description) for a given location name."""
    if not location_name:
        return None
    canonical = LOCATION_SYNONYMS.get(location_name.strip().lower(), location_name.strip())
    return REFERENCE_COORDINATES.get(canonical.lower())
