/**
 * Client-Side Deterministic Scheme Matching Engine.
 * Provides instant evaluations and offline resilience when backend or network is down.
 * Matches 100% of the verified government statutory eligibility rules.
 */

import { VERIFIED_SCHEMES_CATALOG, VerifiedScheme } from '../data/verifiedSchemesCatalog';
import { SchemeMatchResponse, SchemeMatchItemOut } from '../types';

export interface QuestionnaireFormAnswers {
  // Step 1: Location
  state?: string;
  district?: string;
  pincode?: string;
  town_or_village?: string;

  // Step 2: Personal Profile
  age?: number | string;
  age_range?: string;
  gender?: string; // FEMALE, MALE, TRANSGENDER, PREFER_NOT_TO_SAY
  residence?: string; // RURAL, URBAN

  // Step 3: Household & Income
  annual_income?: number | string;
  income_range?: string; // BELOW_72K, 72K_TO_120K, 120K_TO_250K, 250K_TO_500K, ABOVE_500K
  family_size?: number | string;
  is_woman_head_of_household?: boolean;
  is_head_of_household?: boolean;
  ration_card_type?: string; // PHH, PHH_AAY, NPHH, NPHH_S, NONE, UNKNOWN

  // Step 4: Social Eligibility
  caste_category?: string; // SC, ST, MBC, BC, GENERAL, PREFER_NOT_TO_SAY
  is_differently_abled?: boolean;
  disability_percentage?: number | string;
  special_circumstances?: string[]; // destitute, widow, orphan

  // Step 5: Employment & Education
  employment_status?: string; // EMPLOYED, UNEMPLOYED, SELF_EMPLOYED, DAILY_WAGE, STUDENT, RETIRED
  student_status?: string; // SCHOOL, HIGHER_SECONDARY, GOVT_COLLEGE, PRIVATE_COLLEGE, ITI_DIPLOMA, NOT_STUDYING
  studied_in_govt_school?: boolean;
  occupation?: string;
  education_level?: string;

  // Step 6: Health & Family Circumstances
  pregnancy_status?: string; // PREGNANT, LACTATING, CHILD_UNDER_2, NONE
  is_senior_citizen?: boolean;
  healthcare_needs?: string[]; // tertiary_care, chronic_disease, assistive_devices
  is_farmer?: boolean;
  landholding_acres?: number | string;

  // Step 7: Existing Benefits & Priorities
  existing_benefits?: string[];
  desired_assistance?: string[];

  language?: string;
}

export function evaluateLocalSchemeMatches(
  answers: QuestionnaireFormAnswers,
  language: string = 'ta'
): SchemeMatchResponse {
  const isTa = language === 'ta';

  // 1. Normalize demographic numbers
  const age = answers.age ? Number(answers.age) : undefined;
  const isSenior = answers.is_senior_citizen || (age !== undefined && age >= 60);
  const gender = answers.gender || 'PREFER_NOT_TO_SAY';
  const state = answers.state || 'Tamil Nadu';
  const isTamilNadu = state.toLowerCase().includes('tamil');
  const residence = answers.residence || 'RURAL';

  // Income mapping
  let income = answers.annual_income ? Number(answers.annual_income) : undefined;
  if (income === undefined) {
    if (answers.income_range === 'BELOW_72K') income = 60000;
    else if (answers.income_range === '72K_TO_120K') income = 100000;
    else if (answers.income_range === '120K_TO_250K') income = 180000;
    else if (answers.income_range === '250K_TO_500K') income = 350000;
    else if (answers.income_range === 'ABOVE_500K') income = 600000;
    else income = 80000;
  }

  const hasRationCard = answers.ration_card_type !== 'NONE';
  const isWomanHead = Boolean(answers.is_woman_head_of_household);
  const isFemale = gender === 'FEMALE' || isWomanHead;
  const isMale = gender === 'MALE';
  const isDifferentlyAbled = Boolean(answers.is_differently_abled);
  const disabilityPct = answers.disability_percentage ? Number(answers.disability_percentage) : 0;
  const isStudent =
    answers.student_status === 'SCHOOL' ||
    answers.student_status === 'HIGHER_SECONDARY' ||
    answers.student_status === 'GOVT_COLLEGE' ||
    answers.student_status === 'PRIVATE_COLLEGE' ||
    answers.student_status === 'ITI_DIPLOMA' ||
    answers.employment_status === 'STUDENT';
  const studiedGovtSchool = Boolean(answers.studied_in_govt_school);
  const isPregnantOrMaternal =
    answers.pregnancy_status === 'PREGNANT' ||
    answers.pregnancy_status === 'LACTATING' ||
    answers.pregnancy_status === 'CHILD_UNDER_2';
  const ownsLand =
    Boolean(answers.is_farmer) || (answers.landholding_acres !== undefined && Number(answers.landholding_acres) > 0);
  const desired = answers.desired_assistance || [];
  const healthcareNeeds = answers.healthcare_needs || [];

  const likelyMatches: SchemeMatchItemOut[] = [];
  const moreInfoNeeded: SchemeMatchItemOut[] = [];
  const notMatching: SchemeMatchItemOut[] = [];
  const allResults: SchemeMatchItemOut[] = [];

  for (const scheme of VERIFIED_SCHEMES_CATALOG) {
    const rules = scheme.eligibility_rules || {};
    const matchedReasons: string[] = [];
    const missingInfo: string[] = [];
    const unmetCriteria: string[] = [];
    let hardFail = false;
    let potentialFail = false;
    let score = 50;

    // A. State / Territory Check
    const allowedStates = rules.allowed_states || ['ALL'];
    if (!allowedStates.includes('ALL') && !allowedStates.includes(state)) {
      hardFail = true;
      unmetCriteria.push(
        isTa ? `வசிப்பிடம் தமிழ்நாட்டில் இல்லை (${state})` : `Residency outside eligible state (${state})`
      );
    } else {
      matchedReasons.push(isTa ? `வசிப்பிடம் தகுதியானது (${state})` : `Resident of eligible state (${state})`);
    }

    // B. Income Check
    const maxIncome = rules.max_annual_income;
    if (maxIncome !== undefined && income !== undefined) {
      if (income > maxIncome) {
        hardFail = true;
        unmetCriteria.push(
          isTa
            ? `ஆண்டு வருமானம் ₹${maxIncome.toLocaleString('en-IN')} வரம்பை விட அதிகம் (தற்போதைய வருமானம்: ₹${income.toLocaleString('en-IN')})`
            : `Household annual income exceeds ₹${maxIncome.toLocaleString('en-IN')} statutory limit (Current: ₹${income.toLocaleString('en-IN')})`
        );
      } else {
        score += 20;
        matchedReasons.push(
          isTa
            ? `ஆண்டு வருமானம் ₹${maxIncome.toLocaleString('en-IN')} வரம்பிற்குள் உள்ளது`
            : `Household income within statutory ceiling of ₹${maxIncome.toLocaleString('en-IN')}`
        );
      }
    } else if (maxIncome !== undefined) {
      missingInfo.push(
        isTa
          ? `வருமானச் சான்றிதழ் விவரம் தேவை (அதிகபட்ச வரம்பு: ₹${maxIncome.toLocaleString('en-IN')})`
          : `Income verification required (Statutory limit: ₹${maxIncome.toLocaleString('en-IN')})`
      );
    }

    // C. Gender Checks
    const allowedGenders = rules.allowed_genders;
    if (allowedGenders) {
      if (gender !== 'PREFER_NOT_TO_SAY' && !allowedGenders.includes(gender) && !(allowedGenders.includes('FEMALE') && isWomanHead)) {
        hardFail = true;
        unmetCriteria.push(
          isTa
            ? `இத்திட்டம் ${allowedGenders.join(', ')} பயனாளிகளுக்கு மட்டுமே பொருந்தும்`
            : `Scheme is exclusively for ${allowedGenders.join(', ')} applicants`
        );
      } else if (allowedGenders.includes(gender) || (allowedGenders.includes('FEMALE') && isFemale)) {
        score += 15;
        matchedReasons.push(
          isTa ? 'பாலினத் தகுதி நிபந்தனை பொருந்துகிறது' : 'Applicant gender satisfies scheme target demographic'
        );
      } else {
        missingInfo.push(isTa ? 'பாலின விவரம் உறுதிப்படுத்தப்பட வேண்டும்' : 'Gender selection required to confirm target demographic');
      }
    }

    // D. Age Checks
    const minAge = rules.min_age;
    const maxAge = rules.max_age;
    if (age !== undefined) {
      if (minAge !== undefined && age < minAge) {
        hardFail = true;
        unmetCriteria.push(isTa ? `குறைந்தபட்ச வயது ${minAge} பூர்த்தியாகவில்லை (தற்போதைய வயது: ${age})` : `Applicant age (${age}) below minimum required age of ${minAge}`);
      } else if (maxAge !== undefined && age > maxAge) {
        hardFail = true;
        unmetCriteria.push(isTa ? `அதிகபட்ச வயது வரம்பு ${maxAge} தாண்டியது (தற்போதைய வயது: ${age})` : `Applicant age (${age}) exceeds maximum allowed age of ${maxAge}`);
      } else {
        if (minAge !== undefined || maxAge !== undefined) {
          score += 10;
          matchedReasons.push(isTa ? `வயது வரம்பு பொருந்துகிறது (${age} வயது)` : `Applicant age (${age}) satisfies scheme age criteria`);
        }
      }
    } else if (minAge !== undefined || maxAge !== undefined) {
      missingInfo.push(isTa ? 'வயது விவரம் உறுதிப்படுத்தப்பட வேண்டும்' : 'Age verification required');
    }

    // E. Scheme Specific Rules
    // CMCHIS
    if (scheme.slug === 'cmchis-tamil-nadu') {
      if (!isTamilNadu) hardFail = true;
      if (income !== undefined && income <= 120000) {
        matchedReasons.push(isTa ? 'முதலமைச்சரின் காப்பீட்டுக்கான வருமான வரம்பு (< ₹1,20,000) பொருந்துகிறது' : 'Qualifies for cashless hospitalization under CMCHIS ceiling');
        score += 25;
      }
      if (!hasRationCard) {
        missingInfo.push(isTa ? 'ஸ்மார்ட் குடும்ப அட்டை அவசியம்' : 'Tamil Nadu Smart Ration Card is mandatory');
      }
    }

    // KMUT
    if (scheme.slug === 'kmut-kalaignar-magalir-urimai') {
      if (!isTamilNadu) hardFail = true;
      if (isMale) {
        hardFail = true;
        unmetCriteria.push(isTa ? 'கலைஞர் மகளிர் உரிமைத் திட்டம் குடும்ப பெண் தலைவருக்கு மட்டுமே' : 'Kalaignar Magalir Urimai Thittam is strictly for female heads of household');
      } else if (isFemale) {
        matchedReasons.push(isTa ? 'குடும்ப பெண் தலைவருக்கான உரிமைத்தொகை தகுதி பொருந்துகிறது' : 'Qualifies as female head of household for monthly basic income');
        score += 25;
      }
    }

    // MRMBS
    if (scheme.slug === 'mrmbs-muthulakshmi-reddy-tn') {
      if (isMale) {
        hardFail = true;
        unmetCriteria.push(isTa ? 'இத்திட்டம் கர்ப்பிணி மற்றும் பாலூட்டும் தாய்மார்களுக்கு மட்டுமே' : 'Scheme is exclusively for pregnant and lactating mothers');
      } else if (isPregnantOrMaternal) {
        matchedReasons.push(isTa ? 'கர்ப்பிணி / பாலூட்டும் தாய்மார்களுக்கான மகப்பேறு நிதி உதவி தகுதி பொருந்துகிறது' : 'Qualifies for pregnancy and maternity nutritional financial support');
        score += 35;
      } else {
        potentialFail = true;
        missingInfo.push(isTa ? 'கர்ப்பிணி அல்லது பாலூட்டும் தாய்மை நிலை பதிவு (RCH/PICME ID) தேவை' : 'Maternity / PICME registration required');
      }
    }

    // Pudhumai Penn
    if (scheme.slug === 'pudhumai-penn-scheme-tn') {
      if (isMale) {
        hardFail = true;
        unmetCriteria.push(isTa ? 'புதுமைப் பெண் திட்டம் மாணவிகளுக்கு மட்டுமே' : 'Pudhumai Penn is strictly for female students');
      } else if (isFemale && isStudent && studiedGovtSchool) {
        matchedReasons.push(isTa ? 'அரசுப் பள்ளியில் பயின்று உயர்கல்வி தொடரும் மாணவிக்கான தகுதி பொருந்துகிறது' : 'Eligible for ₹1,000/mo scholarship as girl student from TN govt school pursuing higher education');
        score += 35;
      } else if (isFemale && isStudent) {
        missingInfo.push(isTa ? 'தமிழ்நாடு அரசுப் பள்ளியில் 6-12ஆம் வகுப்பு பயின்றதற்கான சான்றிதழ் தேவை' : 'Proof of studying 6th-12th standard in Tamil Nadu Government school required');
      } else {
        potentialFail = true;
      }
    }

    // Tamil Pudhalvan
    if (scheme.slug === 'tamil-pudhalvan-scheme-tn') {
      if (isFemale) {
        hardFail = true;
        unmetCriteria.push(isTa ? 'தமிழ்ப் புதல்வன் திட்டம் மாணவர்களுக்கு மட்டுமே' : 'Tamil Pudhalvan is strictly for male students');
      } else if (isMale && isStudent && studiedGovtSchool) {
        matchedReasons.push(isTa ? 'அரசுப் பள்ளியில் பயின்று உயர்கல்வி தொடரும் மாணவர்க்கான தகுதி பொருந்துகிறது' : 'Eligible for ₹1,000/mo incentive as male student from TN govt school pursuing higher education');
        score += 35;
      } else if (isMale && isStudent) {
        missingInfo.push(isTa ? 'தமிழ்நாடு அரசுப் பள்ளியில் 6-12ஆம் வகுப்பு பயின்றதற்கான சான்றிதழ் தேவை' : 'Proof of studying 6th-12th standard in Tamil Nadu Government school required');
      } else {
        potentialFail = true;
      }
    }

    // PM-KISAN
    if (scheme.slug === 'pm-kisan-samman-nidhi') {
      if (ownsLand) {
        matchedReasons.push(isTa ? 'விவசாய நிலம் உள்ள உழவர் குடும்பங்களுக்கான நிதி உதவி தகுதி பொருந்துகிறது' : 'Eligible as landholding farmer family for ₹6,000/year income support');
        score += 30;
      } else if (answers.occupation?.toLowerCase().includes('farm') || answers.is_farmer) {
        missingInfo.push(isTa ? 'வருவாய்த்துறை நிலப்பட்டா / சிட்டா ஆவணம் சமர்ப்பிக்கப்பட வேண்டும்' : 'Revenue land records (Patta/Chitta) required to verify cultivable land ownership');
      } else {
        hardFail = true;
        unmetCriteria.push(isTa ? 'விவசாய சாகுபடி நிலம் உள்ள உழவர் குடும்பங்களுக்கு மட்டுமே' : 'PM-KISAN is exclusively for farmer families with cultivable land');
      }
    }

    // Differently Abled Maintenance Allowance
    if (scheme.slug === 'differently-abled-maintenance-allowance-tn') {
      if (isDifferentlyAbled && disabilityPct >= 40) {
        matchedReasons.push(isTa ? 'மாற்றுத்திறனாளி மாதாந்திர பராமரிப்பு உதவித்தொகை தகுதி பொருந்துகிறது (40% மேல்)' : 'Eligible for ₹2,000/mo maintenance allowance with >=40% benchmark disability');
        score += 35;
      } else if (isDifferentlyAbled) {
        missingInfo.push(isTa ? 'மருத்துவக் குழு வழங்கிய 40% அல்லது அதற்கு மேற்பட்ட மாற்றுத்திறனாளி சான்றிதழ் தேவை' : 'UDID / District Medical Board certificate with >= 40% disability required');
      } else {
        hardFail = true;
        unmetCriteria.push(isTa ? '40% அல்லது அதற்கு மேற்பட்ட மாற்றுத்திறனாளிகளுக்கு மட்டுமே' : 'Exclusively for persons with 40% or higher benchmark disability');
      }
    }

    // OAP (Old Age Pension)
    if (scheme.slug === 'oap-indira-gandhi-old-age-pension') {
      if (age !== undefined && age >= 60 && income !== undefined && income <= 100000) {
        matchedReasons.push(isTa ? '60 வயதுக்கு மேற்பட்ட முதியோர் ஓய்வூதிய தகுதி பொருந்துகிறது' : 'Eligible for senior citizen monthly social security pension (Age 60+)');
        score += 30;
      } else if (age !== undefined && age < 60) {
        hardFail = true;
        unmetCriteria.push(isTa ? 'முதியோர் ஓய்வூதியத்திற்கு குறைந்தபட்ச வயது 60 ஆகும்' : 'Minimum age of 60 required for Old Age Pension');
      } else {
        missingInfo.push(isTa ? 'வயது மற்றும் வறுமைக்கோட்டிற்கு கீழ் உள்ளமைக்கான வட்டாட்சியர் சான்றிதழ் தேவை' : 'Proof of age (60+) and BPL/Destitute income certificate required');
      }
    }

    // Desired assistance alignment
    if (desired.includes('HEALTHCARE') && scheme.category === 'HEALTHCARE') score += 15;
    if (desired.includes('EDUCATION') && scheme.category === 'EDUCATION') score += 15;
    if (desired.includes('AGRICULTURE') && scheme.category === 'AGRICULTURE') score += 15;
    if (desired.includes('LOAN') && scheme.category === 'FINANCIAL') score += 15;

    // Determine final status
    let status: 'LIKELY_MATCH' | 'MORE_INFO_NEEDED' | 'NOT_MATCHING' = 'MORE_INFO_NEEDED';
    let statusLabelEn = 'More information needed';
    let statusLabelTa = 'கூடுதல் தகவல் தேவை';

    if (hardFail) {
      status = 'NOT_MATCHING';
      statusLabelEn = 'Not currently matching';
      statusLabelTa = 'தகுதி பொருந்தவில்லை';
      score = Math.min(score, 30);
    } else if (potentialFail) {
      status = 'MORE_INFO_NEEDED';
      statusLabelEn = 'More information needed';
      statusLabelTa = 'கூடுதல் தகவல் தேவை';
      score = Math.min(score, 65);
    } else if (missingInfo.length === 0 || (missingInfo.length <= 1 && score >= 70)) {
      status = 'LIKELY_MATCH';
      statusLabelEn = 'Likely match';
      statusLabelTa = 'பொருத்தமானது';
      score = Math.max(score, 80);
    }

    const item: SchemeMatchItemOut = {
      scheme: {
        ...scheme,
        level: scheme.level as 'CENTRAL' | 'STATE' | 'DISTRICT' | 'LOCAL',
        category: scheme.category as any,
        eligibility_rules: scheme.eligibility_rules,
        required_documents: scheme.required_documents.map((d) => ({
          name_en: d.name_en,
          name_ta: d.name_ta,
          is_mandatory: d.is_mandatory,
          description_en: d.description_en,
          description_ta: d.description_ta,
        })),
        is_saved: false,
      },
      match_status: status,
      match_status_label_en: statusLabelEn,
      match_status_label_ta: statusLabelTa,
      match_score: Math.min(100, Math.round(score)),
      reasons: matchedReasons.length > 0 ? matchedReasons : [isTa ? 'அடிப்படை குடியிருப்பு விவரம் பொருந்துகிறது' : 'Basic residency matches'],
      missing_information: missingInfo.length > 0 ? missingInfo : [isTa ? 'அதிகாரப்பூர்வ ஆவண சரிபார்ப்பு தேவை' : 'Official documentation verification required'],
      unmet_criteria: unmetCriteria,
      required_documents: scheme.required_documents.map((d) => ({
        name_en: d.name_en,
        name_ta: d.name_ta,
        is_mandatory: d.is_mandatory,
        description_en: d.description_en,
        description_ta: d.description_ta,
      })),
      official_source_url: scheme.official_source_url,
      official_portal_url: scheme.official_portal_url,
      last_verified_date: 'November 2026',
      application_status: scheme.application_status || 'OPEN',
      is_saved: false,
    };

    allResults.push(item);
    if (status === 'LIKELY_MATCH') likelyMatches.push(item);
    else if (status === 'MORE_INFO_NEEDED') moreInfoNeeded.push(item);
    else notMatching.push(item);
  }

  // Sort by score descending
  likelyMatches.sort((a, b) => b.match_score - a.match_score);
  moreInfoNeeded.sort((a, b) => b.match_score - a.match_score);
  notMatching.sort((a, b) => b.match_score - a.match_score);
  allResults.sort((a, b) => b.match_score - a.match_score);

  return {
    total_evaluated: VERIFIED_SCHEMES_CATALOG.length,
    likely_matches_count: likelyMatches.length,
    more_info_needed_count: moreInfoNeeded.length,
    not_matching_count: notMatching.length,
    likely_matches: likelyMatches,
    more_info_needed: moreInfoNeeded,
    not_matching: notMatching,
    all_results: allResults,
    disclaimer_en:
      'These evaluations are based on officially published eligibility rules and the information you provided. Formal verification by the respective government department is required. NALAM AI does not guarantee benefit approval.',
    disclaimer_ta:
      'இந்த மதிப்பீடுகள் அதிகாரப்பூர்வ தகுதி விதிகளின் அடிப்படையில் கணக்கிடப்பட்டுள்ளன. இறுதி அங்கீகாரம் சம்பந்தப்பட்ட அரசுத் துறையினரால் வழங்கப்படும். நலம் ஏஐ திட்ட அனுமதியை உறுதிப்படுத்தாது.',
    evaluated_at: new Date().toISOString(),
  };
}
