# NALAM Symptom Guidance Safety Documentation

## Date: November 13, 2026

## 1. Overview

NALAM provides non-diagnostic, first-aid-level symptom guidance to users in Tamil and English. This guidance is designed to help users understand their symptoms, take basic self-care steps, and recognize when to seek medical attention.

**NALAM does NOT provide medical diagnoses or prescriptions.**

Every symptom guidance response includes an explicit disclaimer stating this.

## 2. Supported Symptoms

| Symptom | English Keywords | Tamil Keywords |
|---|---|---|
| Fever | fever | காய்ச்சல் |
| Cough | cough | இருமல் |
| Cold | cold | சளி |
| Headache | headache | தலைவலி |
| Vomiting | vomit, vomiting | வாந்தி |
| Diarrhea | diarrhea | பேதி |
| Stomach Pain | stomach pain | வயிற்று வலி |
| Sore Throat | sore throat | தொண்டை வலி |
| Body Pain | body pain | உடல் வலி |
| Dizziness | dizziness, dizzy | தலைச்சுற்றல் |
| Dehydration | dehydration | நீரிழப்பு |
| Weakness | weakness, feel sick | சோர்வு, உடம்பு சரியில்லை |
| Cuts/Wounds | cuts, wound, bleeding | காயம், ரத்தம் |

## 3. Fever Guidance Details

Fever receives the most comprehensive guidance because it is the most commonly queried symptom and has important safety considerations.

### Included in Fever Guidance

1. **Immediate self-care steps**
   - Rest, adequate fluid intake, light clothing
   - ORS (Oral Rehydration Solution) preparation instructions

2. **Medication safety**
   - Paracetamol (Acetaminophen) dosage caveats
   - Warning: Do not self-prescribe antibiotics
   - Warning: Do not take aspirin for children (Reye's syndrome risk)

3. **When to seek medical attention (danger signs)**
   - Fever above 103°F / 39.4°C
   - Fever lasting more than 3 days
   - Difficulty breathing
   - Severe headache with neck stiffness
   - Rash or skin changes
   - Confusion or altered consciousness
   - Seizures / convulsions

4. **Child fever special caution**
   - Infants under 3 months: any fever requires immediate medical attention
   - Children: specific temperature thresholds

5. **Dengue and malaria awareness**
   - Symptoms overlap with common fever
   - Do NOT take aspirin or ibuprofen (dengue risk)
   - Platelet count monitoring reminder
   - Seek medical testing if fever persists with body pain

6. **Follow-up questions**
   - How long has the fever lasted?
   - Any rash or skin changes?
   - Any recent travel?
   - Is the patient a child?

## 4. Combined Symptom + Facility Intent

When a user says "I have fever and need a hospital in Sulur", NALAM:
1. Provides symptom guidance first
2. Then searches for facilities in the specified location
3. Combines both in a single response

This uses the `SYMPTOM_WITH_FACILITY` intent type.

## 5. Educational vs. Guidance Distinction

Queries phrased as educational questions (e.g., "What causes fever?", "How to prevent dehydration?") are classified as `HEALTH_INFORMATION`, not `SYMPTOM_GUIDANCE`.

This prevents educational queries from triggering first-aid guidance responses when the user is seeking general knowledge.

## 6. Clinical Disclaimers

Every symptom guidance response includes:

> ⚠️ **Disclaimer:** This is general health guidance, not a medical diagnosis or prescription. Please consult a qualified healthcare professional for proper diagnosis and treatment.

This disclaimer appears in both Tamil and English, matching the user's selected language.

## 7. Sources

All symptom guidance content is attributed to the following authoritative sources:

| Source | Organization |
|---|---|
| MoHFW India | Ministry of Health and Family Welfare, Government of India |
| NHM | National Health Mission |
| WHO | World Health Organization |
| NHS | National Health Service (UK) — for general first-aid guidelines |
| ICMR | Indian Council of Medical Research |

## 8. Safety Rules

1. **Never diagnose.** NALAM states symptoms and possible next steps, never identifies a disease.
2. **Never prescribe.** NALAM mentions general medication categories (e.g., "paracetamol may help") but never prescribes specific dosages.
3. **Always recommend professional consultation** for persistent, severe, or concerning symptoms.
4. **Highlight danger signs prominently** so users know when to seek emergency care.
5. **Child safety is paramount.** Any fever in an infant under 3 months triggers an immediate "seek medical attention" recommendation.
6. **Dengue caution** is always mentioned in fever guidance for Tamil Nadu users, given endemic risk.
7. **Source attribution** is included to maintain trust and traceability.
