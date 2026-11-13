"""NALAM Closed-Loop Intent-Driven AI Healthcare Assistant Engine.

Core Philosophy: UNDERSTAND -> CLASSIFY INTENT -> EXTRACT LOCATION -> EXECUTE -> RETRIEVE -> VERIFY -> EXPLAIN -> DISPLAY.
Strict Rule: NEVER merely announce an intention to search. Execute backend tools and return factual records.
Strict Location Rule: NEVER silently substitute requested location with Tiruchengode.
"""
from datetime import date
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.intent_classifier import IntentType, classify_intent
from app.ai.location_extractor import extract_location, get_coordinates_for_location
from app.ai.rag import rag_engine
from app.ai.schemas import (
    AIChatCard,
    AIChatRequest,
    AIChatResponse,
    CardType,
)
from app.ai.session_manager import session_manager
from app.ai.system_prompt import CAREBRIDGE_SYSTEM_PROMPT, TAMIL_TRANSLATIONS
from app.ai.tools import (
    check_doctor_availability_tool,
    check_medicine_stock_tool,
    emergency_guidance_tool,
    get_appointment_slots_tool,
    get_recommendations_tool,
    query_rag_knowledge_tool,
    search_facilities_tool,
)


class NalamAIAgent:
    """Intelligent NALAM Healthcare Assistant with structured Intent-Driven Pipeline."""

    def __init__(self):
        self.system_prompt = CAREBRIDGE_SYSTEM_PROMPT

    async def _build_response(
        self,
        conversation_id: str,
        response_text: str,
        language: str,
        intent: str,
        tools_called: List[str],
        cards: List[AIChatCard],
        rag_sources: Optional[List[Dict[str, Any]]] = None,
        action_taken: Optional[str] = None,
        request: Optional[AIChatRequest] = None,
    ) -> AIChatResponse:
        audio_b64 = None
        duration = None
        v_provider = None

        if request and request.include_audio:
            try:
                # Strip markdown syntax for natural-sounding speech synthesis
                clean_text = re.sub(r"[*#_`\[\]()>-]", " ", response_text).strip()
                clean_text = re.sub(r"\s+", " ", clean_text)[:800]
                from app.ai.gnani_adapter import gnani_adapter
                synth = await gnani_adapter.synthesize(
                    text=clean_text,
                    language=language,
                    voice_name=request.voice_name,
                )
                audio_b64 = synth.get("audio_base64")
                duration = synth.get("duration_seconds")
                v_provider = synth.get("provider")
            except Exception:
                pass

        return AIChatResponse(
            conversation_id=conversation_id,
            response_text=response_text,
            language=language,
            intent=intent,
            tools_called=tools_called,
            cards=cards,
            rag_sources=rag_sources or [],
            action_taken=action_taken,
            audio_base64=audio_b64,
            audio_duration=duration,
            voice_provider=v_provider,
        )

    def detect_language(self, text: str, user_preference: Optional[str] = "auto") -> str:
        """Detects whether user is speaking Tamil or English."""
        if user_preference in ["ta", "en"]:
            return user_preference

        # Count Tamil Unicode characters (U+0B80 to U+0BFF)
        tamil_chars = len(re.findall(r"[\u0B80-\u0BFF]", text))
        latin_chars = len(re.findall(r"[a-zA-Z]", text))

        if tamil_chars > 0:
            total_letters = tamil_chars + latin_chars
            if (tamil_chars / max(total_letters, 1)) >= 0.15:
                return "ta"

        # Check for common spoken Tamil words in Tanglish
        tanglish_patterns = [
            r"\bவணக்கம்\b", r"\bபண்ண\b", r"\bபண்ணனும்\b", r"\bஇருக்கு\b",
            r"\bவேணும்\b", r"\bஎங்கே\b", r"\bமருந்து\b", r"\bடாக்டர்\b",
            r"\bசொல்லு\b", r"\bசொல்லுங்க\b", r"\bகாட்டு\b",
            r"\bpannanum\b", r"\bvenum\b", r"\birukku\b", r"\benga\b",
            r"\benakku\b", r"\bmarunthu\b", r"\bmaruthuvar\b", r"\bvanakkam\b",
            r"\bsollu\b", r"\bsollunga\b"
        ]
        lowered = text.lower()
        if any(re.search(p, lowered) for p in tanglish_patterns):
            return "ta"

        return "en"

    def extract_location(self, text: str, fallback_location: Optional[str] = None) -> Optional[str]:
        """Extracts location or village name from query without hardcoded default fallback."""
        loc, _, is_explicit = extract_location(text)
        if loc:
            return loc
        return fallback_location

    def extract_medicine(self, text: str) -> Optional[str]:
        """Extracts medicine name from query."""
        from app.ai.intent_classifier import extract_medicine_entity
        return extract_medicine_entity(text)

    def _build_symptom_guidance(self, symptom: str, lang: str, message: str) -> str:
        """Builds comprehensive, medically responsible symptom guidance."""
        lowered = message.lower()
        is_child = any(w in lowered for w in ["child", "baby", "infant", "குழந்தை", "சிசு", "பிள்ளை", "kid", "toddler"])
        is_breathing = any(w in lowered for w in ["breathing", "breathe", "மூச்சு", "மூச்சுத்திணறல்"])
        is_severe_pain = any(w in lowered for w in ["severe", "கடுமையான", "தீவிர", "unbearable"])

        if symptom == "fever":
            if lang == "ta":
                text = (
                    "**காய்ச்சல் — முதலுதவி வழிகாட்டுதல்:**\n\n"
                    "நீங்கள் உடல்நலமின்றி இருப்பதாகத் தெரிகிறது. இது ஒரு பொதுவான வழிகாட்டுதல், மருத்துவ ஆலோசனை அல்ல.\n\n"
                    "**உடனடி நடவடிக்கைகள்:**\n"
                    "1. 🌡️ **வெப்பநிலை அளவிடுங்கள்** — தெர்மாமீட்டர் கொண்டு உடல் வெப்பநிலையை சரிபார்க்கவும்.\n"
                    "2. 🛌 **ஓய்வு எடுங்கள்** — கடினமான வேலைகளைத் தவிர்த்து போதுமான ஓய்வு எடுங்கள்.\n"
                    "3. 💧 **நிறைய நீர் பருகுங்கள்** — தண்ணீர், இளநீர், கஞ்சி அல்லது ORS கரைசல் பருகுங்கள். நீரிழப்பைத் தவிர்க்கவும்.\n"
                    "4. 👕 **லேசான ஆடை அணியுங்கள்** — அதிக போர்வைகள் தவிர்க்கவும்.\n"
                    "5. 🚿 **வெதுவெதுப்பான ஈரத் துணியால்** நெற்றி, கழுத்தில் ஒத்தடம் கொடுக்கலாம். குளிர்ந்த நீர் அல்லது ஆல்கஹால் தவிர்க்கவும்.\n"
                    "6. 📊 **சிறுநீர் அளவை கவனியுங்கள்** — குறைவான சிறுநீர் நீரிழப்பின் அறிகுறி.\n\n"
                )
                if is_child:
                    text += (
                        "👶 **குழந்தைகளுக்கு முக்கிய எச்சரிக்கை:**\n"
                        "- 3 மாதத்திற்குக் குறைவான குழந்தைக்கு காய்ச்சல் இருந்தால் **உடனடியாக மருத்துவரை அணுகுங்கள்**.\n"
                        "- குழந்தைகளுக்கு ஆஸ்பிரின் கொடுக்க வேண்டாம்.\n"
                        "- எடையின் அடிப்படையில் மருந்தளவை மருத்துவர் தீர்மானிக்க வேண்டும்.\n\n"
                    )
                text += (
                    "⚠️ **உடனடியாக மருத்துவரை அணுக வேண்டிய அபாய அறிகுறிகள்:**\n"
                    "- மூச்சுத்திணறல் அல்லது நெஞ்சு வலி\n"
                    "- குழப்பம் அல்லது மயக்கம்\n"
                    "- வலிப்பு\n"
                    "- கடுமையான நீரிழப்பு (நீர் அருந்த இயலாமை, தொடர் வாந்தி)\n"
                    "- அசாதாரண இரத்தப்போக்கு\n"
                    "- கடுமையான தலைவலி + பிடரி விறைப்பு\n"
                    "- காய்ச்சல் 3 நாட்களுக்கு மேல் நீடித்தால்\n\n"
                    "🦟 **டெங்கு / மலேரியா விழிப்புணர்வு:**\n"
                    "காய்ச்சலுக்கு பல காரணங்கள் இருக்கலாம். டெங்கு அல்லது மலேரியா சந்தேகம் இருந்தால் ஆஸ்பிரின் / இப்யூபுரோஃபன் தவிர்த்து, "
                    "இரத்தப் பரிசோதனை செய்துகொள்ளுங்கள்.\n\n"
                    "💊 **மருந்து பாதுகாப்பு:**\n"
                    "- பாராசிட்டமால் பொதுவாக பாதுகாப்பானது, ஆனால் அளவு வயது, எடை மற்றும் உடல்நிலையைப் பொறுத்தது.\n"
                    "- மருத்துவர் பரிந்துரை இன்றி ஆன்டிபயாடிக் எடுக்க வேண்டாம்.\n"
                    "- ஒரே நேரத்தில் பாராசிட்டமால் கொண்ட பல மருந்துகள் எடுக்க வேண்டாம்.\n\n"
                    "அவசர உதவிக்கு **108** அழைக்கவும்.\n\n"
                    "---\n*இது பொது வழிகாட்டுதல் மட்டுமே, மருத்துவ ஆலோசனை அல்ல. (ஆதாரம்: MoHFW India, NHM, WHO)*\n\n"
                    "உங்கள் வெப்பநிலை என்ன? எத்தனை நாட்கள் காய்ச்சல் இருக்கிறது?"
                )
            else:
                text = (
                    "**Fever — General First-Aid Guidance:**\n\n"
                    "I'm sorry you're feeling unwell. This is general guidance, not a medical diagnosis or prescription.\n\n"
                    "**Immediate Steps:**\n"
                    "1. 🌡️ **Check your temperature** using a thermometer.\n"
                    "2. 🛌 **Rest** and avoid strenuous activity.\n"
                    "3. 💧 **Drink adequate fluids** — water, coconut water, clear broths, or ORS solution. Monitor for dehydration.\n"
                    "4. 👕 **Wear light, comfortable clothing.** Avoid excessive blankets.\n"
                    "5. 🚿 **Lukewarm sponge** on forehead and neck for comfort. Avoid cold baths or alcohol rubs.\n"
                    "6. 📊 **Monitor urine output** — reduced output may indicate dehydration.\n\n"
                )
                if is_child:
                    text += (
                        "👶 **Important — Children:**\n"
                        "- Fever in infants **younger than 3 months** requires **urgent medical assessment**.\n"
                        "- Do not give aspirin to children unless prescribed.\n"
                        "- Dosage must be weight-based; consult a clinician or pharmacist.\n\n"
                    )
                text += (
                    "⚠️ **Danger Signs — Seek Immediate Medical Help If:**\n"
                    "- Difficulty breathing or chest pain\n"
                    "- Confusion or reduced consciousness\n"
                    "- Seizures\n"
                    "- Severe dehydration (inability to drink, repeated vomiting)\n"
                    "- Unusual bleeding\n"
                    "- Severe headache with neck stiffness\n"
                    "- Fever persisting more than 3 days\n"
                    "- Rapidly worsening condition\n\n"
                    "🦟 **Dengue & Malaria Awareness:**\n"
                    "Fever can have many causes. If dengue or malaria is suspected, avoid aspirin/ibuprofen and get a blood test. "
                    "Do not self-medicate — seek clinical assessment.\n\n"
                    "💊 **Medication Safety:**\n"
                    "- Paracetamol is generally suitable, but dosage depends on age, weight, liver health, and other medicines.\n"
                    "- Do not self-prescribe antibiotics for routine fever.\n"
                    "- Avoid taking multiple products containing paracetamol simultaneously.\n"
                    "- When in doubt, consult a clinician or pharmacist.\n\n"
                    "For emergencies, call **108**.\n\n"
                    "---\n*This is general guidance only, not a diagnosis or prescription. (Sources: MoHFW India, NHM, WHO, NHS)*\n\n"
                    "Can you tell me your measured temperature and how many days you have had fever?"
                )
            return text

        # General symptom guidance for non-fever symptoms
        if lang == "ta":
            return (
                "**நல்வாழ்வு முதலுதவி & கவனிப்பு வழிகாட்டுதல்:**\n\n"
                "1. **ஓய்வு மற்றும் நீரேற்றம்:** போதுமான அளவு நீர், கஞ்சி அல்லது ORS பருகி உடலை நீரேற்றமாக வைத்திருங்கள்.\n"
                "2. **அறிகுறிகளை கவனியுங்கள்:** வெப்பநிலை, வலி, மூச்சு சிரமம் போன்றவற்றை தொடர்ந்து கண்காணியுங்கள்.\n"
                "3. **சுய மருத்துவம் தவிர்க்கவும்:** மருத்துவர் பரிந்துரை இன்றி ஆன்டிபயாடிக் அல்லது வலி நிவாரணிகளை உட்கொள்ளாதீர்கள்.\n\n"
                "⚠️ **எப்போது உடனடியாக மருத்துவரை அணுக வேண்டும்?**\n"
                "- காய்ச்சல் 3 நாட்களுக்கு மேல் நீடித்தால்\n"
                "- மூச்சுத்திணறல், நெஞ்சு வலி அல்லது தொடர் வாந்தி\n"
                "- மயக்கம், வலிப்பு அல்லது தீவிர உடல் சோர்வு\n"
                "- கடுமையான வயிற்று வலி அல்லது அசாதாரண இரத்தப்போக்கு\n\n"
                "*அருகிலுள்ள அரசு ஆரம்ப சுகாதார நிலையத்தில் (PHC) பரிசோதித்துக் கொள்ளவும். அவசர உதவிக்கு 108 அழைக்கவும்.*\n\n"
                "---\n*பொது வழிகாட்டுதல் மட்டுமே, மருத்துவ ஆலோசனை அல்ல. (ஆதாரம்: MoHFW India, NHM, WHO)*"
            )
        else:
            return (
                "**Symptom Guidance & Supportive First-Aid:**\n\n"
                "1. **Rest & Hydration:** Drink plenty of fluids (boiled water, clear broths, or ORS solution).\n"
                "2. **Monitor Symptoms:** Track temperature, pain levels, and breathing regularly.\n"
                "3. **Avoid Self-Medication:** Do not self-prescribe antibiotics or unverified drugs.\n\n"
                "⚠️ **Seek Immediate Medical Attention If:**\n"
                "- Fever lasting more than 3 days\n"
                "- Difficulty breathing, chest pain, or severe persistent vomiting\n"
                "- Confusion, seizures, or extreme weakness\n"
                "- Severe abdominal pain or unusual bleeding\n\n"
                "*Please consult a medical officer at your nearest Primary Health Centre. Call 108 for emergencies.*\n\n"
                "---\n*General guidance only, not a diagnosis or prescription. (Sources: MoHFW India, NHM, WHO, NHS)*"
            )

    async def execute_turn(
        self,
        request: AIChatRequest,
        db: AsyncSession,
    ) -> AIChatResponse:
        """Executes a single conversational turn with Intent Classification and Contextual Routing."""
        message = request.message.strip()
        conv_id = request.conversation_id or str(uuid.uuid4())
        lang = self.detect_language(message, request.language)

        # 1. Retrieve or initialize multi-turn session
        session = session_manager.get_or_create(conv_id)

        # 2. Structured Intent Classification & Entity Extraction
        # Note: Do NOT inject Tiruchengode as default fallback location!
        classification = classify_intent(
            message=message,
            language=lang,
            session=session,
            user_home_village=request.location_context,
        )

        resolved_loc = classification.extracted_location or session.active_location
        tools_called: List[str] = []
        cards: List[AIChatCard] = []
        rag_sources: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # BRANCH 1: EMERGENCY HELP & 108 AMBULANCE PROTOCOL
        # -------------------------------------------------------------
        if classification.intent in [IntentType.EMERGENCY_HELP, IntentType.AMBULANCE_INFORMATION]:
            tools_called.append("emergency_guidance_tool")
            eg_data = emergency_guidance_tool(message)

            cards.append(AIChatCard(
                type=CardType.EMERGENCY,
                title="🚨 அவசர மருத்துவ உதவி (Call 108)" if lang == "ta" else "🚨 Medical Emergency (Call 108)",
                subtitle="Tamil Nadu / National Emergency Ambulance Service",
                badge="108 AMBULANCE",
                badge_color="red",
                details={
                    "emergency_phone": "108",
                    "instruction": eg_data["instruction_ta"] if lang == "ta" else eg_data["instruction_en"],
                    "nearby_24x7_trauma_centres": eg_data["nearest_24x7_facilities"],
                },
                action={"label": "Call 108 Now", "type": "CALL", "target": "108"},
            ))

            resp_text = (
                f"**{eg_data['instruction_ta']}**\n\n"
                f"அருகிலுள்ள 24 மணி நேர தீவிர சிகிச்சை மையங்கள்:\n"
                + "\n".join(f"- {f}" for f in eg_data["nearest_24x7_facilities"])
                if lang == "ta"
                else f"**{eg_data['instruction_en']}**\n\n"
                f"Nearest 24x7 emergency facilities with inpatient trauma care:\n"
                + "\n".join(f"- {f}" for f in eg_data["nearest_24x7_facilities"])
            )

            session.add_turn(message, lang, classification.intent.value, resolved_loc, tools_called, resp_text)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=resp_text,
                language=lang,
                intent="EMERGENCY_DISPATCH",
                tools_called=tools_called,
                cards=cards,
                action_taken="TRIGGER_EMERGENCY_PROTOCOL",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 2: CLINICAL SAFETY GUARD (DOSAGE / PRESCRIPTION ATTEMPTS)
        # -------------------------------------------------------------
        if classification.intent == IntentType.CLINICAL_SAFETY:
            target_loc = resolved_loc or "Tiruchengode"
            tools_called.append("search_facilities_tool")
            fac_res = await search_facilities_tool(db, location_name=target_loc, limit=2)

            for f in fac_res.get("facilities", []):
                doc_name = f["doctors"][0]["name"] if f["doctors"] else "Medical Officer on duty"
                doc_status = f["doctors"][0]["attendance_status"] if f["doctors"] else "UNKNOWN"
                cards.append(AIChatCard(
                    type=CardType.FACILITY,
                    title=f["name"],
                    subtitle=f"{f['facility_type']} • {f.get('distance_km', '0')} km away",
                    badge=f"Doctor: {doc_status}",
                    badge_color="green" if doc_status == "PRESENT" else "yellow",
                    details={
                        "address": f["address"],
                        "doctor": doc_name,
                        "services": f["services"][:4],
                    },
                    action={"label": "Book Consultation", "type": "BOOK", "facility_id": f["facility_id"]},
                ))

            refusal_text = (
                "**மருத்துவ பாதுகாப்பு வழிகாட்டுதல்:**\n"
                "நலம் (NALAM) ஒரு மருத்துவ நோயறிதல் அல்லது மருந்து பரிந்துரை தளம் அல்ல. "
                "மருந்துகளின் அளவு மற்றும் சிகிச்சையை பதிவுபெற்ற அரசு மருத்துவர் மட்டுமே தீர்மானிக்க முடியும்.\n\n"
                f"உங்கள் உடல்நிலையை பரிசோதிக்க, **{target_loc}** பகுதியில் உள்ள அரசு ஆரம்ப சுகாதார நிலையத்திற்கு செல்லுமாறு பரிந்துரைக்கிறோம். "
                "அங்கு மருத்துவர் பணியில் உள்ளார்."
                if lang == "ta"
                else "**Clinical Safety Disclaimer:**\n"
                "NALAM strictly does not provide medical diagnoses, prescriptions, or drug dosage recommendations. "
                "Only a licensed physician can determine the correct medicine dosage for your condition.\n\n"
                f"Please consult a doctor at your nearest Primary Health Centre in **{target_loc}**. "
                "See available facilities and doctor schedules below:"
            )

            session.add_turn(message, lang, classification.intent.value, resolved_loc, tools_called, refusal_text)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=refusal_text,
                language=lang,
                intent="CLINICAL_DISCLAIMER_ENFORCEMENT",
                tools_called=tools_called,
                cards=cards,
                action_taken="NON_DIAGNOSTIC_REDIRECT",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 3: SYMPTOM GUIDANCE (COMPREHENSIVE, MEDICALLY RESPONSIBLE)
        # -------------------------------------------------------------
        if classification.intent == IntentType.SYMPTOM_GUIDANCE:
            symptom = classification.extracted_symptom or "general"
            guidance_text = self._build_symptom_guidance(symptom, lang, message)

            session.add_turn(message, lang, classification.intent.value, resolved_loc, tools_called, guidance_text)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=guidance_text,
                language=lang,
                intent="SYMPTOM_GUIDANCE",
                tools_called=tools_called,
                cards=[],
                action_taken="PROVIDE_SYMPTOM_GUIDANCE",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 3B: SYMPTOM + FACILITY COMBINED
        # -------------------------------------------------------------
        if classification.intent == IntentType.SYMPTOM_WITH_FACILITY:
            symptom = classification.extracted_symptom or "general"
            guidance_text = self._build_symptom_guidance(symptom, lang, message)

            # Also search for facilities
            loc = classification.extracted_location or session.active_location
            fac_type = classification.extracted_facility_type
            own = classification.entities.get("ownership")

            if loc:
                tools_called.append("search_facilities_tool")
                fac_data = await search_facilities_tool(
                    db,
                    location_name=loc,
                    facility_type=fac_type,
                    ownership=own,
                    limit=3,
                )
                matched = fac_data.get("facilities", [])
                sub_loc = fac_data.get("query_sub_locality")

                if matched:
                    loc_label = sub_loc or loc
                    if lang == "ta":
                        guidance_text += f"\n\n---\n\n**{loc_label} பகுதியில் உள்ள மருத்துவமனைகள்:**\n"
                    else:
                        guidance_text += f"\n\n---\n\n**Verified Healthcare Facilities in {loc_label}:**\n"

                    for f in matched:
                        f_locality = f.get("locality") or f.get("block") or f.get("district") or ""
                        phone = f.get("official_phone") or f.get("emergency_contact")
                        method = f.get("appointment_booking_method", "WALK_IN_ONLY")
                        hours = f.get("opening_hours") or ""

                        if lang == "ta":
                            booking_desc = "நேரடி OPD பதிவு" if method == "WALK_IN_ONLY" else f"இணைய முன்பதிவு: {f.get('online_booking_url', '')}"
                            guidance_text += (
                                f"- **{f['name']}** ({f.get('ownership', '')}) — {f_locality}\n"
                                f"  - முகவரி: {f['address']}\n"
                                f"  - தொலைபேசி: {phone or 'பட்டியலிடப்படவில்லை'}\n"
                                f"  - நேரம்: {hours}\n"
                                f"  - முன்பதிவு: {booking_desc}\n"
                            )
                        else:
                            booking_desc = "Walk-in OPD registration" if method == "WALK_IN_ONLY" else f"Online: {f.get('online_booking_url', '')}"
                            guidance_text += (
                                f"- **{f['name']}** ({f.get('ownership', '')}) — {f_locality}\n"
                                f"  - Address: {f['address']}\n"
                                f"  - Phone: {phone or 'Not listed'}\n"
                                f"  - Hours: {hours}\n"
                                f"  - Booking: {booking_desc}\n"
                            )

                        cards.append(AIChatCard(
                            type=CardType.FACILITY,
                            title=f["name"],
                            subtitle=f"{f.get('ownership', '')} • {f_locality}",
                            badge="24x7 EMERGENCY" if f.get("emergency_services") else f["facility_type"],
                            badge_color="red" if f.get("emergency_services") else "blue",
                            details={"address": f["address"], "phone": phone or "Not listed", "hours": hours},
                            action={"label": f"Call {phone}", "type": "CALL", "target": phone} if phone else {"label": "Walk-in OPD", "type": "INFO"},
                        ))
                else:
                    if lang == "ta":
                        guidance_text += f"\n\n---\n\n**{sub_loc or loc} பகுதியில் சரிபார்க்கப்பட்ட மருத்துவமனை தகவல்கள் நலம் தரவுத்தளத்தில் இல்லை.** அவசர உதவிக்கு **108** அழைக்கவும்."
                    else:
                        guidance_text += f"\n\n---\n\n**No verified facility records found for {sub_loc or loc} in the NALAM database.** For emergencies, call **108**."

            session.add_turn(message, lang, classification.intent.value, resolved_loc, tools_called, guidance_text)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=guidance_text,
                language=lang,
                intent="SYMPTOM_WITH_FACILITY",
                tools_called=tools_called,
                cards=cards,
                action_taken="PROVIDE_SYMPTOM_GUIDANCE_WITH_FACILITIES",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 4: DOCTOR AVAILABILITY INTENT
        # -------------------------------------------------------------
        if classification.intent == IntentType.DOCTOR_AVAILABILITY:
            target_loc = resolved_loc
            tools_called.append("check_doctor_availability_tool")
            doc_data = await check_doctor_availability_tool(db, location_name=target_loc)
            doctor_items = doc_data.get("doctors", [])

            lines = []
            loc_label = f" in {target_loc}" if target_loc else ""
            loc_label_ta = f" ({target_loc} பகுதி)" if target_loc else ""

            if not doctor_items:
                if lang == "ta":
                    lines.append(
                        f"**{target_loc or 'கோரப்பட்ட'} பகுதியில் தற்போது பதிவுசெய்யப்பட்ட மருத்துவர் பணி விவரங்கள் கிடைக்கவில்லை.**\n\n"
                        "அருகிலுள்ள பிற சுகாதார நிலையங்களின் மருத்துவர் வருகையை அறிய வேறு இருப்பிடத்தை குறிப்பிடலாம் அல்லது ஆரம்ப சுகாதார நிலையத்திற்கு நேரடியாகச் செல்லலாம்."
                    )
                else:
                    lines.append(
                        f"**No verified doctor duty records were found directly matching{loc_label} for today ({date.today().isoformat()}).**\n\n"
                        "You can specify an alternate town or village to check doctor rosters at nearby primary health facilities."
                    )
            else:
                if lang == "ta":
                    lines.append(f"**மருத்துவர் பணி மற்றும் வருகை விவரங்கள்{loc_label_ta} ({date.today().isoformat()}):**\n")
                else:
                    lines.append(f"**Verified Doctor Duty & Attendance Status{loc_label} (Date: {date.today().isoformat()}):**\n")

                for d in doctor_items[:4]:
                    status = d["attendance_status"]
                    badge_color = "green" if status == "PRESENT" else ("yellow" if status == "EXPECTED" else ("red" if status == "ABSENT" else "blue"))
                    status_label = (
                        "பணியில் உள்ளார் (உறுதிசெய்யப்பட்டது)" if status == "PRESENT"
                        else ("திட்டமிடப்பட்ட பணி (வருகை நிலுவையில்)" if status == "EXPECTED"
                              else ("விடுப்பில் உள்ளார்" if status == "ABSENT" else "வருகை விவரம் கிடைக்கவில்லை"))
                    ) if lang == "ta" else (
                        "Physically verified on duty" if status == "PRESENT"
                        else ("Rostered shift; check-in pending" if status == "EXPECTED"
                              else ("On leave" if status == "ABSENT" else "Attendance unlogged"))
                    )

                    cards.append(AIChatCard(
                        type=CardType.DOCTOR,
                        title=d["name"],
                        subtitle=f"{d['specialization']} • {d['facility_name']}",
                        badge=status,
                        badge_color=badge_color,
                        details={
                            "qualification": d.get("qualification"),
                            "shift_hours": d.get("shift_hours"),
                            "notes": d.get("notes"),
                            "status_description": status_label,
                        },
                        action={"label": "Book Appointment Slot", "type": "BOOK", "doctor_id": d["doctor_id"]},
                    ))

                    if lang == "ta":
                        lines.append(
                            f"- **{d['name']}** ({d['specialization']}) – {d['facility_name']}\n"
                            f"  - நிலை: `{status}` ({status_label})\n"
                            f"  - நேரம்: {d.get('shift_hours', 'N/A')}\n"
                        )
                    else:
                        lines.append(
                            f"- **{d['name']}** ({d['specialization']}, {d.get('qualification', '')}) at **{d['facility_name']}**\n"
                            f"  - Attendance: `{status}` ({status_label})\n"
                            f"  - Shift Hours: {d.get('shift_hours', 'N/A')}\n"
                        )

                lines.append(
                    "\n*NALAM verifies physical biometric and duty-desk check-ins (PRESENT) vs planned shifts (EXPECTED) to eliminate wasted trips.*"
                    if lang == "en"
                    else "\n*நலம் தளம் வீண் பயணங்களைத் தடுக்க திட்டமிடப்பட்ட பணிகளையும் (EXPECTED), உண்மையான பணி வருகையையும் (PRESENT) தனித்தனியாக காட்டுகிறது.*"
                )

            resp_text = "\n".join(lines)
            session.add_turn(message, lang, classification.intent.value, resolved_loc, tools_called, resp_text)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=resp_text,
                language=lang,
                intent="DOCTOR_AVAILABILITY_LOOKUP",
                tools_called=tools_called,
                cards=cards,
                action_taken="FETCH_DOCTOR_SCHEDULES",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 5: APPOINTMENT BOOKING INTENT
        # -------------------------------------------------------------
        if classification.intent == IntentType.APPOINTMENT_BOOKING:
            target_loc = resolved_loc
            tools_called.append("get_appointment_slots_tool")
            slots_data = await get_appointment_slots_tool(db, location_name=target_loc)
            options = slots_data.get("options", [])

            lines = []
            if not options:
                if lang == "ta":
                    lines.append(
                        f"**{target_loc or 'கோரப்பட்ட'} பகுதியில் சரிபார்க்கப்பட்ட மருத்துவமனை முன்பதிவு தகவல்கள் தற்போது நலம் தரவுத்தளத்தில் இல்லை.**\n\n"
                        "நலம் தளம் போலி முன்பதிவு எண்களையோ மாதிரி நேரங்களையோ உருவாக்காது. "
                        "அரசு மருத்துவமனைகளில் காலை 07:30 முதல் நேரடி பதிவு கவுண்டர் மூலம் டோக்கன் பெறலாம். "
                        "அவசர சிகிச்சைக்கு உடனடியாக **108** ஆம்புலன்ஸை அழைக்கவும்."
                    )
                else:
                    lines.append(
                        f"**No verified appointment booking records were found for {target_loc or 'the requested location'} in the NALAM database.**\n\n"
                        "NALAM strictly adheres to zero-fabrication clinical safety and never generates fake appointment confirmation IDs or mock slots. "
                        "For Government facilities, consultations operate via direct on-site Walk-In OPD Registration (07:30 AM – 12:00 PM). "
                        "For medical emergencies, call **108** immediately."
                    )
            else:
                loc_txt = f" ({target_loc} பகுதி)" if target_loc else ""
                loc_txt_en = f" in {target_loc}" if target_loc else ""

                if lang == "ta":
                    lines.append(f"**மருத்துவமனை முன்பதிவு மற்றும் பதிவு வழிகாட்டுதல்{loc_txt}:**\n")
                    lines.append(
                        "தமிழ்நாடு பொது சுகாதார அமைப்பில், அரசு மருத்துவமனைகள் (CMCH, தாலுகா மருத்துவமனைகள்) மற்றும் PHC-களில் "
                        "முன்பதிவு இணைய வழியில் வழங்கப்படுவதில்லை; மருத்துவமனை புறநோயாளி (OPD) கவுண்டரில் நேரடி பதிவு மட்டுமே நடைபெறும். "
                        "அங்கீகரிக்கப்பட்ட தனியார் மருத்துவமனைகளில் அதிகாரப்பூர்வ இணையதளம் மூலம் முன்பதிவு செய்யலாம்.\n"
                    )
                else:
                    lines.append(f"**Verified Healthcare Appointment & Registration Guidance{loc_txt_en}:**\n")
                    lines.append(
                        "In Tamil Nadu public health infrastructure, all Government Hospitals (CMCH, Taluk Hospitals) and PHCs "
                        "operate strictly via **on-site Walk-In OPD Registration** at hospital counters (typically 07:30 AM – 12:00 PM). "
                        "Emergency casualties operate 24x7 with no appointment required. "
                        "Verified private hospitals offer online appointment portals and dedicated booking telephone desks.\n"
                    )

                for opt in options[:4]:
                    method = opt.get("booking_method", "WALK_IN_ONLY")
                    fac_name = opt["facility_name"]
                    phone = opt.get("booking_phone")
                    online_url = opt.get("online_booking_url")
                    inst = opt["instructions_ta"] if lang == "ta" else opt["instructions_en"]
                    badge_label = "WALK-IN OPD" if method == "WALK_IN_ONLY" else "ONLINE BOOKING"
                    badge_col = "blue" if method == "WALK_IN_ONLY" else "green"

                    # Card action
                    if method == "ONLINE_BOOKING_AVAILABLE" and online_url:
                        c_action = {
                            "label": "Official Booking Portal" if lang == "en" else "இணைய முன்பதிவு",
                            "type": "LINK",
                            "url": online_url,
                        }
                    elif phone:
                        c_action = {
                            "label": f"Call {phone}",
                            "type": "CALL",
                            "target": phone,
                        }
                    else:
                        c_action = {
                            "label": "Walk-in OPD Info" if lang == "en" else "நேரடி பதிவு விவரம்",
                            "type": "INFO",
                        }

                    docs_summary = []
                    for d in opt.get("verified_doctors", []):
                        docs_summary.append(f"{d['doctor_name']} ({d['specialization']}) - {d['doctor_status']}")

                    cards.append(AIChatCard(
                        type=CardType.APPOINTMENT,
                        title=fac_name,
                        subtitle=f"{opt.get('ownership', 'Hospital')} • {opt.get('locality') or opt.get('district') or 'Coimbatore'}",
                        badge=badge_label,
                        badge_color=badge_col,
                        details={
                            "booking_method": method,
                            "instructions": inst,
                            "phone": phone or "Not listed",
                            "online_portal": online_url or "N/A (Walk-in only)",
                            "emergency_services": "24x7 Available" if opt.get("emergency_services") else "Standard hours",
                            "doctors": ", ".join(docs_summary) if docs_summary else "Roster pending",
                        },
                        action=c_action,
                    ))

                    if lang == "ta":
                        lines.append(
                            f"- **{fac_name}** ({opt.get('ownership', 'மருத்துவமனை')}): `{badge_label}`\n"
                            f"  - பதிவு முறை: {inst}\n"
                            f"  - தொடர்பு: {phone or 'நேரடி அணுகல்'}\n"
                        )
                    else:
                        lines.append(
                            f"- **{fac_name}** ({opt.get('ownership', 'Hospital')}): `{badge_label}`\n"
                            f"  - Procedure: {inst}\n"
                            f"  - Official Contact: {phone or 'On-site counter'}\n"
                        )

                lines.append(
                    "\n*Strict Clinical Safety Rule: NALAM never fabricates fake booking confirmations or synthetic appointment tokens.*"
                    if lang == "en"
                    else "\n*மருத்துவ பாதுகாப்பு விதி: நலம் தளம் போலியான முன்பதிவு டோக்கன்களையோ உறுதிப்படுத்தல் எண்களையோ ஒருபோதும் வழங்காது.*"
                )

            resp_text = "\n".join(lines)
            session.add_turn(message, lang, classification.intent.value, resolved_loc, tools_called, resp_text)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=resp_text,
                language=lang,
                intent="APPOINTMENT_BOOKING_FLOW",
                tools_called=tools_called,
                cards=cards,
                action_taken="PRESENT_APPOINTMENT_SLOTS",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 6: MEDICINE STOCK & INVENTORY INTELLIGENCE
        # -------------------------------------------------------------
        if classification.intent in [IntentType.MEDICINE_SEARCH, IntentType.MEDICINE_AVAILABILITY]:
            med_name = classification.extracted_medicine or session.active_medicine or "Paracetamol"
            target_loc = resolved_loc
            tools_called.append("check_medicine_stock_tool")
            stock_data = await check_medicine_stock_tool(db, medicine_name=med_name, location_name=target_loc)

            lines = []
            loc_label = f" near {target_loc}" if target_loc else ""
            loc_label_ta = f" ({target_loc} பகுதி)" if target_loc else ""

            if lang == "ta":
                lines.append(f"**{med_name} மருந்து இருப்பு விவரங்கள்{loc_label_ta}:**\n")
            else:
                lines.append(f"**Probabilistic Availability for {med_name}{loc_label}:**\n")

            facilities_list = stock_data.get("facilities", [])
            for sf in facilities_list[:4]:
                label = sf["availability_label"]
                prob = sf["p_available"]
                badge_color = "green" if label == "LIKELY" else ("yellow" if label == "UNCERTAIN" else "red")

                cards.append(AIChatCard(
                    type=CardType.MEDICINE,
                    title=sf["facility_name"],
                    subtitle=f"{med_name} • {sf['facility_type']}",
                    badge=f"{label} ({int(prob*100)}%)",
                    badge_color=badge_color,
                    details={
                        "availability_probability": prob,
                        "confidence": sf["confidence"],
                        "label": label,
                        "evidence_reports": sf.get("evidence_count", 0),
                        "address": sf["address"],
                    },
                    action={"label": "View Facility", "type": "NAVIGATE", "facility_id": sf["facility_id"]},
                ))

                if lang == "ta":
                    ta_label = "கிடைக்க அதிக வாய்ப்புள்ளது" if label == "LIKELY" else ("உறுதியாகத் தெரியவில்லை" if label == "UNCERTAIN" else "இருப்பு இல்லை")
                    lines.append(
                        f"- **{sf['facility_name']}** ({sf['facility_type']}): `{label}` (சாத்தியக்கூறு: {int(prob*100)}%)\n"
                        f"  - நிலை: {ta_label}\n"
                    )
                else:
                    lines.append(
                        f"- **{sf['facility_name']}** ({sf['facility_type']}): `{label}` ($P={prob:.2f}$, Confidence: {sf['confidence']:.2f})\n"
                        f"  - Recommendation: {'Safe to visit for refill' if label == 'LIKELY' else 'High risk of wasted trip; check alternate facility'}\n"
                    )

            lines.append("\n*Availability states are computed dynamically using Bayesian decay on weighted staff and ASHA reports.*")

            resp_text = "\n".join(lines)
            session.add_turn(message, lang, classification.intent.value, resolved_loc, tools_called, resp_text)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=resp_text,
                language=lang,
                intent="MEDICINE_STOCK_LOOKUP",
                tools_called=tools_called,
                cards=cards,
                action_taken="FETCH_MEDICINE_BELIEFS",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 7: PLATFORM INFORMATION & RAG ARCHITECTURE
        # -------------------------------------------------------------
        if classification.intent == IntentType.PLATFORM_INFORMATION:
            tools_called.append("query_rag_knowledge_tool")
            rag_res = query_rag_knowledge_tool(message, top_k=3)
            rag_sources = rag_res.get("sources", [])

            for s in rag_sources:
                cards.append(AIChatCard(
                    type=CardType.RAG_SOURCE,
                    title=f"{s['document']} — {s['section']}",
                    subtitle=f"Relevance Score: {s['score']}",
                    badge="DOC SOURCE",
                    badge_color="purple",
                    details={
                        "document": s["document"],
                        "section": s["section"],
                        "snippet": s["content"][:300] + "...",
                    },
                ))

            lowered = message.lower()
            if "loss" in lowered or "recommend" in lowered or "calculate" in lowered or "சூத்திரம்" in lowered:
                explanation = (
                    "### NALAM Healthcare Recommendation & Expected Trip Loss Algorithm\n\n"
                    "Unlike traditional healthcare locators that sort solely by raw distance, **NALAM routes patients by minimizing the risk of a wasted journey**.\n\n"
                    "#### The Mathematical Loss Formula:\n"
                    "$$\\text{Expected Loss} = \\text{RoundHalfUp}(\\text{Failure Probability} \\times \\text{Travel Cost})$$\n\n"
                    "Where:\n"
                    "1. **Travel Cost ($C$)**: Distance between the patient's village and facility multiplied by transportation tier cost: $\\text{Cost} = \\text{Base} + (\\text{Cost/km} \\times \\text{km})$.\n"
                    "2. **Failure Probability ($P_{\\text{fail}}$)**:\n"
                    "   - For **Consultations**: $P_{\\text{fail}}$ increases heavily if the doctor is not physically present (`PRESENT` $\\implies 0.05$, `EXPECTED` $\\implies 0.35$, `ABSENT` $\\implies 0.80$).\n"
                    "   - For **Medicine Refills**: $P_{\\text{fail}} = 1.0 - P_{\\text{available}}$. If medicine stock is `UNLIKELY`, visit failure risk is high.\n\n"
                    "*Source Citation: `STOCK_ALGORITHM.md` & `README.md`*"
                )
            elif "pin" in lowered or "ivr" in lowered or "lockout" in lowered:
                explanation = (
                    "### NALAM IVR Voice Telephony Access & Security Policy\n\n"
                    "NALAM provides button-phone voice access via standard keypad telephony (DTMF) in Tamil (`1`) and English (`2`).\n\n"
                    "#### PIN Authentication & Security Policy:\n"
                    "- Callers authenticate with their registered Phone Number and 4-digit PIN.\n"
                    "- **Maximum Attempts:** `3` consecutive failed attempts.\n"
                    "- **Lockout Duration:** `15 minutes` lockout period.\n"
                    "- **Emergency Exemption:** Pressing `7` or stating an emergency immediately bridges to 108 emergency ambulance protocols.\n\n"
                    "*Source Citation: `IVR_CALL_FLOWS.md` & `FINAL_SECURITY_AUDIT.md`*"
                )
            else:
                top_content = rag_sources[0]["content"] if rag_sources else "NALAM Architecture Documentation"
                explanation = (
                    f"### NALAM Platform Documentation Overview\n\n"
                    f"{top_content}\n\n"
                    f"*Sources: {', '.join(s['document'] for s in rag_sources)}*"
                )

            session.add_turn(message, lang, classification.intent.value, resolved_loc, tools_called, explanation)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=explanation,
                language=lang,
                intent="PROJECT_DOCUMENTATION_RAG",
                tools_called=tools_called,
                cards=cards,
                rag_sources=rag_sources,
                action_taken="RAG_DOCUMENT_RETRIEVAL",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 8: GENERAL HEALTH INFORMATION
        # -------------------------------------------------------------
        if classification.intent == IntentType.HEALTH_INFORMATION:
            if lang == "ta":
                info_text = (
                    "**பொது சுகாதார விழிப்புணர்வு வழிகாட்டல்:**\n\n"
                    "- **நீரேற்றம் & வெயில் பாதுகாப்பு:** போதுமான அளவு நீர் பருகி நீரிழப்பைத் தவிர்க்கவும். ஓஆர்எஸ் (ORS) கரைசலை நீரிழப்புக்கு பயன்படுத்தலாம்.\n"
                    "- **சத்தான உணவு:** காய்கறிகள், கீரைகள் மற்றும் புரதச்சத்து நிறைந்த உணவுகள் உடலின் நோய் எதிர்ப்பு சக்தியை அதிகரிக்கும்.\n"
                    "- **தடுப்பூசிகள்:** குழந்தைகள் மற்றும் கர்ப்பிணி தாய்மார்கள் அரசு ஆரம்ப சுகாதார நிலையங்களில் குறித்த நேரத்தில் தடுப்பூசி போட்டுக்கொள்வது அவசியம்.\n\n"
                    "*குறிப்பிட்ட உடல்நல ஆலோசனைகளுக்கு அருகிலுள்ள அரசு மருத்துவரை அணுகவும்.*"
                )
            else:
                info_text = (
                    "**Public Health Information & Preventive Care:**\n\n"
                    "- **Hydration & Heat Safety:** Drink adequate clean water to prevent dehydration. Use Oral Rehydration Salts (ORS) during fluid loss.\n"
                    "- **Nutrition & Hygiene:** A balanced diet rich in local vegetables, pulses, and greens boosts immunity.\n"
                    "- **Immunization:** Timely routine immunizations are available free of charge at all Primary Health Centres.\n\n"
                    "*For clinical advice tailored to your medical history, please consult a registered medical officer at your local PHC.*"
                )

            session.add_turn(message, lang, classification.intent.value, resolved_loc, tools_called, info_text)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=info_text,
                language=lang,
                intent="HEALTH_INFORMATION",
                tools_called=tools_called,
                cards=[],
                action_taken="PROVIDE_HEALTH_INFORMATION",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 9: LOCATION CLARIFICATION / "கோயம்புத்தூர்ல சொல்லு"
        # -------------------------------------------------------------
        # If user provided a location statement without active healthcare context:
        # e.g. "கோயம்புத்தூர்ல சொல்லு." or "What about Salem?"
        if classification.intent == IntentType.LOCATION_INFORMATION and classification.needs_clarification:
            loc = classification.extracted_location or "Coimbatore"
            clarify_text = (
                classification.clarification_prompt_ta
                if lang == "ta"
                else classification.clarification_prompt_en
            )

            session.add_turn(message, lang, classification.intent.value, loc, tools_called, clarify_text)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=clarify_text,
                language=lang,
                intent="LOCATION_CLARIFICATION_REQUIRED",
                tools_called=tools_called,
                cards=[],
                action_taken="PROMPT_FOR_LOCATION_SERVICES",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 10: GENERAL CONVERSATION (GREETINGS / THANKS)
        # -------------------------------------------------------------
        if classification.intent == IntentType.GENERAL_CONVERSATION:
            if lang == "ta":
                welcome_text = (
                    "வணக்கம்! நான் நலம் (NALAM) AI நல்வாழ்வு உதவியாளர்.\n\n"
                    "உங்களுக்கு தேவையான தகவலைக் கேளுங்கள்:\n"
                    "- அரசு ஆரம்ப சுகாதார நிலையங்களை (PHC) கண்டறிய\n"
                    "- மருத்துவர் பணி வருகையை சரிபார்க்க\n"
                    "- மருந்து இருப்பை அறிய\n"
                    "- அவசர மருத்துவ உதவி (Call 108)"
                )
            else:
                welcome_text = (
                    "Hello! I am your NALAM AI Healthcare Assistant.\n\n"
                    "How can I help you today? You can ask me to:\n"
                    "- Find nearby Primary Health Centres (PHC)\n"
                    "- Check verified doctor duty and attendance\n"
                    "- Check medicine stock availability\n"
                    "- Access 108 Emergency ambulance protocols"
                )

            session.add_turn(message, lang, classification.intent.value, resolved_loc, tools_called, welcome_text)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=welcome_text,
                language=lang,
                intent="GENERAL_CONVERSATION",
                tools_called=tools_called,
                cards=[],
                action_taken="RESPOND_CONVERSATIONAL",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 11: UNKNOWN INTENT (ASK CLARIFICATION, DO NOT DUMP PHCs!)
        # -------------------------------------------------------------
        if classification.intent == IntentType.UNKNOWN_INTENT:
            clarify_msg = (
                classification.clarification_prompt_ta
                if lang == "ta"
                else classification.clarification_prompt_en
            )
            session.add_turn(message, lang, classification.intent.value, resolved_loc, tools_called, clarify_msg)
            return await self._build_response(
                conversation_id=conv_id,
                response_text=clarify_msg,
                language=lang,
                intent="UNKNOWN_INTENT_CLARIFICATION",
                tools_called=tools_called,
                cards=[],
                action_taken="REQUEST_INTENT_CLARIFICATION",
                request=request,
            )

        # -------------------------------------------------------------
        # BRANCH 12: FACILITY SEARCH INTENT
        # -------------------------------------------------------------
        loc = classification.extracted_location or session.active_location
        fac_type = classification.extracted_facility_type
        ownership = classification.entities.get("ownership")
        service = classification.entities.get("service")
        maternity = True if (service == "maternity") else None
        emergency = True if (service == "emergency") else None

        # If user asked about Coimbatore generally or no location was given in a Coimbatore context
        if not loc and (fac_type or service or ownership):
            loc = "Coimbatore"

        tools_called.append("search_facilities_tool")
        fac_data = await search_facilities_tool(
            db,
            location_name=loc,
            facility_type=fac_type,
            ownership=ownership,
            service=service,
            maternity=maternity,
            emergency=emergency,
            limit=5,
        )

        matched_facilities = fac_data.get("facilities", [])
        in_range = fac_data.get("in_range", len(matched_facilities) > 0)
        sub_locality = fac_data.get("query_sub_locality")
        lines = []

        if not in_range or not matched_facilities:
            nearest_name = fac_data.get("nearest_facility_name")
            display_loc = sub_locality or loc or "the requested location"

            if lang == "ta":
                lines.append(
                    f"**{display_loc} பகுதியில் உங்கள் அளவுகோல்களுக்குப் பொருந்தக்கூடிய சரிபார்க்கப்பட்ட மருத்துவமனைகள் நலம் தரவுத்தளத்தில் இல்லை.**\n\n"
                    "நலம் தளம் உண்மைத் தரவுகளை மட்டுமே காட்டுகிறது; கற்பனையான தகவல்களை உருவாக்காது.\n"
                )
                if nearest_name:
                    lines.append(
                        f"நலம் நெட்வொர்க்கில் மிக அருகிலுள்ள சுகாதார மையம்: **{nearest_name}**.\n"
                    )
                    if sub_locality:
                        lines.append(
                            f"கோயம்புத்தூர் மாவட்டத்தில் உள்ள மருத்துவமனைகளைக் காட்டவா?\n"
                        )
                lines.append(
                    "அவசர சிகிச்சை தேவைப்பட்டால் உடனடியாக **108** ஆம்புலன்ஸை அழைக்கவும் அல்லது உள்ளூர் அரசு தலைமை மருத்துவமனையை அணுகவும்."
                )
            else:
                lines.append(
                    f"**Currently, no verified healthcare facilities matching your criteria were found for {display_loc} in the NALAM database.**\n\n"
                    "NALAM strictly adheres to zero-fabrication clinical safety and never estimates or invents healthcare facility data.\n"
                )
                if nearest_name:
                    lines.append(
                        f"The closest registered facility in the network is **{nearest_name}**.\n"
                    )
                    if sub_locality:
                        lines.append(
                            f"Would you like to see verified hospitals elsewhere in Coimbatore district?\n"
                        )
                lines.append(
                    "For immediate emergency assistance, call **108** or visit your local Government Medical College Hospital."
                )
        else:
            loc_label = sub_locality or loc or "Coimbatore"
            if ownership == "Government":
                hdr_en = f"**Verified Government Healthcare Facilities in {loc_label}:**\n"
                hdr_ta = f"**{loc_label} பகுதியில் உள்ள அரசு மருத்துவமனைகள் விவரங்கள்:**\n"
            elif service == "maternity":
                hdr_en = f"**Verified Maternity & Delivery Hospitals in {loc_label}:**\n"
                hdr_ta = f"**{loc_label} பகுதியில் உள்ள பிரசவ மற்றும் தாய் சேய் நல மருத்துவமனைகள்:**\n"
            elif service == "emergency":
                hdr_en = f"**Verified 24/7 Emergency & Casualty Hospitals in {loc_label}:**\n"
                hdr_ta = f"**{loc_label} பகுதியில் உள்ள 24/7 அவசர சிகிச்சை மருத்துவமனைகள்:**\n"
            elif fac_type == "CHC":
                hdr_en = f"**Community Health Centres (CHC) in {loc_label}:**\n"
                hdr_ta = f"**{loc_label} பகுதியில் உள்ள சமூக சுகாதார மையங்கள் (CHC):**\n"
            elif fac_type == "PHC":
                hdr_en = f"**Primary Health Centres (PHC) in {loc_label}:**\n"
                hdr_ta = f"**{loc_label} பகுதியில் உள்ள அரசு ஆரம்ப சுகாதார நிலையங்கள் (PHC):**\n"
            else:
                hdr_en = f"**Verified Healthcare Facilities in {loc_label}:**\n"
                hdr_ta = f"**{loc_label} பகுதியில் உள்ள மருத்துவமனைகள் விவரங்கள்:**\n"

            lines.append(hdr_ta if lang == "ta" else hdr_en)

            for f in matched_facilities:
                f_locality = f.get("locality") or f.get("block") or f.get("district") or "Coimbatore"
                dist_str = f"{f['distance_km']} km" if f["distance_km"] is not None else None
                doc_info = f["doctors"][0] if f["doctors"] else None
                doc_name = doc_info["name"] if doc_info else "Medical Officer on duty"
                doc_status = doc_info["attendance_status"] if doc_info else "UNKNOWN"

                method = f.get("appointment_booking_method", "WALK_IN_ONLY")
                phone = f.get("official_phone") or f.get("emergency_contact")
                online_url = f.get("online_booking_url")
                hours = f.get("opening_hours") or "OPD: 07:30 AM - 12:00 PM | Casualty: 24x7"

                # Badging
                if f.get("emergency_services"):
                    badge_label = "24x7 EMERGENCY"
                    badge_color = "red"
                elif f.get("maternity_services"):
                    badge_label = "MATERNITY CARE"
                    badge_color = "purple"
                elif doc_status == "PRESENT":
                    badge_label = "DOCTOR PRESENT"
                    badge_color = "green"
                else:
                    badge_label = f["facility_type"]
                    badge_color = "blue"

                # Action
                if method == "ONLINE_BOOKING_AVAILABLE" and online_url:
                    c_action = {
                        "label": "Official Booking Portal" if lang == "en" else "இணைய முன்பதிவு",
                        "type": "LINK",
                        "url": online_url,
                    }
                elif phone:
                    c_action = {
                        "label": f"Call {phone}",
                        "type": "CALL",
                        "target": phone,
                    }
                else:
                    c_action = {
                        "label": "Walk-in OPD Info" if lang == "en" else "நேரடி பதிவு விவரம்",
                        "type": "INFO",
                    }

                cards.append(AIChatCard(
                    type=CardType.FACILITY,
                    title=f["name"],
                    subtitle=f"{f.get('ownership', 'Hospital')} • {f.get('locality') or f.get('block') or f.get('district') or 'Coimbatore'}",
                    badge=badge_label,
                    badge_color=badge_color,
                    details={
                        "category": f.get("facility_category") or f["facility_type"],
                        "ownership": f.get("ownership"),
                        "distance_km": f["distance_km"],
                        "address": f["address"],
                        "phone": phone or "Not listed",
                        "opening_hours": hours,
                        "booking_method": method,
                        "emergency_services": "24x7 Available" if f.get("emergency_services") else "Standard hours",
                        "maternity_services": "Available" if f.get("maternity_services") else "General OPD",
                    },
                    action=c_action,
                ))

                if lang == "ta":
                    booking_desc = (
                        "நேரடி புறநோயாளி (OPD) பதிவு கவுண்டர்"
                        if method == "WALK_IN_ONLY"
                        else f"இணைய முன்பதிவு: {online_url}"
                    )
                    loc_part = f" — தூரம்: `{dist_str}`" if dist_str else f" — {f_locality}"
                    lines.append(
                        f"- **{f['name']}** ({f.get('ownership', 'மருத்துவமனை')}){loc_part}\n"
                        f"  - முகவரி: {f['address']}\n"
                        f"  - தொலைபேசி: {phone or 'நேரடி அணுகல்'}\n"
                        f"  - செயல்படும் நேரம்: {hours}\n"
                        f"  - முன்பதிவு முறை: {booking_desc}\n"
                    )
                else:
                    booking_desc = (
                        "Walk-in registration at hospital OPD counter (07:30 AM - 12:00 PM). 24x7 Casualty."
                        if method == "WALK_IN_ONLY"
                        else f"Online booking portal: {online_url}"
                    )
                    loc_part = f" — **{dist_str}**" if dist_str else f" — {f_locality}"
                    lines.append(
                        f"- **{f['name']}** ({f.get('ownership', 'Hospital')}){loc_part}\n"
                        f"  - Address: {f['address']}\n"
                        f"  - Phone: {phone or 'Not listed'}\n"
                        f"  - Hours: {hours}\n"
                        f"  - Booking: {booking_desc}\n"
                    )

            lines.append(
                "\n*Notice: NALAM displays verified district records and never generates synthetic hospital or doctor data.*"
                if lang == "en"
                else "\n*அறிவிப்பு: நலம் தளம் சரிபார்க்கப்பட்ட அதிகாரப்பூர்வ தகவல்களை மட்டுமே வழங்குகிறது; மாதிரி தகவல்களை உருவாக்காது.*"
            )

        resp_text = "\n".join(lines)
        session.add_turn(message, lang, "FACILITY_SEARCH", loc, tools_called, resp_text)
        return await self._build_response(
            conversation_id=conv_id,
            response_text=resp_text,
            language=lang,
            intent="FACILITY_PROXIMITY_SEARCH",
            tools_called=tools_called,
            cards=cards,
            action_taken="RETRIEVE_AND_DISPLAY_FACILITIES",
            request=request,
        )


# Global agent instance (aliased for backwards compatibility)
nalam_agent = NalamAIAgent()
carebridge_agent = nalam_agent
