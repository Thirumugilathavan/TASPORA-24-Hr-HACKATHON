from typing import Any, Dict, List, Optional
from app.schemas.shared import AttendanceStatus, AvailabilityLabel, RequestType


class IVRPromptService:
    """Bilingual voice prompts manager supporting Tamil and English for button-phone users."""

    @staticmethod
    def get_welcome_prompt() -> str:
        return (
            "CareBridge-க்கு வரவேற்கிறோம். உங்கள் சுகாதார சேவை உதவியாளர். "
            "Welcome to CareBridge healthcare assistant. "
            "தமிழில் தொடர 1-ஐ அழுத்தவும். For English, press 2."
        )

    @staticmethod
    def get_main_menu(lang: str = "ta") -> str:
        if lang == "ta":
            return (
                "முதன்மை மெனு: "
                "அருகிலுள்ள மருத்துவமனைகளை அறிய 1-ஐ அழுத்தவும். "
                "மருத்துவர் வருகை விவரம் அறிய 2-ஐ அழுத்தவும். "
                "மருந்து இருப்பு அறிய 3-ஐ அழுத்தவும். "
                "மருத்துவ உதவி கோரிக்கை பதிவு செய்ய 4-ஐ அழுத்தவும். "
                "உங்கள் கோரிக்கை மற்றும் முன்பதிவு நிலை அறிய 5-ஐ அழுத்தவும். "
                "மருத்துவர் முன்பதிவு செய்ய 6-ஐ அழுத்தவும். "
                "அவசர உதவி வழிகாட்டலுக்கு 7-ஐ அழுத்தவும். "
                "இந்த தேர்வுகளை மீண்டும் கேட்க 8-ஐ அழுத்தவும். "
                "அழைப்பை முடிக்க 9-ஐ அழுத்தவும்."
            )
        return (
            "Main Menu: "
            "Press 1 to find nearby healthcare facilities. "
            "Press 2 to check doctor availability. "
            "Press 3 to check medicine availability. "
            "Press 4 to create a healthcare request. "
            "Press 5 to check existing request or appointment status. "
            "Press 6 to book an appointment. "
            "Press 7 for emergency guidance. "
            "Press 8 to repeat this menu. "
            "Press 9 to end the call."
        )

    @staticmethod
    def get_pin_prompt(lang: str = "ta") -> str:
        if lang == "ta":
            return (
                "உங்கள் தனிப்பட்ட தகவல்களை பாதுகாக்க 4 இலக்க பின் எண்ணை உள்ளிட்டு # குறியை அழுத்தவும். "
                "(உதாரணம்: உங்கள் தொலைபேசி எண்ணின் கடைசி 4 இலக்கங்கள்). முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        return (
            "For your security, please enter your 4-digit PIN followed by hash. "
            "(Default: last 4 digits of your phone number). Press 0 to return to main menu."
        )

    @staticmethod
    def get_pin_invalid(remaining_attempts: int, lang: str = "ta") -> str:
        if lang == "ta":
            return f"தவறான பின் எண். மீண்டும் உள்ளிடவும். மீதமுள்ள முயற்சிகள்: {remaining_attempts}."
        return f"Invalid PIN. Please try again. Remaining attempts: {remaining_attempts}."

    @staticmethod
    def get_pin_locked(lang: str = "ta") -> str:
        if lang == "ta":
            return "தொடர்ந்து தவறாக உள்ளிட்டதால் உங்கள் கணக்கு 15 நிமிடங்களுக்கு தற்காலிகமாக முடக்கப்பட்டுள்ளது. நன்றி."
        return "Too many failed attempts. Your account is temporarily locked for 15 minutes. Goodbye."

    @staticmethod
    def get_emergency_message(lang: str = "ta") -> str:
        if lang == "ta":
            return (
                "அவசர மருத்துவ உதவிக்கு தயவுசெய்து உடனே 108 அவசர ஆம்புலன்ஸ் எண்ணை அழைக்கவும், "
                "அல்லது அருகிலுள்ள அரசு பொது மருத்துவமனைக்கு உடனடியாக செல்லவும். "
                "முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும். அழைப்பை முடிக்க 9-ஐ அழுத்தவும்."
            )
        return (
            "For medical emergencies, please immediately dial 108 ambulance service or visit your nearest hospital. "
            "CareBridge IVR cannot replace emergency dispatch. Press 0 for main menu, or press 9 to end call."
        )

    @staticmethod
    def get_facilities_prompt(facilities: List[Dict[str, Any]], lang: str = "ta") -> str:
        if not facilities:
            if lang == "ta":
                return "உங்கள் பகுதிக்கு அருகில் மருத்துவமனைகள் எதுவும் கிடைக்கவில்லை. முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            return "No healthcare facilities found near your village. Press 0 for main menu."

        parts = []
        if lang == "ta":
            parts.append("கண்டறியப்பட்ட அருகிலுள்ள மருத்துவமனைகள்: ")
            for idx, f in enumerate(facilities[:3], start=1):
                name = f.get("name", "மருத்துவமனை")
                ft = f.get("facility_type", "")
                ft_ta = "ஆரம்ப சுகாதார நிலையம்" if ft == "PHC" else "சமூக சுகாதார மையம்" if ft == "CHC" else "மருத்துவமனை"
                dist = f.get("distance_km")
                dist_str = f", சுமார் {dist} கிலோமீட்டர் நேர்கோட்டு தொலைவு" if dist is not None else ""
                parts.append(f"{idx}-வது: {name}, {ft_ta}{dist_str}. ")
            parts.append("கவனிக்க: கணக்கிடப்பட்ட தூரம் நேர்கோட்டு தூரமாகும். சாலை தூரம் மாறுபடலாம். விவரங்களை மீண்டும் கேட்க 8-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்.")
        else:
            parts.append("Nearby healthcare facilities: ")
            for idx, f in enumerate(facilities[:3], start=1):
                name = f.get("name", "Facility")
                ft = f.get("facility_type", "")
                dist = f.get("distance_km")
                dist_str = f", approx {dist} km straight-line distance" if dist is not None else ""
                parts.append(f"Option {idx}: {name} ({ft}){dist_str}. ")
            parts.append("Notice: Distance is straight-line approximation, road distance may be longer. Press 8 to repeat, 0 for main menu.")

        return "".join(parts)

    @staticmethod
    def get_doctor_status_prompt(doc_name: str, fac_name: str, status: AttendanceStatus, target_date_str: str, lang: str = "ta") -> str:
        status_val = status.value if hasattr(status, "value") else str(status)
        if lang == "ta":
            if status_val == "PRESENT":
                stat_desc = "பணியில் உள்ளார் (வருகை உறுதி செய்யப்பட்டுள்ளது)."
            elif status_val == "EXPECTED":
                stat_desc = "பணி அட்டவணையில் உள்ளார். ஆனால் வருகை இன்னும் உறுதி செய்யப்படவில்லை."
            elif status_val == "ABSENT":
                stat_desc = "இன்று விடுப்பில் உள்ளார்."
            else:
                stat_desc = "வருகை விவரம் இன்னும் பதிவு செய்யப்படவில்லை."

            return (
                f"{fac_name}-ல் {doc_name} {target_date_str} அன்று: {stat_desc} "
                "மீண்டும் கேட்க 8-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        else:
            if status_val == "PRESENT":
                stat_desc = "is verified PRESENT on duty."
            elif status_val == "EXPECTED":
                stat_desc = "is EXPECTED as scheduled. Attendance is planned, not confirmed present."
            elif status_val == "ABSENT":
                stat_desc = "is reported ABSENT."
            else:
                stat_desc = "attendance status is UNKNOWN."

            return (
                f"At {fac_name}, {doc_name} on {target_date_str} {stat_desc} "
                "Press 8 to repeat, 0 for main menu."
            )

    @staticmethod
    def get_medicine_select_prompt(medicines: List[Dict[str, Any]], lang: str = "ta") -> str:
        parts = []
        if lang == "ta":
            parts.append("இருப்பு விவரம் அறிய மருந்தை தேர்வு செய்யவும்: ")
            for idx, m in enumerate(medicines[:4], start=1):
                parts.append(f"{m.get('name')} அறிய {idx}-ஐ அழுத்தவும். ")
            parts.append("முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்.")
        else:
            parts.append("Select a medicine to check stock: ")
            for idx, m in enumerate(medicines[:4], start=1):
                parts.append(f"Press {idx} for {m.get('name')}. ")
            parts.append("Press 0 for main menu.")
        return "".join(parts)

    @staticmethod
    def get_medicine_stock_result(med_name: str, fac_name: str, label: AvailabilityLabel, p: float, conf: float, lang: str = "ta") -> str:
        label_val = label.value if hasattr(label, "value") else str(label)
        conf_pct = int(conf * 100)

        if lang == "ta":
            if label_val == "LIKELY":
                label_desc = f"{fac_name}-ல் {med_name} கிடைக்க அதிக வாய்ப்புள்ளது."
            elif label_val == "UNLIKELY":
                label_desc = f"{fac_name}-ல் {med_name} இருப்பு இல்லை அல்லது தீர்ந்துவிட்டது."
            else:
                label_desc = f"{fac_name}-ல் {med_name} இருப்பு நிலை உறுதியாக தெரியவில்லை."

            return (
                f"{label_desc} தகவல் நம்பகத்தன்மை: {conf_pct} சதவீதம். "
                "கவனிக்க: இது மருத்துவ பரிந்துரை அல்ல; இருப்பு விவரம் மட்டுமே. "
                "மீண்டும் கேட்க 8-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        else:
            if label_val == "LIKELY":
                label_desc = f"{med_name} is LIKELY in stock at {fac_name}."
            elif label_val == "UNLIKELY":
                label_desc = f"{med_name} is UNLIKELY in stock at {fac_name}."
            else:
                label_desc = f"{med_name} stock status is UNCERTAIN at {fac_name}."

            return (
                f"{label_desc} Evidence confidence: {conf_pct} percent. "
                "Notice: This is catalogue availability estimation, not dosage or prescription advice. "
                "Press 8 to repeat, 0 for main menu."
            )

    @staticmethod
    def get_request_type_menu(lang: str = "ta") -> str:
        if lang == "ta":
            return (
                "மருத்துவ உதவி கோரிக்கை வகை: "
                "மருத்துவ ஆலோசனைக்கு 1-ஐ அழுத்தவும். "
                "மருந்து மறு நிரப்பலுக்கு 2-ஐ அழுத்தவும். "
                "பொது சுகாதார பரிசோதனைக்கு 3-ஐ அழுத்தவும். "
                "பரிசோதனை ஆய்வக சேவைக்கு 4-ஐ அழுத்தவும். "
                "ஆஷா பணியாளர் உதவிக்கு 5-ஐ அழுத்தவும். "
                "முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        return (
            "Select Request Type: "
            "Press 1 for Consultation. "
            "Press 2 for Medicine Refill. "
            "Press 3 for General Checkup. "
            "Press 4 for Diagnostics. "
            "Press 5 for ASHA worker callback assistance. "
            "Press 0 for main menu."
        )

    @staticmethod
    def get_request_urgency_menu(req_type_name: str, lang: str = "ta") -> str:
        if lang == "ta":
            return (
                f"{req_type_name} கோரிக்கைக்கு: "
                "சாதாரண முன்னுரிமைக்கு 1-ஐ அழுத்தவும். "
                "அவசர முன்னுரிமைக்கு 2-ஐ அழுத்தவும். "
                "முந்தைய மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        return (
            f"For {req_type_name}: "
            "Press 1 for Normal urgency. "
            "Press 2 for Priority urgency. "
            "Press 0 to go back."
        )

    @staticmethod
    def get_request_created(req_ref: str, lang: str = "ta") -> str:
        if lang == "ta":
            return (
                f"உங்கள் மருத்துவ கோரிக்கை வெற்றிகரமாக பதிவு செய்யப்பட்டது. கோரிக்கை குறிப்பு எண்: {req_ref[-6:]}. "
                "பரிந்துரைக்கப்பட்ட மருத்துவமனைகளை கேட்க 1-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        return (
            f"Healthcare request registered successfully. Reference ID: {req_ref[-6:]}. "
            "Press 1 to hear recommended facilities. Press 0 for main menu."
        )

    @staticmethod
    def get_recommendation_readout(items: List[Dict[str, Any]], lang: str = "ta") -> str:
        if not items:
            if lang == "ta":
                return "தற்போது பரிந்துரைகள் எதுவும் கிடைக்கவில்லை. முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            return "No facility recommendations found for this request. Press 0 for main menu."

        top = items[0]
        name = top.get("facility_name", "மருத்துவமனை")
        loss = top.get("expected_loss", 0)
        dist = top.get("travel_distance_km", 0)
        doc_stat = top.get("doctor_status", "UNKNOWN")

        if lang == "ta":
            doc_str = "மருத்துவர் பணியில் உள்ளார்" if doc_stat == "PRESENT" else "மருத்துவர் பணி அட்டவணை திட்டமிடப்பட்டுள்ளது"
            return (
                f"சிறந்த பரிந்துரை: {name}. {doc_str}. "
                f"பயண தூரம் சுமார் {dist} கி.மீ நேர்கோடு. பயண இழப்பு மதிப்பீடு ரூ {loss}. "
                "இந்த மருத்துவமனையில் முன்பதிவு செய்ய 1-ஐ அழுத்தவும். "
                "மீண்டும் கேட்க 8-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        else:
            doc_str = "Doctor is verified PRESENT" if doc_stat == "PRESENT" else "Doctor is EXPECTED as scheduled"
            return (
                f"Top recommended facility: {name}. {doc_str}. "
                f"Approx distance {dist} km straight-line. Expected journey loss calculated at Rs {loss}. "
                "Press 1 to book an appointment here. "
                "Press 8 to repeat, 0 for main menu."
            )

    @staticmethod
    def get_slot_selection_menu(fac_name: str, lang: str = "ta") -> str:
        if lang == "ta":
            return (
                f"{fac_name}-ல் முன்பதிவு செய்ய நேரத்தை தேர்வு செய்யவும்: "
                "காலை 10 மணிக்கு 1-ஐ அழுத்தவும். "
                "பிற்பகல் 12 மணிக்கு 2-ஐ அழுத்தவும். "
                "மதியம் 2 மணிக்கு 3-ஐ அழுத்தவும். "
                "முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        return (
            f"Select appointment slot at {fac_name}: "
            "Press 1 for 10:00 AM. "
            "Press 2 for 12:00 PM. "
            "Press 3 for 02:00 PM. "
            "Press 0 for main menu."
        )

    @staticmethod
    def get_appointment_booked(appt_id: str, fac_name: str, time_str: str, date_str: str, lang: str = "ta") -> str:
        if lang == "ta":
            return (
                f"உங்கள் முன்பதிவு உறுதி செய்யப்பட்டது! மருத்துவமனை: {fac_name}, தேதி: {date_str}, நேரம்: {time_str}. "
                f"முன்பதிவு எண்: {str(appt_id)[-6:]}. முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும். அழைப்பை முடிக்க 9-ஐ அழுத்தவும்."
            )
        return (
            f"Your appointment is confirmed! Facility: {fac_name}, Date: {date_str}, Time: {time_str}. "
            f"Appointment Reference: {str(appt_id)[-6:]}. Press 0 for main menu, 9 to end call."
        )

    @staticmethod
    def get_slot_conflict_message(lang: str = "ta") -> str:
        if lang == "ta":
            return (
                "மன்னிக்கவும்! நீங்கள் தேர்ந்தெடுத்த நேரம் மற்றொருவரால் முன்பதிவு செய்யப்பட்டுவிட்டது. "
                "வேறு நேரத்தை தேர்வு செய்ய 1-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        return (
            "Sorry, this slot was just booked by another patient. "
            "Press 1 to select an alternate slot. Press 0 for main menu."
        )

    @staticmethod
    def get_status_overview(req_count: int, appt_count: int, latest_appt: Optional[Dict[str, Any]] = None, lang: str = "ta") -> str:
        if lang == "ta":
            parts = [f"உங்களிடம் {req_count} மருத்துவ கோரிக்கைகளும், {appt_count} மருத்துவ முன்பதிவுகளும் உள்ளன. "]
            if latest_appt:
                fac = latest_appt.get("facility_name", "மருத்துவமனை")
                dt = latest_appt.get("date", "")
                tm = latest_appt.get("time", "")
                parts.append(f"சமீபத்திய முன்பதிவு: {fac}, {dt} {tm}. இந்த முன்பதிவை ரத்து செய்ய 1-ஐ அழுத்தவும். ")
            parts.append("முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்.")
            return "".join(parts)
        else:
            parts = [f"You have {req_count} active requests and {appt_count} appointments. "]
            if latest_appt:
                fac = latest_appt.get("facility_name", "Facility")
                dt = latest_appt.get("date", "")
                tm = latest_appt.get("time", "")
                parts.append(f"Upcoming appointment: {fac} on {dt} at {tm}. Press 1 to cancel this appointment. ")
            parts.append("Press 0 for main menu.")
            return "".join(parts)

    @staticmethod
    def get_cancel_confirm_prompt(lang: str = "ta") -> str:
        if lang == "ta":
            return "உங்கள் மருத்துவ முன்பதிவை ரத்து செய்ய உறுதிப்படுத்த 1-ஐ அழுத்தவும். ரத்து செய்யாமல் தொடர 2-ஐ அழுத்தவும்."
        return "Press 1 to confirm cancelling this appointment. Press 2 to keep your appointment."

    @staticmethod
    def get_cancel_success(lang: str = "ta") -> str:
        if lang == "ta":
            return "உங்கள் முன்பதிவு வெற்றிகரமாக ரத்து செய்யப்பட்டது. முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும். அழைப்பை முடிக்க 9-ஐ அழுத்தவும்."
        return "Your appointment has been cancelled successfully. Press 0 for main menu, 9 to end call."

    @staticmethod
    def get_goodbye(lang: str = "ta") -> str:
        if lang == "ta":
            return "CareBridge-ஐ தொடர்பு கொண்டதற்கு நன்றி. நலமுடன் வாழ்க. வணக்கம்."
        return "Thank you for calling CareBridge. Stay healthy. Goodbye."

    @staticmethod
    def get_invalid_input(lang: str = "ta") -> str:
        if lang == "ta":
            return "தவறான தேர்வு. மீண்டும் முயற்சிக்கவும்."
        return "Invalid selection. Please try again."

    @staticmethod
    def get_timeout_message(lang: str = "ta") -> str:
        if lang == "ta":
            return "எந்த பொத்தானும் அழுத்தப்படவில்லை. மீண்டும் ஒருமுறை சொல்லப்படுகின்றது."
        return "No keypress detected. Repeating option."

    @staticmethod
    def get_asha_callback_prompt(lang: str = "ta") -> str:
        if lang == "ta":
            return (
                "ஆஷா சுகாதார பணியாளர் உங்களை மீண்டும் தொடர்பு கொள்ள கோரிக்கை வெற்றிகரமாக பதிவு செய்யப்பட்டது. "
                "உங்கள் கிராம ஆஷா பணியாளர் உங்களை விரைவில் தொடர்புகொள்வார். "
                "கவனிக்க: ஆஷா பணியாளர் தங்கள் ஒதுக்கப்பட்ட கிராம எல்லைக்குள் மட்டுமே சேவை புரிவர். "
                "முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        return (
            "Your request for an ASHA community health worker callback has been registered successfully. "
            "Your assigned village ASHA worker will contact you. "
            "Note: ASHA workers provide assistance within their designated village scope. "
            "Press 0 for main menu."
        )

    @staticmethod
    def get_call_transfer_prompt(lang: str = "ta") -> str:
        if lang == "ta":
            return "உங்கள் அழைப்பு சுகாதார மைய பிரதிநிதிக்கு இணைக்கப்படுகிறது. தயவுசெய்து காத்திருக்கவும்."
        return "Connecting your call to a healthcare support representative. Please hold."

    @staticmethod
    def get_call_transfer_unavailable(lang: str = "ta") -> str:
        if lang == "ta":
            return (
                "மன்னிக்கவும்! சுகாதார உதவி மேசை தற்போது பயன்பாட்டில் இல்லை அல்லது பணி நேரத்திற்கு வெளியில் உள்ளது. "
                "ஆஷா பணியாளர் உதவி பெற 4-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
            )
        return (
            "Live healthcare support is currently unavailable or outside duty hours. "
            "Please request ASHA assistance under option 4, or press 0 for main menu."
        )

    @staticmethod
    def get_outbound_greeting(purpose: str = "ASHA_CALLBACK", lang: str = "ta") -> str:
        if lang == "ta":
            return (
                "வணக்கம்! இது CareBridge சுகாதார மையத்திலிருந்து வரும் அழைப்பு. "
                "உங்கள் சுகாதார உதவி கோரிக்கை தொடர்பாக அழைக்கின்றோம். "
                "தமிழில் தொடர 1-ஐ அழுத்தவும். For English, press 2."
            )
        return (
            "Hello! This is CareBridge rural healthcare service following up on your healthcare request. "
            "For Tamil, press 1. For English, press 2."
        )

