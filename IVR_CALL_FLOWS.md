# CareBridge Voice Access (IVR) — Detailed Call Flows

This document details the complete step-by-step caller interaction flows, DTMF keypad mappings, and bilingual audio transcripts in **Tamil (`ta`)** and **English (`en`)**.

---

## 1. Flow Overview & Keypad Hierarchy

```
[Inbound Call]
       |
  [0. Language Selection]
   ├── 1: Tamil (தமிழ்)
   └── 2: English
       |
  [1. Main Menu]
   ├── 1: Nearby Healthcare Facilities (Public)
   ├── 2: Doctor Availability Today (Public)
   ├── 3: Medicine Stock Availability (Public)
   ├── 4: Create Healthcare Request (Protected - Requires PIN)
   ├── 5: Check Request & Appointment Status / Cancellation (Protected - Requires PIN)
   ├── 6: Book an Appointment (Protected - Requires PIN)
   ├── 7: Emergency 108 Guidance (Immediate Public Guidance)
   ├── 8: Repeat Current Menu Prompt
   └── 9: End Call Gracefully
```

---

## 2. Universal Navigation Keys

The following keys behave consistently across all menus:
- **`9`**: End call immediately. Plays a courteous goodbye and disconnects.
- **`0` or `*`**: Return to the Main Menu from any submenu.
- **`8`**: Repeat the current menu's audio options.
- **`#`**: Finish DTMF input (e.g. following PIN entry).

---

## 3. Bilingual Audio Transcripts

### Step 0: Welcome & Language Selection

| Key | Event | Tamil Prompt | English Prompt |
|---|---|---|---|
| Inbound | Welcome | "CareBridge-க்கு நல்வரவு. தமிழில் தொடர 1-ஐ அழுத்தவும். For English, press 2." | "Welcome to CareBridge. For Tamil, press 1. For English, press 2." |
| `1` | Select Tamil | Language set to `ta` $\to$ Proceed to Main Menu | - |
| `2` | Select English | - | Language set to `en` $\to$ Proceed to Main Menu |

---

### Step 1: Main Menu

#### Tamil Prompt:
> "முதன்மை மெனு: அருகிலுள்ள மருத்துவமனைகளை அறிய 1-ஐ அழுத்தவும். மருத்துவர் வருகை விவரம் அறிய 2-ஐ அழுத்தவும். மருந்து இருப்பு நிலையை அறிய 3-ஐ அழுத்தவும். புதிய மருத்துவ உதவி கோரிக்கை உருவாக்க 4-ஐ அழுத்தவும். உங்கள் முந்தைய கோரிக்கை மற்றும் முன்பதிவு நிலை அறிய 5-ஐ அழுத்தவும். மருத்துவ முன்பதிவு செய்ய 6-ஐ அழுத்தவும். அவசர உதவி வழிகாட்டலுக்கு 7-ஐ அழுத்தவும். இந்த தேர்வுகளை மீண்டும் கேட்க 8-ஐ அழுத்தவும். அழைப்பை முடிக்க 9-ஐ அழுத்தவும்."

#### English Prompt:
> "Main Menu: Press 1 to find nearby healthcare facilities. Press 2 to check doctor availability. Press 3 to check medicine stock. Press 4 to create a healthcare request. Press 5 to check existing request or appointment status. Press 6 to book an appointment. Press 7 for emergency guidance. Press 8 to repeat this menu. Press 9 to end the call."

---

### Flow 1: Nearby Facilities Discovery (Key `1`)

- **Access:** Public (No authentication required).
- **Behavior:** Queries the database for candidate facilities near the caller's registered village (or general facilities if village is not registered). Computes Euclidean straight-line distance ($km$).

#### Spoken Format:
- **Tamil:**  
  *"உங்களுக்கு அருகிலுள்ள மருத்துவமனைகள்: 1: PHC Rampur, ஆரம்ப சுகாதார நிலையம், சுமார் 10 கி.மீ தூரம். 2: CHC Sitapur, சமூக சுகாதார மையம், சுமார் 18 கி.மீ தூரம். மீண்டும் கேட்க 8-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."*
- **English:**  
  *"Healthcare facilities near you: 1: PHC Rampur, Primary Health Centre, approximately 10 km. 2: CHC Sitapur, Community Health Centre, approximately 18 km. Press 8 to repeat, 0 for main menu."*

---

### Flow 2: Doctor Availability Today (Key `2`)

- **Access:** Public.
- **Safety Rule:** Strictly distinguishes verified attendance (`PRESENT`) from planned schedule (`EXPECTED`). Never claims an expected doctor is verified on site.

#### Spoken Format:
- **Case A: Verified Present (`PRESENT`)**
  - **Tamil:** *"PHC Rampur-ல் Dr. Anita Sharma இன்று அன்று பணியில் இருப்பது உறுதி செய்யப்பட்டுள்ளது. மீண்டும் கேட்க 8-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."*
  - **English:** *"At PHC Rampur, Dr. Anita Sharma on today is verified PRESENT on-site. Press 8 to repeat, 0 for main menu."*
- **Case B: Scheduled (`EXPECTED`)**
  - **Tamil:** *"PHC Rampur-ல் Dr. Anita Sharma இன்று அன்று: பணி அட்டவணையில் உள்ளார். ஆனால் வருகை இன்னும் உறுதி செய்யப்படவில்லை. மீண்டும் கேட்க 8-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."*
  - **English:** *"At PHC Rampur, Dr. Anita Sharma on today is EXPECTED as scheduled. Attendance is planned, not confirmed present. Press 8 to repeat, 0 for main menu."*
- **Case C: Absent / Unknown (`ABSENT` / `UNKNOWN`)**
  - **Tamil:** *"மருத்துவர் இன்று பணியில் இல்லை அல்லது வருகை தகவல் இல்லை."*
  - **English:** *"Doctor is absent or attendance status is unknown today."*

---

### Flow 3: Probabilistic Medicine Stock Intelligence (Key `3`)

- **Access:** Public.
- **Behavior:** Reads catalogue options (e.g. 1: Paracetamol, 2: Amoxicillin, 3: Metformin, 4: ORS). Upon selection, calculates probabilistic belief $(p, \text{conf}, \text{label})$. Discloses staleness and warns that this is logistical guidance, not a medical prescription.

#### Catalogue Prompt:
- **Tamil:** *"மருந்து இருப்பை அறிய மருந்தை தேர்வு செய்யவும்: 1: Paracetamol 500mg, 2: Amoxicillin 250mg, 3: Metformin 500mg. முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."*
- **English:** *"Select a medicine to check availability: 1: Paracetamol 500mg, 2: Amoxicillin 250mg, 3: Metformin 500mg. Press 0 for main menu."*

#### Result Prompt:
- **Tamil:** *"PHC Rampur-ல் Paracetamol 500mg மருந்து இருப்பு நிலை: பெரும்பாலும் கிடைக்கும் (LIKELY). மதிப்பிடப்பட்ட வாய்ப்பு: 85 சதவீதம். தகவல் உறுதித்தன்மை: மிதமானது. இது அதிகாரப்பூர்வ மருத்துவ பரிந்துரை அல்ல. மீண்டும் கேட்க 8-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."*
- **English:** *"At PHC Rampur, Paracetamol 500mg availability status: LIKELY. Estimated probability: 85 percent. Confidence: MODERATE. This is an estimate and not medical advice. Press 8 to repeat, 0 for main menu."*

---

### Flow 4: Security PIN Verification (Keys `4`, `5`, `6`)

- **Access:** Required prior to entering protected personal health data flows.
- **Rate Limiting:** 3 attempts maximum. On the 3rd consecutive failed attempt, the account is locked for 15 minutes and the call is terminated.
- **PIN Rule:** Securely provisioned 4-digit PIN verified via bcrypt password hashes. (Demonstration mode conditionally allows last 4 digits of phone number for simulated testing; prohibited in production).

#### Prompts:
- **Initial Challenge (Tamil):**  
  *"உங்கள் தனிப்பட்ட தகவல்களை பாதுகாக்க 4 இலக்க பின் எண்ணை உள்ளிட்டு # குறியை அழுத்தவும். (உதாரணம்: உங்கள் தொலைபேசி எண்ணின் கடைசி 4 இலக்கங்கள்). முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."*
- **Initial Challenge (English):**  
  *"For security, please enter your 4-digit PIN followed by pound. (Default is the last 4 digits of your registered mobile number). Press 0 to return to main menu."*
- **Invalid Retry (Tamil):**  
  *"தவறான பின் எண். உங்களுக்கு இன்னும் {remaining} வாய்ப்புகள் உள்ளன. மீண்டும் உள்ளிடவும்."*
- **Lockout (Tamil):**  
  *"தவறான பின் எண் அதிக முறை உள்ளிடப்பட்டதால் உங்கள் கணக்கு 15 நிமிடங்களுக்கு தற்காலிகமாக பூட்டப்பட்டுள்ளது. சிறிது நேரம் கழித்து மீண்டும் அழைக்கவும்."*
- **Lockout (English):**  
  *"Maximum PIN attempts exceeded. Your account has been temporarily locked for 15 minutes for your protection. Goodbye."*

---

### Flow 5: Create Healthcare Request & AI Recommendations (Key `4`)

1. **Request Type Submenu:**
   - `1`: Medical Consultation (மருத்துவ ஆலோசனை)
   - `2`: Medicine Refill (மருந்து மறு நிரப்பல்)
   - `3`: General Checkup (பொது பரிசோதனை)
   - `4`: Diagnostics / Lab Test (ஆய்வக பரிசோதனை)
2. **Urgency Submenu:**
   - `1`: Normal (சாதாரண)
   - `2`: Priority (அவசரமல்லாத முன்னுரிமை)
3. **Confirmation & AI Recommendations:**
   - System registers `HealthcareRequest` in database.
   - Runs `recommendation_service` to score candidate facilities based on distance, service match, and doctor attendance.
   - Reads top recommendation:  
     *"சிறந்த பரிந்துரை: PHC Rampur. மருத்துவர் பணி அட்டவணை திட்டமிடப்பட்டுள்ளது. பயண தூரம் சுமார் 10 கி.மீ நேர்கோடு. இந்த மருத்துவமனையில் முன்பதிவு செய்ய 1-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."*
4. **Direct Appointment Booking:**
   - Pressing `1` seamlessly routes caller to slot selection (10:00 AM, 12:00 PM, 2:00 PM) and books the appointment.

---

### Flow 6: Check Status & Cancellation (Key `5`)

1. **Status Summary:**
   - Queries caller's active requests and appointments.
   - Speaks count and latest appointment facility, date, and time.
   - Prompt:  
     *"உங்களிடம் 1 செயலில் உள்ள மருத்துவ கோரிக்கை மற்றும் 1 முன்பதிவு உள்ளது. அடுத்த முன்பதிவு: PHC Rampur-ல் 2026-11-13 அன்று 10:00 AM மணிக்கு. இந்த முன்பதிவை ரத்து செய்ய 1-ஐ அழுத்தவும். முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."*
2. **Explicit Cancellation Confirmation:**
   - Prompt:  
     *"உங்கள் மருத்துவ முன்பதிவை ரத்து செய்ய உறுதிப்படுத்த 1-ஐ அழுத்தவும். ரத்து செய்யாமல் தொடர 2-ஐ அழுத்தவும்."*
   - Pressing `1` updates status to `CANCELLED` in the database.
   - Pressing `2` keeps appointment and returns to Main Menu.

---

### Flow 7: Emergency 108 Guidance (Key `7`)

- **Access:** Public, immediate, unauthenticated.
- **Safety Directive:** In medical emergencies, the system directs the caller to professional ambulance dispatch and nearest emergency facility immediately.

#### Prompts:
- **Tamil:**  
  *"அவசர மருத்துவ உதவிக்கு உடனடியாக 108 என்ற எண்ணை அழைக்கவும். உங்கள் அருகிலுள்ள அவசர சிகிச்சை மையம்: City General Hospital, Central Ring Road. முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."*
- **English:**  
  *"For medical emergencies, please dial 108 immediately for an ambulance. Your nearest emergency facility is City General Hospital, Central Ring Road. Press 0 for main menu."*
