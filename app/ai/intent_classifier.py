"""Comprehensive Intent Classifier and Query Analysis for NALAM AI Assistant.

Supports 14 distinct intents with multilingual (Tamil, English, Tanglish) understanding:
- FACILITY_SEARCH
- DOCTOR_AVAILABILITY
- APPOINTMENT_BOOKING
- MEDICINE_SEARCH
- MEDICINE_AVAILABILITY
- HEALTH_INFORMATION
- SYMPTOM_GUIDANCE
- EMERGENCY_HELP
- AMBULANCE_INFORMATION
- LOCATION_INFORMATION
- GENERAL_CONVERSATION
- PLATFORM_INFORMATION
- FOLLOW_UP
- UNKNOWN_INTENT

Also extracts:
- Location
- Medicine
- Doctor/Specialization
- Facility Type
- Clarification requirement
"""
from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional

from app.ai.location_extractor import extract_location
from app.ai.session_manager import ConversationSession


class IntentType(str, Enum):
    FACILITY_SEARCH = "FACILITY_SEARCH"
    DOCTOR_AVAILABILITY = "DOCTOR_AVAILABILITY"
    APPOINTMENT_BOOKING = "APPOINTMENT_BOOKING"
    MEDICINE_SEARCH = "MEDICINE_SEARCH"
    MEDICINE_AVAILABILITY = "MEDICINE_AVAILABILITY"
    HEALTH_INFORMATION = "HEALTH_INFORMATION"
    SYMPTOM_GUIDANCE = "SYMPTOM_GUIDANCE"
    EMERGENCY_HELP = "EMERGENCY_HELP"
    AMBULANCE_INFORMATION = "AMBULANCE_INFORMATION"
    LOCATION_INFORMATION = "LOCATION_INFORMATION"
    GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
    PLATFORM_INFORMATION = "PLATFORM_INFORMATION"
    FOLLOW_UP = "FOLLOW_UP"
    UNKNOWN_INTENT = "UNKNOWN_INTENT"
    CLINICAL_SAFETY = "CLINICAL_SAFETY"
    SYMPTOM_WITH_FACILITY = "SYMPTOM_WITH_FACILITY"
    GOVERNMENT_SCHEMES_DISCOVERY = "GOVERNMENT_SCHEMES_DISCOVERY"


@dataclass
class IntentClassificationResult:
    intent: IntentType
    confidence: float
    extracted_location: Optional[str] = None
    is_location_explicit: bool = False
    extracted_medicine: Optional[str] = None
    extracted_doctor: Optional[str] = None
    extracted_facility_type: Optional[str] = None
    extracted_date: Optional[str] = None
    extracted_symptom: Optional[str] = None
    needs_clarification: bool = False
    clarification_prompt_en: Optional[str] = None
    clarification_prompt_ta: Optional[str] = None
    is_emergency: bool = False
    entities: Dict[str, Any] = field(default_factory=dict)


def extract_medicine_entity(text: str) -> Optional[str]:
    """Extracts known medicines from English, Tamil, and Tanglish queries."""
    lowered = text.lower()
    med_mapping = {
        "paracetamol": "Paracetamol",
        "பாராசிட்டமால்": "Paracetamol",
        "amoxicillin": "Amoxicillin",
        "அமாக்சிசிலின்": "Amoxicillin",
        "metformin": "Metformin",
        "மெட்பார்மின்": "Metformin",
        "ors": "ORS Sachet",
        "ors sachet": "ORS Sachet",
        "ஓஆர்எஸ்": "ORS Sachet",
        "cetirizine": "Cetirizine",
        "செட்டிரிசின்": "Cetirizine",
        "amlodipine": "Amlodipine",
        "அம்லோடிபைன்": "Amlodipine",
        "iron and folic acid": "Iron and Folic Acid",
        "ifa": "Iron and Folic Acid",
        "folic acid": "Iron and Folic Acid",
    }
    for m_key, m_val in med_mapping.items():
        if m_key in lowered:
            return m_val
    return None


def classify_intent(
    message: str,
    language: str,
    session: Optional[ConversationSession] = None,
    user_home_village: Optional[str] = None,
) -> IntentClassificationResult:
    """Classifies user query into structured intent with extracted entities and multi-turn context."""
    cleaned = message.strip()
    lowered = cleaned.lower()

    active_loc_in_session = session.active_location if session else None
    active_intent_in_session = session.active_intent if session else None

    # 1. Location Extraction
    extracted_loc, coords, is_explicit_loc = extract_location(
        cleaned,
        conversation_active_location=active_loc_in_session,
        user_home_village=user_home_village,
    )
    # Effective location preserves active location from ongoing session if query has no new location
    effective_loc = extracted_loc or active_loc_in_session

    # 2. Medicine Extraction
    extracted_med = extract_medicine_entity(cleaned)

    # 3. Facility Type Extraction
    fac_type = None
    if any(k in lowered for k in ["chc", "chcs", "சமூக சுகாதார மையம்", "community health"]):
        fac_type = "CHC"
    elif any(k in lowered for k in ["uphc", "uphcs", "நகர்ப்புற ஆரம்ப சுகாதார"]):
        fac_type = "UPHC"
    elif any(k in lowered for k in ["phc", "phcs", "ஆரம்ப சுகாதார நிலையம்", "primary health"]):
        fac_type = "PHC"
    elif any(k in lowered for k in ["hospital", "hospitals", "மருத்துவமனை", "மருத்துவமனைகள்", "clinic", "dispensary"]):
        fac_type = "HOSPITAL"

    # 4. Ownership Extraction (Government vs Private)
    extracted_ownership = None
    if any(k in lowered for k in ["government", "govt", "public", "அரசு"]):
        extracted_ownership = "Government"
    elif any(k in lowered for k in ["private", "pvt", "தனியார்"]):
        extracted_ownership = "Private"

    # 5. Service / Specialty Extraction (Maternity, Emergency, etc.)
    extracted_service = None
    if any(k in lowered for k in ["maternity", "பிரசவ", "கர்ப்ப", "தாய் சேய்", "தாய்சேய்", "delivery", "டெலிவரி", "மசக்கை", "obstetric"]):
        extracted_service = "maternity"
    elif any(k in lowered for k in ["emergency", "அவசர", "trauma", "விபத்து", "casualty", "24x7", "24 மணி", "தீவிர சிகிச்சை"]):
        extracted_service = "emergency"

    # -------------------------------------------------------------
    # PRIORITY 1: EMERGENCY TRIAGE & AMBULANCE
    # -------------------------------------------------------------
    emergency_patterns = [
        r"chest pain", r"மாரடைப்பு", r"heart attack", r"difficulty breathing",
        r"மூச்சுத்திணறல்", r"emergency", r"அவசரம்", r"accident", r"விபத்து",
        r"heavy bleeding", r"ரத்தப்போக்கு", r"unconscious", r"மயக்கம்",
        r"(?<!heat\s)(?<!sun\s)\bstroke\b", r"பக்கவாதம்", r"snake bite", r"பாம்பு கடி", r"\b108\b",
        r"ambulance", r"ஆம்புலன்ஸ்",
    ]
    # Check if this is an immediate life-threatening emergency vs asking which hospitals have emergency services
    is_facility_inquiry = any(w in lowered for w in [
        "which hospital", "what hospital", "suggest hospital", "list of hospital",
        "hospitals have", "hospitals provide", "hospital with", "மருத்துவமனையில் அவசர",
        "எந்த மருத்துவமனை", "show me hospital", "which government hospital"
    ])
    if any(re.search(p, lowered) for p in emergency_patterns) and not is_facility_inquiry:
        is_amb = "108" in lowered or "ambulance" in lowered or "ஆம்புலன்ஸ்" in lowered
        return IntentClassificationResult(
            intent=IntentType.AMBULANCE_INFORMATION if is_amb else IntentType.EMERGENCY_HELP,
            confidence=0.98,
            extracted_location=effective_loc,
            is_location_explicit=is_explicit_loc,
            is_emergency=True,
            entities={"emergency_phone": "108"},
        )

    # -------------------------------------------------------------
    # PRIORITY 2: CLINICAL SAFETY GUARD (DOSAGE / PRESCRIPTIONS)
    # -------------------------------------------------------------
    dosage_patterns = [
        r"what dose", r"how much paracetamol", r"prescribe", r"dosage",
        r"how many tablets", r"what medicine should i take",
        r"என்ன மருந்து சாப்பிட வேண்டும்", r"மருந்தளவு", r"எத்தனை மாத்திரை",
        r"எந்த மருந்து சாப்பிடலாம்",
    ]
    if any(re.search(p, lowered) for p in dosage_patterns):
        return IntentClassificationResult(
            intent=IntentType.CLINICAL_SAFETY,
            confidence=0.95,
            extracted_location=effective_loc,
            is_location_explicit=is_explicit_loc,
            extracted_medicine=extracted_med,
        )

    # -------------------------------------------------------------
    # PRIORITY 3: SYMPTOM GUIDANCE (NON-DIAGNOSTIC FIRST AID)
    # -------------------------------------------------------------
    symptom_patterns = [
        r"fever", r"காய்ச்சல்", r"cough", r"இருமல்", r"cold", r"சளி",
        r"headache", r"தலைவலி", r"vomit", r"வாந்தி", r"diarrhea", r"பேதி",
        r"stomach pain", r"வயிற்று வலி", r"sore throat", r"தொண்டை வலி",
        r"body pain", r"உடல் வலி", r"dizziness", r"தலைச்சுற்றல்",
        r"என்ன செய்யலாம்", r"what should i do", r"feel sick", r"உடம்பு சரியில்லை",
        r"dehydration", r"நீரிழப்பு", r"weakness", r"சோர்வு",
        r"cuts", r"wound", r"காயம்", r"bleeding", r"ரத்தம்",
    ]
    # Detect specific symptom
    detected_symptom = None
    symptom_map = {
        "fever": ["fever", "காய்ச்சல்"],
        "cough": ["cough", "இருமல்"],
        "cold": ["cold", "சளி"],
        "headache": ["headache", "தலைவலி"],
        "vomiting": ["vomit", "வாந்தி"],
        "diarrhea": ["diarrhea", "பேதி"],
        "stomach_pain": ["stomach pain", "வயிற்று வலி"],
        "sore_throat": ["sore throat", "தொண்டை வலி"],
        "body_pain": ["body pain", "உடல் வலி"],
        "dizziness": ["dizziness", "தலைச்சுற்றல்"],
        "dehydration": ["dehydration", "நீரிழப்பு"],
        "weakness": ["weakness", "சோர்வு", "feel sick", "உடம்பு சரியில்லை"],
        "cuts_wounds": ["cuts", "wound", "காயம்", "bleeding", "ரத்தம்"],
    }
    for sym_key, sym_triggers in symptom_map.items():
        if any(t in lowered for t in sym_triggers):
            detected_symptom = sym_key
            break

    has_symptom = any(re.search(p, lowered) for p in symptom_patterns)
    # Educational / informational phrasing → let HEALTH_INFORMATION handle it
    educational_phrases = [
        r"what causes", r"how to prevent", r"benefits of", r"risk factors",
        r"symptoms of", r"treatment for", r"what is", r"explain",
        r"causes of", r"prevention of", r"how to treat",
        r"தடுப்பது எப்படி", r"என்ன காரணம்",
    ]
    is_educational = any(re.search(p, lowered) for p in educational_phrases)
    has_facility_keyword = any(
        k in lowered for k in ["phc", "hospital", "doctor", "dr.", "மருத்துவர்", "மருத்துவமனை", "book", "appointment", "find", "where", "nearest", "near", "எங்கே", "எங்க", "அருகில்"]
    )
    # Check if symptom + facility/location coexist
    if has_symptom and not is_educational and (has_facility_keyword or is_explicit_loc):
        return IntentClassificationResult(
            intent=IntentType.SYMPTOM_WITH_FACILITY,
            confidence=0.93,
            extracted_location=effective_loc,
            is_location_explicit=is_explicit_loc,
            extracted_facility_type=fac_type,
            extracted_symptom=detected_symptom,
            entities={
                "ownership": extracted_ownership,
                "service": extracted_service,
                "facility_type": fac_type,
                "symptom": detected_symptom,
            },
        )
    # Pure symptom guidance without facility request (but not educational queries)
    if has_symptom and not has_facility_keyword and not is_educational:
        return IntentClassificationResult(
            intent=IntentType.SYMPTOM_GUIDANCE,
            confidence=0.92,
            extracted_location=effective_loc,
            is_location_explicit=is_explicit_loc,
            extracted_symptom=detected_symptom,
            entities={"symptom": detected_symptom},
        )

    # -------------------------------------------------------------
    # PRIORITY 4: APPOINTMENT BOOKING
    # -------------------------------------------------------------
    booking_patterns = [
        r"appointment", r"முன்பதிவு", r"அப்பாயின்ட்மென்ட்", r"\bbook\b",
        r"\bbooking\b", r"\bslot\b", r"\breserve\b", r"டோக்கன்", r"\btoken\b",
        r"book pann", r"booking pann", r"நேர முன்பதிவு",
    ]
    if any(re.search(p, lowered) for p in booking_patterns) and not any(
        k in lowered for k in ["how does", "formula", "algorithm", "architecture"]
    ):
        return IntentClassificationResult(
            intent=IntentType.APPOINTMENT_BOOKING,
            confidence=0.95,
            extracted_location=effective_loc,
            is_location_explicit=is_explicit_loc,
            extracted_facility_type=fac_type,
            entities={
                "ownership": extracted_ownership,
                "service": extracted_service,
                "facility_type": fac_type,
            },
        )

    # -------------------------------------------------------------
    # PRIORITY 5: DOCTOR AVAILABILITY
    # -------------------------------------------------------------
    doctor_patterns = [
        r"\bdoctor\b", r"\bphysician\b", r"\bdr\b", r"\bdr\.", r"மருத்துவர்",
        r"டாக்டர்", r"on duty", r"பணியில்", r"இருக்கிறாரா", r"attendance",
        r"duty doctor", r"வருகை", r"available doctor",
    ]
    if any(re.search(p, lowered) for p in doctor_patterns) and not any(
        k in lowered for k in ["how does", "formula", "algorithm", "rag"]
    ):
        return IntentClassificationResult(
            intent=IntentType.DOCTOR_AVAILABILITY,
            confidence=0.93,
            extracted_location=effective_loc,
            is_location_explicit=is_explicit_loc,
            extracted_facility_type=fac_type,
        )

    # -------------------------------------------------------------
    # PRIORITY 6: MEDICINE STOCK & SEARCH
    # -------------------------------------------------------------
    medicine_patterns = [
        r"\bmedicine\b", r"\bmedicines\b", r"\btablet\b", r"\btablets\b",
        r"\bcapsule\b", r"\bstock\b", r"\binventory\b", r"மருந்து",
        r"மாத்திரை", r"இருப்பு", r"கிடைக்குமா", r"எங்கே கிடைக்கும்",
        r"paracetamol", r"amoxicillin", r"metformin", r"ors", r"cetirizine",
    ]
    if any(re.search(p, lowered) for p in medicine_patterns) and not any(
        k in lowered for k in ["how does", "formula", "algorithm"]
    ):
        intent_type = IntentType.MEDICINE_AVAILABILITY if any(
            w in lowered for w in ["stock", "இருப்பு", "கிடைக்குமா", "available", "where can i get"]
        ) else IntentType.MEDICINE_SEARCH

        return IntentClassificationResult(
            intent=intent_type,
            confidence=0.92,
            extracted_location=effective_loc,
            is_location_explicit=is_explicit_loc,
            extracted_medicine=extracted_med or "Paracetamol",
        )

    # -------------------------------------------------------------
    # PRIORITY 7: PLATFORM INFORMATION & RAG
    # -------------------------------------------------------------
    platform_patterns = [
        r"how does nalam", r"what is nalam", r"carebridge", r"loss formula",
        r"expected loss", r"stock algorithm", r"trip loss", r"ivr pin",
        r"pin lockout", r"lockout", r"நலம் என்றால் என்ன", r"பரிந்துரை சூத்திரம்",
        r"architecture", r"bayesian decay",
    ]
    if any(re.search(p, lowered) for p in platform_patterns):
        return IntentClassificationResult(
            intent=IntentType.PLATFORM_INFORMATION,
            confidence=0.94,
        )

    # -------------------------------------------------------------
    # PRIORITY 8: GENERAL HEALTH INFORMATION
    # -------------------------------------------------------------
    health_info_patterns = [
        r"what causes", r"how to prevent", r"benefits of", r"dehydration",
        r"heat stroke", r"diabetes", r"hypertension", r"உணவு முறை",
        r"தடுப்பது எப்படி", r"தண்ணீர் பற்றாக்குறை", r"நலக் குறிப்பு",
    ]
    if any(re.search(p, lowered) for p in health_info_patterns):
        return IntentClassificationResult(
            intent=IntentType.HEALTH_INFORMATION,
            confidence=0.88,
        )

    # -------------------------------------------------------------
    # PRIORITY 9: FACILITY SEARCH (EXPLICIT REQUESTS)
    # -------------------------------------------------------------
    facility_patterns = [
        r"\bphc\b", r"\bphcs\b", r"\bchc\b", r"\bchcs\b", r"\buphc\b", r"\buphcs\b",
        r"\bhospital\b", r"\bhospitals\b",
        r"\bclinic\b", r"\bdispensary\b", r"\bhealth centre\b",
        r"ஆரம்ப சுகாதார நிலையம்", r"மருத்துவமனை", r"மருத்துவ மையம்",
        r"சுகாதார நிலையம்", r"find a phc", r"show hospitals", r"மருத்துவமனை எங்கே",
        r"facilities", r"healthcare facilities", r"suggest hospitals", r"மருத்துவமனைகள்",
        r"maternity", r"பிரசவ", r"emergency", r"அவசர மருத்துவமனை",
    ]
    if any(re.search(p, lowered) for p in facility_patterns):
        return IntentClassificationResult(
            intent=IntentType.FACILITY_SEARCH,
            confidence=0.95,
            extracted_location=effective_loc,
            is_location_explicit=is_explicit_loc,
            extracted_facility_type=fac_type,
            entities={
                "ownership": extracted_ownership,
                "service": extracted_service,
                "facility_type": fac_type,
            },
        )

    # -------------------------------------------------------------
    # PRIORITY 10: LOCATION CHANGE / FOLLOW-UP / "கோயம்புத்தூர்ல சொல்லு"
    # -------------------------------------------------------------
    # If the user input is primarily specifying or changing a location:
    # e.g.: "கோயம்புத்தூர்ல சொல்லு.", "சேலத்தில்?", "What about Salem?", "In Coimbatore", "Tell me in Coimbatore"
    words = cleaned.split()
    is_short_location_query = is_explicit_loc and (
        len(words) <= 3 or
        any(re.search(p, lowered) for p in [r"^in\s+[a-z]+$", r"what about", r"how about", r"tell me in", r"சொல்லு", r"சொல்லுங்க", r"சொல்ல$"])
    ) and not any(
        re.search(p, lowered) for p in [r"\bphc\b", r"\bhospital\b", r"\bdoctor\b", r"\bmedicine\b", r"ஆரம்ப சுகாதார", r"மருத்துவ", r"மருந்து"]
    )

    if is_short_location_query:
        # Check if there is an active previous intent in the multi-turn session
        if active_intent_in_session in [
            "FACILITY_SEARCH", "DOCTOR_AVAILABILITY", "MEDICINE_SEARCH",
            "MEDICINE_AVAILABILITY", "APPOINTMENT_BOOKING"
        ]:
            # Inherit previous intent with new location
            return IntentClassificationResult(
                intent=IntentType(active_intent_in_session),
                confidence=0.90,
                extracted_location=extracted_loc,
                is_location_explicit=True,
                extracted_facility_type=fac_type,
                extracted_medicine=session.active_medicine if session else None,
            )
        else:
            # Standalone location query with no prior context!
            # e.g.: "கோயம்புத்தூர்ல சொல்லு."
            # Do NOT silently dump Tiruchengode! Ask what information they need in that location.
            ta_clarify = f"{extracted_loc} பகுதியில் உங்களுக்கு என்ன தகவல் வேண்டும்? அரசு ஆரம்ப சுகாதார நிலையங்கள் (PHC), மருத்துவர் வருகை அல்லது மருந்து இருப்பு பற்றி கேட்கலாம்."
            en_clarify = f"What information would you like to know about {extracted_loc}? You can ask about Primary Health Centres (PHC), doctor duty attendance, or medicine stock."

            return IntentClassificationResult(
                intent=IntentType.LOCATION_INFORMATION,
                confidence=0.92,
                extracted_location=extracted_loc,
                is_location_explicit=True,
                needs_clarification=True,
                clarification_prompt_ta=ta_clarify,
                clarification_prompt_en=en_clarify,
            )

    # -------------------------------------------------------------
    # PRIORITY 10.5: GOVERNMENT SCHEMES & WELFARE BENEFITS
    # -------------------------------------------------------------
    scheme_patterns = [
        r"government scheme", r"welfare scheme", r"subsidy", r"subsidies",
        r"scholarship", r"pension scheme", r"cmchis", r"pm[- ]?kisan",
        r"mudra", r"pudhumai penn", r"welfare",
        r"அரசு திட்டம்", r"அரசு மருத்துவ நலத்திட்டங்கள்", r"நலத்திட்டம்", r"மானிய", r"காப்பீடு", r"உதவித்தொகை",
        r"முதியோர் உதவி", r"விதவை உதவி", r"கல்வி உதவி",
    ]
    if any(re.search(p, lowered) for p in scheme_patterns):
        return IntentClassificationResult(
            intent=IntentType.GOVERNMENT_SCHEMES_DISCOVERY,
            confidence=0.92,
        )

    # -------------------------------------------------------------
    # PRIORITY 11: GENERAL CONVERSATION (GREETINGS, THANKS, CHAT)
    # -------------------------------------------------------------
    greeting_patterns = [
        r"^\s*வணக்கம்", r"^\s*hello\b", r"^\s*hi\b", r"^\s*hey\b",
        r"good morning", r"good evening", r"good afternoon",
        r"நன்றி", r"thanks", r"thank you", r"who are you", r"யாரு நீ",
        r"how are you", r"எப்படி இருக்கீங்க", r"bye", r"போய் வருகிறேன்",
    ]
    if any(re.search(p, lowered) for p in greeting_patterns):
        return IntentClassificationResult(
            intent=IntentType.GENERAL_CONVERSATION,
            confidence=0.95,
        )

    # -------------------------------------------------------------
    # PRIORITY 12: UNKNOWN INTENT (DO NOT DUMP FACILITY LIST!)
    # -------------------------------------------------------------
    return IntentClassificationResult(
        intent=IntentType.UNKNOWN_INTENT,
        confidence=0.40,
        extracted_location=extracted_loc,
        is_location_explicit=is_explicit_loc,
        needs_clarification=True,
        clarification_prompt_ta="உங்கள் கேள்வி தெளிவாகப் புரியவில்லை. அரசு ஆரம்ப சுகாதார நிலையங்கள் (PHC), மருத்துவர் பணி விவரம், மருந்து இருப்பு அல்லது அவசர உதவி பற்றி என்னிடம் கேட்கலாம்.",
        clarification_prompt_en="I did not quite understand your question. You can ask me to find nearby Primary Health Centres (PHC), verify doctor duty status, check medicine stock, or call 108 emergency.",
    )
