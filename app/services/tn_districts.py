"""
Canonical Tamil Nadu District Registry for NALAM AI.
Covers all 38 revenue districts of Tamil Nadu with official names,
standardized aliases, administrative portal URLs, and district centroid coordinates.
"""

from typing import Dict, List, Optional, Any

# Authoritative list of all 38 revenue districts of Tamil Nadu
TN_DISTRICTS: Dict[str, Dict[str, Any]] = {
    "Ariyalur": {
        "name": "Ariyalur",
        "name_ta": "அரியலூர்",
        "headquarters": "Ariyalur",
        "latitude": 11.1401,
        "longitude": 79.0786,
        "portal_url": "https://ariyalur.nic.in",
        "aliases": ["ariyalur", "arialur"]
    },
    "Chengalpattu": {
        "name": "Chengalpattu",
        "name_ta": "செங்கல்பட்டு",
        "headquarters": "Chengalpattu",
        "latitude": 12.6920,
        "longitude": 79.9760,
        "portal_url": "https://chengalpattu.nic.in",
        "aliases": ["chengalpattu", "chengalpet", "chenglepet"]
    },
    "Chennai": {
        "name": "Chennai",
        "name_ta": "சென்னை",
        "headquarters": "Chennai",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "portal_url": "https://chennai.nic.in",
        "aliases": ["chennai", "madras"]
    },
    "Coimbatore": {
        "name": "Coimbatore",
        "name_ta": "கோயம்புத்தூர்",
        "headquarters": "Coimbatore",
        "latitude": 11.0168,
        "longitude": 76.9558,
        "portal_url": "https://coimbatore.nic.in",
        "aliases": ["coimbatore", "kovai", "cbe"]
    },
    "Cuddalore": {
        "name": "Cuddalore",
        "name_ta": "கடலூர்",
        "headquarters": "Cuddalore",
        "latitude": 11.7480,
        "longitude": 79.7714,
        "portal_url": "https://cuddalore.nic.in",
        "aliases": ["cuddalore", "kadalur"]
    },
    "Dharmapuri": {
        "name": "Dharmapuri",
        "name_ta": "தருமபுரி",
        "headquarters": "Dharmapuri",
        "latitude": 12.1277,
        "longitude": 78.1579,
        "portal_url": "https://dharmapuri.nic.in",
        "aliases": ["dharmapuri", "dharampuri"]
    },
    "Dindigul": {
        "name": "Dindigul",
        "name_ta": "திண்டுக்கல்",
        "headquarters": "Dindigul",
        "latitude": 10.3673,
        "longitude": 77.9803,
        "portal_url": "https://dindigul.nic.in",
        "aliases": ["dindigul", "dindugul"]
    },
    "Erode": {
        "name": "Erode",
        "name_ta": "ஈரோடு",
        "headquarters": "Erode",
        "latitude": 11.3410,
        "longitude": 77.7172,
        "portal_url": "https://erode.nic.in",
        "aliases": ["erode", "erodu"]
    },
    "Kallakurichi": {
        "name": "Kallakurichi",
        "name_ta": "கள்ளக்குறிச்சி",
        "headquarters": "Kallakurichi",
        "latitude": 11.7384,
        "longitude": 78.9639,
        "portal_url": "https://kallakurichi.nic.in",
        "aliases": ["kallakurichi", "kallakurichi"]
    },
    "Kanchipuram": {
        "name": "Kanchipuram",
        "name_ta": "காஞ்சிபுரம்",
        "headquarters": "Kanchipuram",
        "latitude": 12.8342,
        "longitude": 79.7036,
        "portal_url": "https://kancheepuram.nic.in",
        "aliases": ["kanchipuram", "kancheepuram", "kanchi"]
    },
    "Kanniyakumari": {
        "name": "Kanniyakumari",
        "name_ta": "கன்னியாகுமரி",
        "headquarters": "Nagercoil",
        "latitude": 8.0883,
        "longitude": 77.5385,
        "portal_url": "https://kanniyakumari.nic.in",
        "aliases": ["kanniyakumari", "kanyakumari", "kaniyakumari", "nagercoil"]
    },
    "Karur": {
        "name": "Karur",
        "name_ta": "கரூர்",
        "headquarters": "Karur",
        "latitude": 10.9601,
        "longitude": 78.0766,
        "portal_url": "https://karur.nic.in",
        "aliases": ["karur"]
    },
    "Krishnagiri": {
        "name": "Krishnagiri",
        "name_ta": "கிருஷ்ணகிரி",
        "headquarters": "Krishnagiri",
        "latitude": 12.5186,
        "longitude": 78.2137,
        "portal_url": "https://krishnagiri.nic.in",
        "aliases": ["krishnagiri", "hosur"]
    },
    "Madurai": {
        "name": "Madurai",
        "name_ta": "மதுரை",
        "headquarters": "Madurai",
        "latitude": 9.9252,
        "longitude": 78.1198,
        "portal_url": "https://madurai.nic.in",
        "aliases": ["madurai"]
    },
    "Mayiladuthurai": {
        "name": "Mayiladuthurai",
        "name_ta": "மயிலாடுதுறை",
        "headquarters": "Mayiladuthurai",
        "latitude": 11.1075,
        "longitude": 79.6524,
        "portal_url": "https://mayiladuthurai.nic.in",
        "aliases": ["mayiladuthurai", "mayavaram", "mayiladuturai"]
    },
    "Nagapattinam": {
        "name": "Nagapattinam",
        "name_ta": "நாகப்பட்டினம்",
        "headquarters": "Nagapattinam",
        "latitude": 10.7656,
        "longitude": 79.8424,
        "portal_url": "https://nagapattinam.nic.in",
        "aliases": ["nagapattinam", "nagapattinum", "nagai"]
    },
    "Namakkal": {
        "name": "Namakkal",
        "name_ta": "நாமக்கல்",
        "headquarters": "Namakkal",
        "latitude": 11.2189,
        "longitude": 78.1674,
        "portal_url": "https://namakkal.nic.in",
        "aliases": ["namakkal", "namakal"]
    },
    "Nilgiris": {
        "name": "Nilgiris",
        "name_ta": "நீலகிரி",
        "headquarters": "Udhagamandalam",
        "latitude": 11.4102,
        "longitude": 76.6950,
        "portal_url": "https://nilgiris.nic.in",
        "aliases": ["nilgiris", "the nilgiris", "nilgiri", "ooty", "udhagamandalam"]
    },
    "Perambalur": {
        "name": "Perambalur",
        "name_ta": "பெரம்பலூர்",
        "headquarters": "Perambalur",
        "latitude": 11.2342,
        "longitude": 78.8820,
        "portal_url": "https://perambalur.nic.in",
        "aliases": ["perambalur", "peramballur"]
    },
    "Pudukkottai": {
        "name": "Pudukkottai",
        "name_ta": "புதுக்கோட்டை",
        "headquarters": "Pudukkottai",
        "latitude": 10.3797,
        "longitude": 78.8208,
        "portal_url": "https://pudukkottai.nic.in",
        "aliases": ["pudukkottai", "pudukkotai"]
    },
    "Ramanathapuram": {
        "name": "Ramanathapuram",
        "name_ta": "இராமநாதபுரம்",
        "headquarters": "Ramanathapuram",
        "latitude": 9.3639,
        "longitude": 78.8395,
        "portal_url": "https://ramanathapuram.nic.in",
        "aliases": ["ramanathapuram", "ramnad"]
    },
    "Ranipet": {
        "name": "Ranipet",
        "name_ta": "இராணிப்பேட்டை",
        "headquarters": "Ranipet",
        "latitude": 12.9298,
        "longitude": 79.3330,
        "portal_url": "https://ranipet.nic.in",
        "aliases": ["ranipet", "ranipettai"]
    },
    "Salem": {
        "name": "Salem",
        "name_ta": "சேலம்",
        "headquarters": "Salem",
        "latitude": 11.6643,
        "longitude": 78.1460,
        "portal_url": "https://salem.nic.in",
        "aliases": ["salem", "selam"]
    },
    "Sivaganga": {
        "name": "Sivaganga",
        "name_ta": "சிவகங்கை",
        "headquarters": "Sivaganga",
        "latitude": 9.8433,
        "longitude": 78.4809,
        "portal_url": "https://sivaganga.nic.in",
        "aliases": ["sivaganga", "sivagangai"]
    },
    "Tenkasi": {
        "name": "Tenkasi",
        "name_ta": "தென்காசி",
        "headquarters": "Tenkasi",
        "latitude": 8.9594,
        "longitude": 77.3160,
        "portal_url": "https://tenkasi.nic.in",
        "aliases": ["tenkasi"]
    },
    "Thanjavur": {
        "name": "Thanjavur",
        "name_ta": "தஞ்சாவூர்",
        "headquarters": "Thanjavur",
        "latitude": 10.7870,
        "longitude": 79.1378,
        "portal_url": "https://thanjavur.nic.in",
        "aliases": ["thanjavur", "tanjore"]
    },
    "Theni": {
        "name": "Theni",
        "name_ta": "தேனி",
        "headquarters": "Theni",
        "latitude": 10.0104,
        "longitude": 77.4768,
        "portal_url": "https://theni.nic.in",
        "aliases": ["theni", "teni"]
    },
    "Thoothukudi": {
        "name": "Thoothukudi",
        "name_ta": "தூத்துக்குடி",
        "headquarters": "Thoothukudi",
        "latitude": 8.7642,
        "longitude": 78.1348,
        "portal_url": "https://thoothukudi.nic.in",
        "aliases": ["thoothukudi", "tuticorin", "thootukudi"]
    },
    "Tiruchirappalli": {
        "name": "Tiruchirappalli",
        "name_ta": "திருச்சிராப்பள்ளி",
        "headquarters": "Tiruchirappalli",
        "latitude": 10.7905,
        "longitude": 78.7047,
        "portal_url": "https://tiruchirappalli.nic.in",
        "aliases": ["tiruchirappalli", "tiruchirapalli", "tiruchchirappli", "trichy", "tiruchi"]
    },
    "Tirunelveli": {
        "name": "Tirunelveli",
        "name_ta": "திருநெல்வேலி",
        "headquarters": "Tirunelveli",
        "latitude": 8.7139,
        "longitude": 77.7567,
        "portal_url": "https://tirunelveli.nic.in",
        "aliases": ["tirunelveli", "triunelveli", "nellai"]
    },
    "Tirupathur": {
        "name": "Tirupathur",
        "name_ta": "திருப்பத்தூர்",
        "headquarters": "Tirupathur",
        "latitude": 12.4925,
        "longitude": 78.5678,
        "portal_url": "https://tirupathur.nic.in",
        "aliases": ["tirupathur", "tirupattur", "thirupattur", "thirupathur"]
    },
    "Tiruppur": {
        "name": "Tiruppur",
        "name_ta": "திருப்பூர்",
        "headquarters": "Tiruppur",
        "latitude": 11.1085,
        "longitude": 77.3411,
        "portal_url": "https://tiruppur.nic.in",
        "aliases": ["tiruppur", "tirupur"]
    },
    "Tiruvallur": {
        "name": "Tiruvallur",
        "name_ta": "திருவள்ளூர்",
        "headquarters": "Tiruvallur",
        "latitude": 13.1231,
        "longitude": 79.9120,
        "portal_url": "https://tiruvallur.nic.in",
        "aliases": ["tiruvallur", "thiruvallur", "trivallur"]
    },
    "Tiruvannamalai": {
        "name": "Tiruvannamalai",
        "name_ta": "திருவண்ணாமலை",
        "headquarters": "Tiruvannamalai",
        "latitude": 12.2253,
        "longitude": 79.0747,
        "portal_url": "https://tiruvannamalai.nic.in",
        "aliases": ["tiruvannamalai", "thiruvannamalai", "tiruvannamala"]
    },
    "Tiruvarur": {
        "name": "Tiruvarur",
        "name_ta": "திருவாரூர்",
        "headquarters": "Tiruvarur",
        "latitude": 10.7725,
        "longitude": 79.6365,
        "portal_url": "https://tiruvarur.nic.in",
        "aliases": ["tiruvarur", "thiruvarur"]
    },
    "Vellore": {
        "name": "Vellore",
        "name_ta": "வேலூர்",
        "headquarters": "Vellore",
        "latitude": 12.9165,
        "longitude": 79.1325,
        "portal_url": "https://vellore.nic.in",
        "aliases": ["vellore", "velur"]
    },
    "Viluppuram": {
        "name": "Viluppuram",
        "name_ta": "விழுப்புரம்",
        "headquarters": "Viluppuram",
        "latitude": 11.9401,
        "longitude": 79.4861,
        "portal_url": "https://viluppuram.nic.in",
        "aliases": ["viluppuram", "villupuram"]
    },
    "Virudhunagar": {
        "name": "Virudhunagar",
        "name_ta": "விருதுநகர்",
        "headquarters": "Virudhunagar",
        "latitude": 9.5872,
        "longitude": 77.9514,
        "portal_url": "https://virudhunagar.nic.in",
        "aliases": ["virudhunagar", "virudunagar"]
    }
}

# Alias lookup mapping
ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canonical_name, data in TN_DISTRICTS.items():
    ALIAS_TO_CANONICAL[canonical_name.lower()] = canonical_name
    for alias in data.get("aliases", []):
        ALIAS_TO_CANONICAL[alias.lower().strip()] = canonical_name


def get_all_districts() -> List[Dict[str, Any]]:
    """Return all 38 canonical Tamil Nadu districts with metadata."""
    return [
        {
            "name": name,
            "name_ta": data["name_ta"],
            "headquarters": data["headquarters"],
            "latitude": data["latitude"],
            "longitude": data["longitude"],
            "portal_url": data["portal_url"]
        }
        for name, data in sorted(TN_DISTRICTS.items())
    ]


def normalize_tn_district(query: Optional[str]) -> Optional[str]:
    """
    Normalize any variant, misspelling, or historical name of a Tamil Nadu district
    into its canonical 38-district spelling.
    Returns None if not a recognized Tamil Nadu district.
    """
    if not query:
        return None
    cleaned = query.strip().lower()
    if cleaned in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[cleaned]
    # Check substring or partial token match
    for alias, canonical in ALIAS_TO_CANONICAL.items():
        if alias in cleaned or cleaned in alias:
            return canonical
    return None


def get_district_metadata(district_name: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a canonical district."""
    canonical = normalize_tn_district(district_name)
    if canonical and canonical in TN_DISTRICTS:
        return TN_DISTRICTS[canonical]
    return None
