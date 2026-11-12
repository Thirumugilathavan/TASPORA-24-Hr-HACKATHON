"""CareBridge Closed-Loop AI Agent Engine.

Core Philosophy: UNDERSTAND -> EXECUTE -> RETRIEVE -> VERIFY -> EXPLAIN -> DISPLAY.
Strict Rule: NEVER merely announce an intention to search. Always execute backend tools
and return factual records in the same response.
"""
from datetime import date
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag import rag_engine
from app.ai.schemas import (
    AIChatCard,
    AIChatRequest,
    AIChatResponse,
    CardType,
)
from app.ai.system_prompt import CAREBRIDGE_SYSTEM_PROMPT, TAMIL_TRANSLATIONS
from app.ai.tools import (
    check_doctor_availability_tool,
    check_medicine_stock_tool,
    emergency_guidance_tool,
    get_recommendations_tool,
    query_rag_knowledge_tool,
    search_facilities_tool,
)


class CareBridgeAgent:
    """Intelligent CareBridge Assistant supporting real tool calling and RAG."""

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
        # Check for Tamil Unicode range (U+0B80 to U+0BFF)
        if re.search(r"[\u0B80-\u0BFF]", text):
            return "ta"
        return "en"

    def extract_location(self, text: str, fallback_location: Optional[str] = None) -> Optional[str]:
        """Extracts location or village name from query."""
        lowered = text.lower()
        candidates = [
            "tiruchengode", "molasi", "namakkal", "rampur", "mohanpur",
            "anandpur", "vellore", "salem", "sitapur",
            "திருச்செங்கோடு", "மோளசி", "நாமக்கல்", "ராம்பூர்",
        ]
        for c in candidates:
            if c in lowered:
                # Map Tamil name to English equivalent for DB lookups
                if "திருச்செங்கோடு" in c:
                    return "Tiruchengode"
                if "மோளசி" in c:
                    return "Molasi"
                if "நாமக்கல்" in c:
                    return "Namakkal"
                if "ராம்பூர்" in c:
                    return "Rampur"
                return c.capitalize()

        # Regex for "near <Location>" or "in <Location>"
        match = re.search(r"\b(?:near|in|at|around|அருகே|உள்ள)\s+([a-zA-Z]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).capitalize()

        return fallback_location or "Tiruchengode"

    def extract_medicine(self, text: str) -> Optional[str]:
        """Extracts medicine name from query."""
        lowered = text.lower()
        medicines = [
            "paracetamol", "amoxicillin", "metformin", "ors sachet", "ors",
            "cetirizine", "amlodipine", "பாராசிட்டமால்", "அமாக்சிசிலின்", "மெட்பார்மின்",
        ]
        for m in medicines:
            if m in lowered:
                if "பாராசிட்டமால்" in m:
                    return "Paracetamol"
                if "அமாக்சிசிலின்" in m:
                    return "Amoxicillin"
                if "மெட்பார்மின்" in m:
                    return "Metformin"
                if m == "ors":
                    return "ORS Sachet"
                return m.capitalize()
        return None

    async def execute_turn(
        self,
        request: AIChatRequest,
        db: AsyncSession,
    ) -> AIChatResponse:
        """Executes a single conversational turn with closed-loop tool execution."""
        message = request.message.strip()
        conv_id = request.conversation_id or str(uuid.uuid4())
        lang = self.detect_language(message, request.language)
        lowered = message.lower()

        tools_called = []
        cards: List[AIChatCard] = []
        rag_sources: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # 1. EMERGENCY TRIAGE (HIGHEST PRIORITY)
        # -------------------------------------------------------------
        emergency_keywords = [
            "chest pain", "மாரடைப்பு", "heart attack", "difficulty breathing",
            "மூச்சுத்திணறல்", "emergency", "அவசரம்", "accident", "விபத்து",
            "heavy bleeding", "unconscious", "stroke", "snake bite", "108",
        ]
        if any(ek in lowered for ek in emergency_keywords):
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
        # 2. NON-DIAGNOSTIC SAFETY GUARD (PRESCRIPTION / DOSAGE ATTEMPTS)
        # -------------------------------------------------------------
        dosage_keywords = [
            "what dose", "how much paracetamol", "prescribe", "dosage", "how many tablets",
            "what medicine should i take", "என்ன மருந்து சாப்பிட வேண்டும்", "மருந்தளவு",
        ]
        if any(dk in lowered for dk in dosage_keywords):
            # Still retrieve nearest PHC so patient can visit doctor
            loc = self.extract_location(message, request.location_context)
            tools_called.append("search_facilities_tool")
            fac_res = await search_facilities_tool(db, location_name=loc, limit=2)

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
                "கேர்பிரிட்ஜ் (CareBridge) ஒரு மருத்துவ நோயறிதல் அல்லது மருந்து பரிந்துரை தளம் அல்ல. "
                "மருந்துகளின் அளவு மற்றும் சிகிச்சையை பதிவுபெற்ற அரசு மருத்துவர் மட்டுமே தீர்மானிக்க முடியும்.\n\n"
                f"உங்கள் உடல்நிலையை பரிசோதிக்க, **{loc}** பகுதியில் உள்ள அரசு ஆரம்ப சுகாதார நிலையத்திற்கு செல்லுமாறு பரிந்துரைக்கிறோம். "
                "அங்கு மருத்துவர் பணியில் உள்ளார்."
                if lang == "ta"
                else "**Clinical Safety Disclaimer:**\n"
                "CareBridge strictly does not provide medical diagnoses, prescriptions, or drug dosage recommendations. "
                "Only a licensed physician can determine the correct medicine dosage for your condition.\n\n"
                f"Please consult a doctor at your nearest Primary Health Centre in **{loc}**. "
                "See available facilities and doctor schedules below:"
            )

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
        # 3. DOCTOR AVAILABILITY INTENT
        # -------------------------------------------------------------
        doc_keywords = [
            "doctor", "physician", "duty", "dr.", "attendance", "on duty",
            "மருத்துவர்", "டாக்டர்", "பணியில்", "இருக்கிறாரா",
        ]
        if any(dk in lowered for dk in doc_keywords) and not any(k in lowered for k in ["how does", "formula", "rag", "algorithm"]):
            loc = self.extract_location(message, request.location_context)
            tools_called.append("check_doctor_availability_tool")
            doc_data = await check_doctor_availability_tool(db, location_name=loc)

            # Format response and cards
            doctor_items = doc_data.get("doctors", [])
            lines = []

            if lang == "ta":
                lines.append(f"**{loc} மற்றும் அருகிலுள்ள அரசு மருத்துவமனைகளின் மருத்துவர் பணி விவரங்கள் ({date.today().isoformat()}):**\n")
            else:
                lines.append(f"**Verified Doctor Duty & Attendance Status for {loc} (Date: {date.today().isoformat()}):**\n")

            for d in doctor_items[:4]:
                status = d["attendance_status"]
                badge_color = "green" if status == "PRESENT" else ("yellow" if status == "EXPECTED" else "red")
                status_label = (
                    "பணியில் உள்ளார் (உறுதிசெய்யப்பட்டது)" if status == "PRESENT"
                    else ("திட்டமிடப்பட்ட பணி (வருகை நிலுவையில்)" if status == "EXPECTED" else "விடுப்பில் உள்ளார்")
                ) if lang == "ta" else status

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
                        f"  - Attendance: `{status}` ({'Physically verified on duty' if status == 'PRESENT' else 'Rostered shift; check-in pending'})\n"
                        f"  - Shift Hours: {d.get('shift_hours', 'N/A')}\n"
                    )

            lines.append("\n*CareBridge distinguishes physically verified check-ins (PRESENT) from planned shifts (EXPECTED) to eliminate wasted trips.*")

            return await self._build_response(
                conversation_id=conv_id,
                response_text="\n".join(lines),
                language=lang,
                intent="DOCTOR_AVAILABILITY_LOOKUP",
                tools_called=tools_called,
                cards=cards,
                action_taken="FETCH_DOCTOR_SCHEDULES",
                request=request,
            )

        # -------------------------------------------------------------
        # 4. MEDICINE STOCK INTELLIGENCE INTENT
        # -------------------------------------------------------------
        med_keywords = [
            "medicine", "tablet", "capsule", "stock", "paracetamol", "amoxicillin",
            "metformin", "ors", "cetirizine", "மருந்து", "மாத்திரை", "இருப்பு",
        ]
        if any(mk in lowered for mk in med_keywords) and not any(k in lowered for k in ["how does", "formula", "algorithm"]):
            med_name = self.extract_medicine(message) or "Paracetamol"
            loc = self.extract_location(message, request.location_context)

            tools_called.append("check_medicine_stock_tool")
            stock_data = await check_medicine_stock_tool(db, medicine_name=med_name, location_name=loc)

            lines = []
            if lang == "ta":
                lines.append(f"**{med_name} மருந்து இருப்பு விவரங்கள் ({loc} பகுதி):**\n")
            else:
                lines.append(f"**Probabilistic Availability for {med_name} near {loc}:**\n")

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

            return await self._build_response(
                conversation_id=conv_id,
                response_text="\n".join(lines),
                language=lang,
                intent="MEDICINE_STOCK_LOOKUP",
                tools_called=tools_called,
                cards=cards,
                action_taken="FETCH_MEDICINE_BELIEFS",
                request=request,
            )

        # -------------------------------------------------------------
        # 5. HEALTHCARE RECOMMENDATION / EXPECTED LOSS INTENT
        # -------------------------------------------------------------
        rec_keywords = [
            "recommend", "best facility", "where should i go", "trip loss",
            "வழிகாட்டல்", "எங்கு செல்லலாம்", "பரிந்துரை",
        ]
        if any(rk in lowered for rk in rec_keywords) and not any(k in lowered for k in ["how does", "algorithm", "formula"]):
            loc = self.extract_location(message, request.location_context)
            med = self.extract_medicine(message)
            req_type = "REFILL" if med else "CONSULTATION"

            tools_called.append("get_recommendations_tool")
            rec_data = await get_recommendations_tool(db, village_name=loc, request_type=req_type, medicine_name=med)

            lines = []
            if lang == "ta":
                lines.append(f"**{loc} பகுதிக்கான கேர்பிரிட்ஜ் குறைந்த இழப்பு பரிந்துரைகள்:**\n")
            else:
                lines.append(f"**CareBridge Loss-Minimizing Recommendations for {loc} (Request: {req_type}):**\n")

            for idx, r in enumerate(rec_data.get("recommendations", []), 1):
                cards.append(AIChatCard(
                    type=CardType.RECOMMENDATION,
                    title=f"#{idx} {r['facility_name']}",
                    subtitle=f"{r['facility_type']} • {r['distance_km']} km",
                    badge=f"Expected Loss: {r['expected_loss']}",
                    badge_color="green" if idx == 1 else "blue",
                    details={
                        "expected_loss": r["expected_loss"],
                        "doctor_status": r["doctor_status"],
                        "medicine_status": r["medicine_status"],
                        "travel_cost": r["travel_cost"],
                        "failure_risk_pct": int(r["failure_probability"] * 100),
                    },
                    action={"label": "Book Confirmed Slot", "type": "BOOK", "facility_id": r["facility_id"]},
                ))

                if lang == "ta":
                    lines.append(
                        f"**{idx}. {r['facility_name']}** ({r['facility_type']})\n"
                        f"  - தூரம்: {r['distance_km']} km | மருத்துவர்: `{r['doctor_status']}`\n"
                        f"  - வீண் பயண இழப்பு குறியீடு (Expected Loss): `{r['expected_loss']}` (தோல்வி அபாயம்: {int(r['failure_probability']*100)}%)\n"
                    )
                else:
                    lines.append(
                        f"**{idx}. {r['facility_name']}** ({r['facility_type']}) – **Rank {idx}**\n"
                        f"  - Distance: {r['distance_km']} km | Doctor: `{r['doctor_status']}`\n"
                        f"  - Expected Trip Loss: `{r['expected_loss']}` units (Failure Risk: {int(r['failure_probability']*100)}%)\n"
                        f"  - Why recommended: Minimizes the product of travel cost and failure risk.\n"
                    )

            return await self._build_response(
                conversation_id=conv_id,
                response_text="\n".join(lines),
                language=lang,
                intent="RECOMMENDATION_CALCULATION",
                tools_called=tools_called,
                cards=cards,
                action_taken="CALCULATE_EXPECTED_LOSS",
                request=request,
            )

        # -------------------------------------------------------------
        # 6. PROJECT RAG / ARCHITECTURE / ALGORITHM INTENT
        # -------------------------------------------------------------
        rag_keywords = [
            "how does carebridge", "algorithm", "stock algorithm", "expected loss formula",
            "loss formula", "loss calculation", "ivr pin", "lockout", "architecture",
            "pin lockout", "source weights", "half-life", "decay", "பரிந்துரை சூத்திரம்",
        ]
        if any(rk in lowered for rk in rag_keywords):
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

            # Provide authoritative synthesized explanation
            if "loss" in lowered or "recommend" in lowered or "calculate" in lowered:
                explanation = (
                    "### CareBridge Healthcare Recommendation & Expected Trip Loss Algorithm\n\n"
                    "Unlike traditional healthcare locators that sort solely by raw distance, **CareBridge routes patients by minimizing the risk of a wasted journey**.\n\n"
                    "#### The Mathematical Loss Formula:\n"
                    "$$\\text{Expected Loss} = \\text{RoundHalfUp}(\\text{Failure Probability} \\times \\text{Travel Cost})$$\n\n"
                    "Where:\n"
                    "1. **Travel Cost ($C$)**: Straight-line distance between the patient's village and facility multiplied by transportation tier cost: $\\text{Cost} = \\text{Base} + (\\text{Cost/km} \\times \\text{km})$.\n"
                    "2. **Failure Probability ($P_{\\text{fail}}$)**:\n"
                    "   - For **Consultations**: $P_{\\text{fail}}$ increases heavily if the doctor is not physically present (`PRESENT` $\\implies 0.05$, `EXPECTED` $\\implies 0.35$, `ABSENT` $\\implies 0.80$).\n"
                    "   - For **Medicine Refills**: $P_{\\text{fail}} = 1.0 - P_{\\text{available}}$. If Metformin stock is `UNLIKELY` ($P=0.20$), visit failure is $80\\%$.\n\n"
                    "**Why this matters in rural healthcare:**\n"
                    "A clinic 2 km away with no doctor or empty medicine shelf yields a **wasted trip**. "
                    "CareBridge often recommends a Community Health Centre 5 km away because verified doctor presence and stocked pharmacy guarantee continuous care!\n\n"
                    "*Source Citation: `STOCK_ALGORITHM.md` & `README.md`*"
                )
            elif "pin" in lowered or "ivr" in lowered or "lockout" in lowered:
                explanation = (
                    "### CareBridge IVR Voice Access & Security Policy\n\n"
                    "CareBridge provides button-phone voice access via standard keypad telephony (DTMF) in Tamil (`1`) and English (`2`).\n\n"
                    "#### PIN Authentication & Brute-Force Lockout Policy:\n"
                    "- Callers authenticate with their registered Phone Number and 4-digit PIN (default demo PIN: last 4 digits of phone).\n"
                    "- **Maximum Attempts:** `3` consecutive failed PIN attempts.\n"
                    "- **Lockout Duration:** `15 minutes` lockout period (`IVR_AUTH_LOCKOUT_MINUTES=15`).\n"
                    "- **Emergency Exemption:** Pressing `7` or stating an emergency immediately bridges to 108 emergency ambulance protocols without requiring PIN authentication.\n\n"
                    "*Source Citation: `IVR_CALL_FLOWS.md`, `IVR_ARCHITECTURE.md`, and `FINAL_SECURITY_AUDIT.md`*"
                )
            else:
                top_content = rag_sources[0]["content"] if rag_sources else "CareBridge Architecture Documentation"
                explanation = (
                    f"### CareBridge Technical Documentation Excerpt\n\n"
                    f"{top_content}\n\n"
                    f"*Sources: {', '.join(s['document'] for s in rag_sources)}*"
                )

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
        # 7. FACILITY DISCOVERY INTENT (DEFAULT WORKFLOW)
        # E.g.: "Find a PHC near Tiruchengode"
        # -------------------------------------------------------------
        loc = self.extract_location(message, request.location_context)
        fac_type = "PHC" if "phc" in lowered or "ஆரம்ப சுகாதார நிலையம்" in lowered else (
            "CHC" if "chc" in lowered else None
        )

        tools_called.append("search_facilities_tool")
        fac_data = await search_facilities_tool(
            db,
            location_name=loc,
            facility_type=fac_type,
            limit=4,
        )

        matched_facilities = fac_data.get("facilities", [])
        lines = []

        if lang == "ta":
            lines.append(f"**{loc} பகுதிக்கு அருகிலுள்ள அரசு ஆரம்ப சுகாதார நிலையங்கள் (PHC) விவரங்கள்:**\n")
        else:
            lines.append(f"**Primary Healthcare Facilities near {loc} (ranked by geographic proximity):**\n")

        for f in matched_facilities:
            dist_str = f"{f['distance_km']} km" if f["distance_km"] is not None else "Nearby"
            doc_info = f["doctors"][0] if f["doctors"] else None
            doc_name = doc_info["name"] if doc_info else "Medical Officer on duty"
            doc_status = doc_info["attendance_status"] if doc_info else "UNKNOWN"

            badge_color = "green" if doc_status == "PRESENT" else ("yellow" if doc_status == "EXPECTED" else "blue")

            cards.append(AIChatCard(
                type=CardType.FACILITY,
                title=f["name"],
                subtitle=f"{f['facility_type']} • {dist_str} away",
                badge=f"Doctor: {doc_status}",
                badge_color=badge_color,
                details={
                    "distance_km": f["distance_km"],
                    "address": f["address"],
                    "services": f["services"],
                    "doctor_name": doc_name,
                    "doctor_status": doc_status,
                    "doctor_hours": doc_info.get("hours") if doc_info else "09:00 - 16:00",
                    "contact_phone": f.get("contact_details", {}).get("phone", "04288-252100"),
                },
                action={
                    "label": "Book Appointment Slot" if lang == "en" else "நேரடி முன்பதிவு",
                    "type": "BOOK",
                    "facility_id": f["facility_id"],
                },
            ))

            if lang == "ta":
                status_ta = "பணியில் உள்ளார் (உறுதிசெய்யப்பட்டது)" if doc_status == "PRESENT" else "பணி நேரம் நிலுவையில்"
                services_str = ", ".join(f["services"][:3])
                lines.append(
                    f"- **{f['name']}** ({f['facility_type']}) – தூரம்: `{dist_str}`\n"
                    f"  - முகவரி: {f['address']}\n"
                    f"  - மருத்துவர்: **{doc_name}** (`{doc_status}` - {status_ta})\n"
                    f"  - சேவைகள்: {services_str}\n"
                )
            else:
                services_str = ", ".join(f["services"][:4])
                lines.append(
                    f"- **{f['name']}** ({f['facility_type']}) — **{dist_str}**\n"
                    f"  - Address: {f['address']}\n"
                    f"  - Doctor on duty: **{doc_name}** (Status: `{doc_status}` — {'Physically verified present' if doc_status == 'PRESENT' else 'Scheduled shift'})\n"
                    f"  - Core Services: {services_str}\n"
                )

        lines.append(
            "\n*You can book a confirmed consultation slot directly using the action button on any facility card above.*"
            if lang == "en"
            else "\n*மேலே உள்ள வசதி அட்டை மூலம் நேரடியாக முன்பதிவு செய்யலாம்.*"
        )

        return await self._build_response(
            conversation_id=conv_id,
            response_text="\n".join(lines),
            language=lang,
            intent="FACILITY_PROXIMITY_SEARCH",
            tools_called=tools_called,
            cards=cards,
            action_taken="RETRIEVE_AND_DISPLAY_FACILITIES",
            request=request,
        )


# Global agent instance
carebridge_agent = CareBridgeAgent()
