from typing import Any, Dict, List, Optional
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.facility_service import FacilityServiceHandler
from app.services.pincode_service import PincodeService


class IVRSimulationService:
    """Zero-cost browser-accessible simulated IVR engine for public healthcare access.

    Supports Tamil ('ta') and English ('en') call flows with keypad (DTMF) navigation,
    postal PIN code location resolution, and verified distance-based facility ranking.
    """

    PROMPTS = {
        "welcome": {
            "ta": "வணக்கம்! NALAM AI கிராமப்புற சுகாதார உதவி மையத்திற்கு வரவேற்கிறோம். அருகிலுள்ள சுகாதார நிலையங்களைக் கண்டறியவும் சுகாதாரத் தகவல்களைப் பெறவும் நாங்கள் உங்களுக்கு உதவுகிறோம். தமிழில் தொடர 1-ஐ அழுத்தவும். Welcome to NALAM AI Healthcare Assistance. For English, press 2.",
            "en": "Welcome to NALAM AI Healthcare Assistance. We help you find nearby healthcare facilities and access healthcare information. For English, press 2. தமிழில் தொடர 1-ஐ அழுத்தவும்.",
        },
        "main_menu": {
            "ta": (
                "முதன்மை மெனு: அருகிலுள்ள அரசு சுகாதார நிலையங்களைக் கண்டறிய 1-ஐ அழுத்தவும். "
                "கிடைக்கும் மருத்துவ சேவைகளைப் பற்றி அறிய 2-ஐ அழுத்தவும். "
                "அவசர உதவி மற்றும் தொடர்புத் தகவல்களைக் கேட்க 3-ஐ அழுத்தவும். "
                "இந்த அறிவிப்பை மீண்டும் கேட்க 9-ஐ அழுத்தவும். "
                "முதன்மை மெனுவிற்கு திரும்ப எப்போதும் 0-ஐ அழுத்தவும்."
            ),
            "en": (
                "Main Menu: Press 1 to find nearby healthcare facilities. "
                "Press 2 to learn about available healthcare services. "
                "Press 3 to hear emergency assistance and contact information. "
                "Press 9 to repeat this prompt. "
                "Press 0 at any time to return to the main menu."
            ),
        },
        "location_prompt": {
            "ta": (
                "அருகிலுள்ள சுகாதார நிலையங்களைக் கண்டறிய, உங்கள் தொலைபேசி கீபேடில் 6 இலக்க அஞ்சல் குறியீட்டை (PIN code) உள்ளிட்டு # அழுத்தவும். "
                "அல்லது உங்கள் சாதன இருப்பிடத்தை அறிய * அழுத்தவும். "
                "கிராமத்தின் பெயரைத் தேட 4-ஐ அழுத்தவும். "
                "முதன்மை மெனுவிற்கு திரும்ப 0-ஐ அழுத்தவும்."
            ),
            "en": (
                "To find nearby healthcare facilities, please enter your 6-digit Indian PIN code using the keypad and press pound. "
                "Or press star to detect location automatically. "
                "Or press 4 to search by village name. "
                "Press 0 to return to the main menu."
            ),
        },
        "services_info": {
            "ta": (
                "NALAM AI வழங்கும் சுகாதார சேவைகள்: "
                "1. ஆரம்ப சுகாதார நிலையங்கள் (PHC) - புறநோயாளிகள் சிகிச்சை, தாய் சேய் நலப் பரிசோதனை மற்றும் இலவச அத்தியாவசிய மருந்துகள். "
                "2. சமூக சுகாதார நிலையங்கள் (CHC) - 30 படுக்கை வசதி, அறுவை சிகிச்சை மற்றும் குழந்தைகள் நலம். "
                "3. துணை சுகாதார நிலையங்கள் (Sub-Centre) - கிராம அளவில் முதல் நிலை சிகிச்சை மற்றும் தடுப்பூசி சேவைகள். "
                "4. கிராம ஆஷா பணியாளர்கள் உங்கள் இல்லத்திற்கே வந்து சுகாதார வழிகாட்டல் வழங்குவர். "
                "இந்த தகவலை மீண்டும் கேட்க 9-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            ),
            "en": (
                "NALAM AI Available Healthcare Services: "
                "1. Primary Health Centres (PHCs) provide outpatient care, maternal consultations, basic lab diagnostics, and free essential medicines. "
                "2. Community Health Centres (CHCs) offer 30-bed in-patient care, emergency surgical care, and obstetric specialists. "
                "3. Health Sub-Centres provide village-level first-contact primary care and child immunizations. "
                "4. Village ASHA workers assist with door-to-door consultations and hospital referrals. "
                "Press 9 to repeat this information. Press 0 to return to the main menu."
            ),
        },
        "assistance_info": {
            "ta": (
                "அவசர உதவி மற்றும் தொடர்பு எண்கள்: "
                "தேசிய அவசர உதவி எண்: 112. "
                "இலவச அரசு ஆம்புலன்ஸ் சேவை: 108. "
                "மாநில அரசு சுகாதார ஆலோசனை உதவி எண்: 104. "
                "NALAM AI கட்டணமில்லா உதவி மையம்: 1800-202-CARE (1800-202-2273). "
                "உங்கள் கிராமத்து ஆஷா பணியாளரை நேரடியாகவும் தொடர்புகொள்ளலாம். "
                "மீண்டும் கேட்க 9-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            ),
            "en": (
                "Emergency Assistance and Contacts: "
                "National Emergency Response Support: 112. "
                "Free Government Ambulance: 108. "
                "State Health Information Helpline: 104. "
                "NALAM AI Toll-Free Support Desk: 1800-202-CARE (1800-202-2273). "
                "You can also reach out to your village ASHA worker for local support. "
                "Press 9 to repeat this information. Press 0 to return to the main menu."
            ),
        },
        "invalid_option": {
            "ta": "தவறான தேர்வு. தயவுசெய்து சரியான எண்ணை அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்.",
            "en": "Invalid option. Please enter a valid number from the menu. Press 0 to return to the main menu.",
        },
        "invalid_pincode": {
            "ta": "நீங்கள் உள்ளிட்ட அஞ்சல் குறியீடு தவறானது. 6 இலக்க எண்ணை சரியாக உள்ளிட்டு # அழுத்தவும். அல்லது கிராமத்தின் பெயரைத் தேட 4-ஐ அழுத்தவும்.",
            "en": "The PIN code entered is invalid. Please enter a valid 6-digit Indian PIN code and press pound, or press 4 to search by village name.",
        },
        "no_facilities": {
            "ta": "இந்த இருப்பிடத்திற்கு அருகில் 50 கிலோமீட்டர் வரம்பில் சுகாதார நிலையங்கள் எதுவும் கண்டறியப்படவில்லை. மற்றொரு அஞ்சல் குறியீட்டை உள்ளிடவும் அல்லது கிராமத்தைத் தேடவும்.",
            "en": "No healthcare facilities found within a 50 kilometre radius of this location. Please try another PIN code or search by village.",
        },
        "call_ended": {
            "ta": "NALAM AI சுகாதார உதவி மையத்தை அழைத்ததற்கு நன்றி. நலமாக இருங்கள். அழைப்பு முடிந்தது.",
            "en": "Thank you for calling NALAM AI Healthcare Assistance. Stay healthy. Call ended.",
        },
    }

    @classmethod
    def start_call(cls, language: Optional[str] = "ta") -> Dict[str, Any]:
        """Initiate simulated call session starting at language selection."""
        call_sid = f"sim-{uuid4().hex[:10]}"
        return {
            "call_sid": call_sid,
            "status": "IN_PROGRESS",
            "current_menu": "LANGUAGE_SELECT",
            "language": language or "ta",
            "speak_text": cls.PROMPTS["welcome"]["ta"],
            "options": [
                {"digit": "1", "label": "தமிழ் (Tamil)"},
                {"digit": "2", "label": "English"},
            ],
            "gather_dtmf": True,
            "max_digits": 1,
        }

    @classmethod
    async def process_input(
        cls,
        db: AsyncSession,
        call_sid: str,
        digits: str,
        current_menu: str,
        language: str = "ta",
        location_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """State machine for processing simulated keypad/DTMF inputs."""
        clean_digits = (digits or "").strip()
        lang = "en" if language == "en" else "ta"

        # Universal key 0: Return to Main Menu
        if clean_digits == "0":
            return cls._menu_response(call_sid, "MAIN_MENU", lang, cls.PROMPTS["main_menu"][lang])

        # Universal key 9: Repeat Current Prompt
        if clean_digits == "9":
            return cls._repeat_menu(call_sid, current_menu, lang)

        # 1. LANGUAGE SELECT
        if current_menu == "LANGUAGE_SELECT":
            if clean_digits == "1":
                return cls._menu_response(call_sid, "MAIN_MENU", "ta", cls.PROMPTS["main_menu"]["ta"])
            elif clean_digits == "2":
                return cls._menu_response(call_sid, "MAIN_MENU", "en", cls.PROMPTS["main_menu"]["en"])
            else:
                return {
                    "call_sid": call_sid,
                    "status": "IN_PROGRESS",
                    "current_menu": "LANGUAGE_SELECT",
                    "language": lang,
                    "speak_text": "தவறான தேர்வு / Invalid choice. தமிழில் தொடர 1-ஐ அழுத்தவும். For English, press 2.",
                    "gather_dtmf": True,
                    "max_digits": 1,
                }

        # 2. MAIN MENU
        if current_menu == "MAIN_MENU":
            if clean_digits == "1":
                # Option 1: Find nearby healthcare facilities
                return {
                    "call_sid": call_sid,
                    "status": "IN_PROGRESS",
                    "current_menu": "LOCATION_INPUT",
                    "language": lang,
                    "speak_text": cls.PROMPTS["location_prompt"][lang],
                    "gather_dtmf": True,
                    "max_digits": 6,
                    "supports_pincode": True,
                    "supports_geolocation": True,
                    "supports_village": True,
                }
            elif clean_digits == "2":
                # Option 2: Healthcare services info
                return {
                    "call_sid": call_sid,
                    "status": "IN_PROGRESS",
                    "current_menu": "SERVICES_INFO",
                    "language": lang,
                    "speak_text": cls.PROMPTS["services_info"][lang],
                    "gather_dtmf": True,
                    "max_digits": 1,
                }
            elif clean_digits == "3":
                # Option 3: Assistance & Contact info
                return {
                    "call_sid": call_sid,
                    "status": "IN_PROGRESS",
                    "current_menu": "ASSISTANCE_INFO",
                    "language": lang,
                    "speak_text": cls.PROMPTS["assistance_info"][lang],
                    "gather_dtmf": True,
                    "max_digits": 1,
                }
            else:
                return {
                    "call_sid": call_sid,
                    "status": "IN_PROGRESS",
                    "current_menu": "MAIN_MENU",
                    "language": lang,
                    "speak_text": f"{cls.PROMPTS['invalid_option'][lang]} {cls.PROMPTS['main_menu'][lang]}",
                    "gather_dtmf": True,
                    "max_digits": 1,
                }

        # 3. LOCATION INPUT (Keypad digits or explicit GPS location)
        if current_menu == "LOCATION_INPUT":
            # If caller pressed 4: Switch to village search
            if clean_digits == "4":
                v_msg = (
                    "கிராமத்தின் பெயரைத் தேட கீழேயுள்ள தேடல் பெட்டியைப் பயன்படுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
                    if lang == "ta"
                    else "Please use the village search input to find your village or town. Press 0 for the main menu."
                )
                return {
                    "call_sid": call_sid,
                    "status": "IN_PROGRESS",
                    "current_menu": "VILLAGE_SEARCH_INPUT",
                    "language": lang,
                    "speak_text": v_msg,
                    "gather_dtmf": True,
                }

            # If clean_digits looks like a PIN code (6 digits, or ended with #)
            pin_cand = clean_digits.rstrip("#").strip()
            if len(pin_cand) == 6 and pin_cand.isdigit():
                try:
                    res = PincodeService.resolve_pincode(pin_cand)
                    return await cls.fetch_and_format_facilities(
                        db=db,
                        call_sid=call_sid,
                        lang=lang,
                        latitude=res["latitude"],
                        longitude=res["longitude"],
                        location_name=f"{res['locality']}, {res['district']}",
                        is_approximate=True,
                    )
                except Exception:
                    return {
                        "call_sid": call_sid,
                        "status": "IN_PROGRESS",
                        "current_menu": "LOCATION_INPUT",
                        "language": lang,
                        "speak_text": cls.PROMPTS["invalid_pincode"][lang],
                        "gather_dtmf": True,
                        "max_digits": 6,
                    }

            # If GPS coordinates passed in location_data
            if location_data and "latitude" in location_data and "longitude" in location_data:
                return await cls.fetch_and_format_facilities(
                    db=db,
                    call_sid=call_sid,
                    lang=lang,
                    latitude=float(location_data["latitude"]),
                    longitude=float(location_data["longitude"]),
                    location_name=location_data.get("name", "Device GPS Location"),
                    is_approximate=False,
                )

            return {
                "call_sid": call_sid,
                "status": "IN_PROGRESS",
                "current_menu": "LOCATION_INPUT",
                "language": lang,
                "speak_text": cls.PROMPTS["invalid_pincode"][lang],
                "gather_dtmf": True,
                "max_digits": 6,
            }

        # 4. FACILITIES RESULTS LIST (Navigation: 1 = Next, 9 = Repeat, 0 = Main Menu)
        if current_menu == "FACILITIES_RESULTS":
            if clean_digits == "1":
                # Advance or cycle through results
                items = location_data.get("items", []) if location_data else []
                current_idx = int(location_data.get("current_index", 0)) + 1 if location_data else 0
                if items and current_idx < len(items):
                    fac = items[current_idx]
                    fac_speech = cls._format_single_facility(fac, current_idx + 1, len(items), lang)
                    return {
                        "call_sid": call_sid,
                        "status": "IN_PROGRESS",
                        "current_menu": "FACILITIES_RESULTS",
                        "language": lang,
                        "speak_text": fac_speech,
                        "current_index": current_idx,
                        "facilities": items,
                        "gather_dtmf": True,
                        "max_digits": 1,
                    }
                else:
                    end_msg = (
                        "அனைத்து அருகிலுள்ள சுகாதார நிலையங்களும் கூறப்பட்டன. முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
                        if lang == "ta"
                        else "You have heard all nearby healthcare facilities. Press 0 for the main menu."
                    )
                    return {
                        "call_sid": call_sid,
                        "status": "IN_PROGRESS",
                        "current_menu": "FACILITIES_RESULTS",
                        "language": lang,
                        "speak_text": end_msg,
                        "current_index": len(items) - 1 if items else 0,
                        "facilities": items,
                        "gather_dtmf": True,
                        "max_digits": 1,
                    }

        # Fallback to repeating current menu
        return cls._repeat_menu(call_sid, current_menu, lang)

    @classmethod
    async def fetch_and_format_facilities(
        cls,
        db: AsyncSession,
        call_sid: str,
        lang: str,
        latitude: float,
        longitude: float,
        location_name: str,
        is_approximate: bool = True,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """Queries actual database facilities by ascending distance and formats spoken text."""
        handler = FacilityServiceHandler(db)
        # Search radius default 25 km, expandable up to 50 km if few facilities
        res = await handler.get_nearby_facilities(
            lat=latitude,
            lon=longitude,
            radius_km=30.0,
            limit=limit,
        )

        items = res.items
        if not items:
            # Try expanded radius of 50 km
            res = await handler.get_nearby_facilities(
                lat=latitude,
                lon=longitude,
                radius_km=50.0,
                limit=limit,
            )
            items = res.items

        if not items:
            return {
                "call_sid": call_sid,
                "status": "IN_PROGRESS",
                "current_menu": "LOCATION_INPUT",
                "language": lang,
                "speak_text": cls.PROMPTS["no_facilities"][lang],
                "gather_dtmf": True,
                "max_digits": 6,
            }

        # Build spoken announcement
        approx_notice_ta = " (தோராயமான அஞ்சல் எல்லை)" if is_approximate else ""
        approx_notice_en = " (approximate postal area)" if is_approximate else ""

        fac_summaries = []
        for i, f in enumerate(items[:3], 1):
            dist_str = f"{f.distance_km:.1f}"
            if lang == "ta":
                fac_summaries.append(f"நிலையம் {i}: {f.name}, {f.facility_type}, தூரம் {dist_str} கிலோமீட்டர்.")
            else:
                fac_summaries.append(f"Facility {i}: {f.name}, {f.facility_type}, distance {dist_str} kilometres.")

        joined = " ".join(fac_summaries)
        if lang == "ta":
            speech = (
                f"{location_name}{approx_notice_ta} பகுதிக்கு அருகில் {len(items)} சுகாதார நிலையங்கள் கண்டறியப்பட்டன. "
                f"{joined} "
                "அடுத்த நிலையத்தைக் கேட்க 1-ஐ அழுத்தவும். மீண்டும் கேட்க 9-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        else:
            speech = (
                f"Found {len(items)} healthcare facilities near {location_name}{approx_notice_en}. "
                f"{joined} "
                "Press 1 to hear the next facility. Press 9 to repeat. Press 0 for the main menu."
            )

        serializable_items = [
            {
                "id": str(f.id),
                "name": f.name,
                "facility_type": f.facility_type,
                "address": f.address,
                "district": f.district,
                "state": f.state,
                "latitude": f.latitude,
                "longitude": f.longitude,
                "distance_km": round(f.distance_km, 2),
            }
            for f in items
        ]

        return {
            "call_sid": call_sid,
            "status": "IN_PROGRESS",
            "current_menu": "FACILITIES_RESULTS",
            "language": lang,
            "speak_text": speech,
            "location_name": location_name,
            "is_approximate": is_approximate,
            "latitude": latitude,
            "longitude": longitude,
            "total_found": res.total,
            "facilities": serializable_items,
            "current_index": 0,
            "gather_dtmf": True,
            "max_digits": 1,
        }

    @classmethod
    def _format_single_facility(cls, fac: Dict[str, Any], idx: int, total: int, lang: str) -> str:
        dist_str = f"{fac.get('distance_km', 0):.1f}"
        name = fac.get("name", "Unknown Facility")
        ftype = fac.get("facility_type", "Healthcare Facility")
        addr = fac.get("address", "")
        if lang == "ta":
            return (
                f"நிலையம் {idx} / {total}: {name}, {ftype}. முகவரி: {addr}. தூரம்: {dist_str} கிலோமீட்டர். "
                "அடுத்த நிலையத்தைக் கேட்க 1-ஐ அழுத்தவும். மீண்டும் கேட்க 9-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        else:
            return (
                f"Facility {idx} of {total}: {name}, {ftype}. Address: {addr}. Distance: {dist_str} kilometres. "
                "Press 1 to hear next facility. Press 9 to repeat. Press 0 for main menu."
            )

    @classmethod
    def _menu_response(cls, call_sid: str, menu: str, lang: str, speak_text: str) -> Dict[str, Any]:
        return {
            "call_sid": call_sid,
            "status": "IN_PROGRESS",
            "current_menu": menu,
            "language": lang,
            "speak_text": speak_text,
            "gather_dtmf": True,
            "max_digits": 1,
        }

    @classmethod
    def _repeat_menu(cls, call_sid: str, current_menu: str, lang: str) -> Dict[str, Any]:
        prompt_key = {
            "LANGUAGE_SELECT": "welcome",
            "MAIN_MENU": "main_menu",
            "LOCATION_INPUT": "location_prompt",
            "SERVICES_INFO": "services_info",
            "ASSISTANCE_INFO": "assistance_info",
        }.get(current_menu, "main_menu")

        text = cls.PROMPTS.get(prompt_key, cls.PROMPTS["main_menu"])[lang]
        return {
            "call_sid": call_sid,
            "status": "IN_PROGRESS",
            "current_menu": current_menu,
            "language": lang,
            "speak_text": text,
            "gather_dtmf": True,
            "max_digits": 1,
        }
