import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

# Indian PIN code regex: 6 digits, first digit 1-9
PINCODE_REGEX = re.compile(r"^[1-9]\d{5}$")

# Official Postal Zone / Circle mappings across all Indian states and regions
POSTAL_CIRCLES: Dict[str, Dict[str, Any]] = {
    # 11: Delhi
    "11": {"state": "Delhi", "district": "Central Delhi", "locality": "Delhi Postal Region", "latitude": 28.6139, "longitude": 77.2090},
    # 12-13: Haryana
    "12": {"state": "Haryana", "district": "Gurugram / Rohtak", "locality": "South Haryana Region", "latitude": 28.4595, "longitude": 77.0266},
    "13": {"state": "Haryana", "district": "Ambala / Karnal", "locality": "North Haryana Region", "latitude": 30.3782, "longitude": 76.7767},
    # 14-16: Punjab & Chandigarh
    "14": {"state": "Punjab", "district": "Ludhiana / Jalandhar", "locality": "Central Punjab Region", "latitude": 30.9010, "longitude": 75.8573},
    "15": {"state": "Punjab", "district": "Bathinda / Firozpur", "locality": "South-West Punjab Region", "latitude": 30.2110, "longitude": 74.9455},
    "16": {"state": "Chandigarh", "district": "Chandigarh", "locality": "Chandigarh Postal Region", "latitude": 30.7333, "longitude": 76.7794},
    # 17: Himachal Pradesh
    "17": {"state": "Himachal Pradesh", "district": "Shimla / Kangra", "locality": "Himachal Postal Region", "latitude": 31.1048, "longitude": 77.1734},
    # 18-19: Jammu & Kashmir / Ladakh
    "18": {"state": "Jammu & Kashmir", "district": "Jammu", "locality": "Jammu Region", "latitude": 32.7266, "longitude": 74.8570},
    "19": {"state": "Jammu & Kashmir", "district": "Srinagar", "locality": "Kashmir & Ladakh Region", "latitude": 34.0837, "longitude": 74.7973},
    # 20-28: Uttar Pradesh & Uttarakhand
    "20": {"state": "Uttar Pradesh", "district": "Agra / Aligarh", "locality": "Western Uttar Pradesh", "latitude": 27.1767, "longitude": 78.0081},
    "21": {"state": "Uttar Pradesh", "district": "Prayagraj / Fatehpur", "locality": "Allahabad Region", "latitude": 25.4358, "longitude": 81.8463},
    "22": {"state": "Uttar Pradesh", "district": "Lucknow / Ayodhya", "locality": "Central Uttar Pradesh", "latitude": 26.8467, "longitude": 80.9462},
    "23": {"state": "Uttar Pradesh", "district": "Varanasi / Mirzapur", "locality": "Eastern Uttar Pradesh", "latitude": 25.3176, "longitude": 82.9739},
    "24": {"state": "Uttarakhand", "district": "Dehradun / Haridwar", "locality": "Uttarakhand Region", "latitude": 30.3165, "longitude": 78.0322},
    "25": {"state": "Uttar Pradesh", "district": "Meerut / Muzaffarnagar", "locality": "Upper Doab Region", "latitude": 28.9845, "longitude": 77.7064},
    "26": {"state": "Uttar Pradesh", "district": "Sitapur / Bareilly", "locality": "Rohilkhand Region", "latitude": 27.5684, "longitude": 80.6791},
    "27": {"state": "Uttar Pradesh", "district": "Gorakhpur / Azamgarh", "locality": "Purvanchal Region", "latitude": 26.7606, "longitude": 83.3732},
    "28": {"state": "Uttar Pradesh", "district": "Jhansi / Lalitpur", "locality": "Bundelkhand Region", "latitude": 25.4484, "longitude": 78.5685},
    # 30-34: Rajasthan
    "30": {"state": "Rajasthan", "district": "Jaipur", "locality": "Jaipur Region", "latitude": 26.9124, "longitude": 75.7873},
    "31": {"state": "Rajasthan", "district": "Udaipur / Kota", "locality": "Southern Rajasthan", "latitude": 24.5854, "longitude": 73.7125},
    "32": {"state": "Rajasthan", "district": "Ajmer / Bharatpur", "locality": "Central Rajasthan", "latitude": 26.4499, "longitude": 74.6399},
    "33": {"state": "Rajasthan", "district": "Bikaner / Sikar", "locality": "Northern Rajasthan", "latitude": 28.0229, "longitude": 73.3119},
    "34": {"state": "Rajasthan", "district": "Jodhpur / Barmer", "locality": "Western Rajasthan", "latitude": 26.2389, "longitude": 73.0243},
    # 36-39: Gujarat
    "36": {"state": "Gujarat", "district": "Rajkot / Jamnagar", "locality": "Saurashtra Region", "latitude": 22.3039, "longitude": 70.8022},
    "37": {"state": "Gujarat", "district": "Kutch", "locality": "Kutch Region", "latitude": 23.2420, "longitude": 69.6669},
    "38": {"state": "Gujarat", "district": "Ahmedabad / Gandhinagar", "locality": "North Gujarat", "latitude": 23.0225, "longitude": 72.5714},
    "39": {"state": "Gujarat", "district": "Surat / Vadodara", "locality": "South Gujarat", "latitude": 21.1702, "longitude": 72.8311},
    # 40-44: Maharashtra & Goa
    "40": {"state": "Maharashtra", "district": "Mumbai / Konkan", "locality": "Mumbai & Konkan Region", "latitude": 18.9402, "longitude": 72.8354},
    "41": {"state": "Maharashtra", "district": "Pune / Solapur", "locality": "Western Maharashtra", "latitude": 18.5204, "longitude": 73.8567},
    "42": {"state": "Maharashtra", "district": "Nashik / Jalgaon", "locality": "Khandesh Region", "latitude": 19.9975, "longitude": 73.7898},
    "43": {"state": "Maharashtra", "district": "Chhatrapati Sambhajinagar", "locality": "Marathwada Region", "latitude": 19.8762, "longitude": 75.3433},
    "44": {"state": "Maharashtra", "district": "Nagpur / Amravati", "locality": "Vidarbha Region", "latitude": 21.1458, "longitude": 79.0882},
    # 45-48: Madhya Pradesh
    "45": {"state": "Madhya Pradesh", "district": "Indore / Ujjain", "locality": "Malwa Region", "latitude": 22.7196, "longitude": 75.8577},
    "46": {"state": "Madhya Pradesh", "district": "Bhopal", "locality": "Central Madhya Pradesh", "latitude": 23.2599, "longitude": 77.4126},
    "47": {"state": "Madhya Pradesh", "district": "Gwalior", "locality": "Chambal Region", "latitude": 26.2183, "longitude": 78.1828},
    "48": {"state": "Madhya Pradesh", "district": "Jabalpur", "locality": "Mahakoshal Region", "latitude": 23.1815, "longitude": 79.9864},
    # 49: Chhattisgarh
    "49": {"state": "Chhattisgarh", "district": "Raipur / Bilaspur", "locality": "Chhattisgarh Region", "latitude": 21.2514, "longitude": 81.6296},
    # 50: Telangana
    "50": {"state": "Telangana", "district": "Hyderabad / Warangal", "locality": "Telangana Postal Region", "latitude": 17.3850, "longitude": 78.4867},
    # 51-53: Andhra Pradesh
    "51": {"state": "Andhra Pradesh", "district": "Tirupati / Kurnool", "locality": "Rayalaseema Region", "latitude": 13.6288, "longitude": 79.4192},
    "52": {"state": "Andhra Pradesh", "district": "Vijayawada / Guntur", "locality": "Coastal Andhra Region", "latitude": 16.5062, "longitude": 80.6480},
    "53": {"state": "Andhra Pradesh", "district": "Visakhapatnam / Kakinada", "locality": "North Coastal Andhra", "latitude": 17.6868, "longitude": 83.2185},
    # 56-59: Karnataka
    "56": {"state": "Karnataka", "district": "Bengaluru Urban", "locality": "Bengaluru Postal Region", "latitude": 12.9794, "longitude": 77.5946},
    "57": {"state": "Karnataka", "district": "Mysuru / Mangaluru", "locality": "South Karnataka Region", "latitude": 12.2958, "longitude": 76.6394},
    "58": {"state": "Karnataka", "district": "Hubballi-Dharwad / Belagavi", "locality": "North-West Karnataka", "latitude": 15.3647, "longitude": 75.1240},
    "59": {"state": "Karnataka", "district": "Kalaburagi / Ballari", "locality": "Kalyana-Karnataka Region", "latitude": 17.3297, "longitude": 76.8343},
    # 60-64: Tamil Nadu & Puducherry
    "60": {"state": "Tamil Nadu", "district": "Chennai / Kanchipuram", "locality": "Northern Tamil Nadu", "latitude": 13.0827, "longitude": 80.2707},
    "61": {"state": "Tamil Nadu", "district": "Thanjavur / Nagapattinam", "locality": "Delta Region Tamil Nadu", "latitude": 10.7870, "longitude": 79.1378},
    "62": {"state": "Tamil Nadu", "district": "Madurai / Dindigul", "locality": "Southern Tamil Nadu", "latitude": 9.9252, "longitude": 78.1198},
    "63": {"state": "Tamil Nadu", "district": "Namakkal / Salem / Vellore", "locality": "Kongu & North-Central Tamil Nadu", "latitude": 11.3800, "longitude": 77.8900},
    "64": {"state": "Tamil Nadu", "district": "Coimbatore / Tiruppur / Nilgiris", "locality": "Western Tamil Nadu", "latitude": 11.0168, "longitude": 76.9558},
    # 67-69: Kerala & Lakshadweep
    "67": {"state": "Kerala", "district": "Kozhikode / Kannur", "locality": "Northern Kerala", "latitude": 11.2588, "longitude": 75.7804},
    "68": {"state": "Kerala", "district": "Ernakulam / Thrissur", "locality": "Central Kerala", "latitude": 9.9816, "longitude": 76.2799},
    "69": {"state": "Kerala", "district": "Thiruvananthapuram / Kollam", "locality": "Southern Kerala", "latitude": 8.5061, "longitude": 76.9558},
    # 70-74: West Bengal & Sikkim
    "70": {"state": "West Bengal", "district": "Kolkata", "locality": "Kolkata Postal Region", "latitude": 22.5726, "longitude": 88.3639},
    "71": {"state": "West Bengal", "district": "Howrah / Hooghly / Bardhaman", "locality": "Rarh Bengal Region", "latitude": 22.5958, "longitude": 88.2636},
    "72": {"state": "West Bengal", "district": "Paschim Medinipur / Bankura", "locality": "South-West Bengal Region", "latitude": 22.4257, "longitude": 87.3199},
    "73": {"state": "West Bengal", "district": "Siliguri / Darjeeling / Jalpaiguri", "locality": "North Bengal & Sikkim", "latitude": 26.7271, "longitude": 88.3953},
    "74": {"state": "West Bengal", "district": "Nadia / Murshidabad", "locality": "Central Bengal Region", "latitude": 23.4013, "longitude": 88.5002},
    # 75-77: Odisha
    "75": {"state": "Odisha", "district": "Bhubaneswar / Cuttack / Puri", "locality": "Coastal Odisha", "latitude": 20.2961, "longitude": 85.8245},
    "76": {"state": "Odisha", "district": "Berhampur / Koraput", "locality": "Southern Odisha", "latitude": 19.3149, "longitude": 84.7941},
    "77": {"state": "Odisha", "district": "Rourkela / Sambalpur", "locality": "Western Odisha", "latitude": 22.2604, "longitude": 84.8536},
    # 78: Assam
    "78": {"state": "Assam", "district": "Kamrup / Guwahati", "locality": "Assam Postal Region", "latitude": 26.1856, "longitude": 91.7483},
    # 79: North East (Meghalaya, Tripura, Mizoram, Manipur, Nagaland, Arunachal Pradesh)
    "79": {"state": "Meghalaya / North East", "district": "East Khasi Hills / Shillong", "locality": "North Eastern Postal Circle", "latitude": 25.5788, "longitude": 91.8933},
    # 80-85: Bihar & Jharkhand
    "80": {"state": "Bihar", "district": "Patna / Gaya", "locality": "South Bihar Region", "latitude": 25.6093, "longitude": 85.1376},
    "81": {"state": "Bihar", "district": "Bhagalpur / Munger", "locality": "Eastern Bihar Region", "latitude": 25.2425, "longitude": 86.9842},
    "82": {"state": "Jharkhand", "district": "Hazaribagh / Dhanbad", "locality": "North Jharkhand Region", "latitude": 23.9961, "longitude": 85.3637},
    "83": {"state": "Jharkhand", "district": "Ranchi / Jamshedpur", "locality": "South Jharkhand Region", "latitude": 23.3441, "longitude": 85.3096},
    "84": {"state": "Bihar", "district": "Muzaffarpur / Saran", "locality": "North-West Bihar Region", "latitude": 26.1209, "longitude": 85.3647},
    "85": {"state": "Bihar", "district": "Purnia / Katihar", "locality": "Seemanchal Bihar Region", "latitude": 25.7771, "longitude": 87.4753},
}


class PincodeService:
    """Provides resolution of 6-digit Indian Postal Index Numbers (PIN codes)."""

    _exact_cache: Optional[Dict[str, Dict[str, Any]]] = None

    @classmethod
    def _load_pincodes(cls) -> Dict[str, Dict[str, Any]]:
        if cls._exact_cache is not None:
            return cls._exact_cache

        cache = {}
        base_dir = Path(__file__).resolve().parent.parent.parent
        pincode_file = base_dir / "seed_data" / "pincodes.json"

        if pincode_file.exists():
            try:
                with open(pincode_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        code = str(item.get("pincode", "")).strip()
                        if code:
                            cache[code] = item
            except Exception:
                pass

        cls._exact_cache = cache
        return cache

    @classmethod
    def resolve_pincode(cls, pincode: str) -> Dict[str, Any]:
        """Resolves a 6-digit PIN code into geographic coordinates and administrative boundaries.

        Returns:
            dict containing pincode, locality, district, state, latitude, longitude,
            is_approximate flag, and resolution confidence.
        Raises:
            HTTPException 400 if malformed or invalid PIN format.
            HTTPException 404 if PIN cannot be resolved to any Indian postal area.
        """
        clean = (pincode or "").strip()

        # Validate 6-digit Indian PIN code format
        if not PINCODE_REGEX.match(clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_PINCODE_FORMAT",
                        "message": "PIN code must be a valid 6-digit Indian postal code starting with digits 1-9.",
                    }
                },
            )

        exact_map = cls._load_pincodes()

        # 1. Exact match from curated postal database
        if clean in exact_map:
            rec = exact_map[clean]
            return {
                "pincode": clean,
                "locality": rec.get("office_name", f"Postal Area {clean}"),
                "district": rec["district"],
                "state": rec["state"],
                "latitude": float(rec["latitude"]),
                "longitude": float(rec["longitude"]),
                "is_approximate": True,
                "confidence": "EXACT",
                "message": f"Resolved postal code {clean} ({rec.get('office_name')}, {rec.get('district')}).",
            }

        # 2. Regional postal circle prefix match (2 digits)
        prefix = clean[:2]
        if prefix in POSTAL_CIRCLES:
            circle = POSTAL_CIRCLES[prefix]
            return {
                "pincode": clean,
                "locality": f"{circle['locality']} ({clean})",
                "district": circle["district"],
                "state": circle["state"],
                "latitude": float(circle["latitude"]),
                "longitude": float(circle["longitude"]),
                "is_approximate": True,
                "confidence": "POSTAL_CIRCLE",
                "message": f"Approximate postal region resolved for {clean} in {circle['district']}, {circle['state']}.",
            }

        # 3. Unresolved
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PINCODE_NOT_FOUND",
                    "message": f"PIN code {clean} could not be resolved. Please use village or locality fallback.",
                }
            },
        )
