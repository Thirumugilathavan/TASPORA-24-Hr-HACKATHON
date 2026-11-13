import React, { useState } from 'react';
import {
  MapPin,
  User,
  Home,
  ShieldCheck,
  Briefcase,
  HeartPulse,
  Gift,
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  AlertCircle,
  HelpCircle,
  Info,
  Sparkles,
  Edit2,
  RotateCcw,
} from 'lucide-react';
import { useTranslation } from '../../context/LanguageContext';
import { QuestionnaireFormAnswers } from '../../services/localSchemeMatcher';

interface SchemeQuestionnaireWizardProps {
  initialAnswers?: QuestionnaireFormAnswers;
  onComplete: (answers: QuestionnaireFormAnswers) => void;
  onBrowseDirectly?: () => void;
  isSubmitting?: boolean;
}

const TN_DISTRICTS = [
  'Ariyalur',
  'Chengalpattu',
  'Chennai',
  'Coimbatore',
  'Cuddalore',
  'Dharmapuri',
  'Dindigul',
  'Erode',
  'Kallakurichi',
  'Kanchipuram',
  'Kanyakumari',
  'Karur',
  'Krishnagiri',
  'Madurai',
  'Mayiladuthurai',
  'Nagapattinam',
  'Namakkal',
  'Nilgiris',
  'Perambalur',
  'Pudukkottai',
  'Ramanathapuram',
  'Ranipet',
  'Salem',
  'Sivaganga',
  'Tenkasi',
  'Thanjavur',
  'Theni',
  'Thoothukudi',
  'Tiruchirappalli',
  'Tirunelveli',
  'Tirupathur',
  'Tiruppur',
  'Tiruvallur',
  'Tiruvannamalai',
  'Tiruvarur',
  'Vellore',
  'Viluppuram',
  'Virudhunagar',
];

export const SchemeQuestionnaireWizard: React.FC<SchemeQuestionnaireWizardProps> = ({
  initialAnswers = {},
  onComplete,
  onBrowseDirectly,
  isSubmitting = false,
}) => {
  const { language } = useTranslation();
  const isTa = language === 'ta';

  const [currentStep, setCurrentStep] = useState<number>(1);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Answers State
  const [answers, setAnswers] = useState<QuestionnaireFormAnswers>({
    state: initialAnswers.state || 'Tamil Nadu',
    district: initialAnswers.district || 'Namakkal',
    pincode: initialAnswers.pincode || '',
    town_or_village: initialAnswers.town_or_village || '',
    age: initialAnswers.age || '',
    gender: initialAnswers.gender || 'FEMALE',
    residence: initialAnswers.residence || 'RURAL',
    annual_income: initialAnswers.annual_income || '',
    income_range: initialAnswers.income_range || 'BELOW_72K',
    family_size: initialAnswers.family_size || 4,
    is_woman_head_of_household: initialAnswers.is_woman_head_of_household ?? true,
    is_head_of_household: initialAnswers.is_head_of_household ?? true,
    ration_card_type: initialAnswers.ration_card_type || 'PHH',
    caste_category: initialAnswers.caste_category || 'MBC',
    is_differently_abled: initialAnswers.is_differently_abled || false,
    disability_percentage: initialAnswers.disability_percentage || '',
    special_circumstances: initialAnswers.special_circumstances || [],
    employment_status: initialAnswers.employment_status || 'DAILY_WAGE',
    student_status: initialAnswers.student_status || 'NOT_STUDYING',
    studied_in_govt_school: initialAnswers.studied_in_govt_school || false,
    occupation: initialAnswers.occupation || 'Agricultural Laborer',
    education_level: initialAnswers.education_level || '10TH_PASS',
    pregnancy_status: initialAnswers.pregnancy_status || 'NONE',
    is_senior_citizen: initialAnswers.is_senior_citizen || false,
    healthcare_needs: initialAnswers.healthcare_needs || ['tertiary_care'],
    is_farmer: initialAnswers.is_farmer || false,
    landholding_acres: initialAnswers.landholding_acres || '',
    existing_benefits: initialAnswers.existing_benefits || [],
    desired_assistance: initialAnswers.desired_assistance || ['HEALTHCARE', 'FINANCIAL'],
  });

  const updateAnswer = (field: keyof QuestionnaireFormAnswers, value: any) => {
    setAnswers((prev) => ({ ...prev, [field]: value }));
    if (validationErrors[field]) {
      setValidationErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const toggleArrayItem = (field: 'special_circumstances' | 'healthcare_needs' | 'existing_benefits' | 'desired_assistance', item: string) => {
    setAnswers((prev) => {
      const arr = prev[field] || [];
      const updated = arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item];
      return { ...prev, [field]: updated };
    });
  };

  // Step Validation
  const validateCurrentStep = (): boolean => {
    const errors: Record<string, string> = {};

    if (currentStep === 1) {
      if (answers.pincode && !/^[1-9][0-9]{5}$/.test(answers.pincode.toString().trim())) {
        errors.pincode = isTa
          ? 'சரியான 6 இலக்க அஞ்சல் குறியீட்டை (PIN code) உள்ளிடவும்'
          : 'Please enter a valid 6-digit Indian PIN code (e.g. 637211)';
      }
    }

    if (currentStep === 2) {
      if (answers.age !== undefined && answers.age !== '') {
        const ageNum = Number(answers.age);
        if (isNaN(ageNum) || ageNum < 1 || ageNum > 120) {
          errors.age = isTa ? 'சரியான வயதை உள்ளிடவும் (1-120)' : 'Please enter a valid age between 1 and 120';
        }
      }
    }

    if (currentStep === 4) {
      if (answers.is_differently_abled && answers.disability_percentage) {
        const pct = Number(answers.disability_percentage);
        if (isNaN(pct) || pct < 1 || pct > 100) {
          errors.disability_percentage = isTa
            ? 'மாற்றுத்திறன் சதவீதம் 1 முதல் 100 வரை இருக்க வேண்டும்'
            : 'Disability percentage must be between 1 and 100';
        }
      }
    }

    if (currentStep === 6) {
      if (answers.is_farmer && answers.landholding_acres) {
        const acres = Number(answers.landholding_acres);
        if (isNaN(acres) || acres < 0) {
          errors.landholding_acres = isTa ? 'சரியான ஏக்கர் பரப்பளவை உள்ளிடவும்' : 'Please enter a valid land area in acres';
        }
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleNext = () => {
    if (validateCurrentStep()) {
      if (currentStep < 8) {
        setCurrentStep((prev) => prev + 1);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        onComplete(answers);
      }
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleSkipStep7 = () => {
    setCurrentStep(8);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const stepsMeta = [
    { num: 1, title: isTa ? 'இருப்பிடம்' : 'Location', icon: MapPin },
    { num: 2, title: isTa ? 'தனிநபர் விவரம்' : 'Profile', icon: User },
    { num: 3, title: isTa ? 'குடும்பம் & வருமானம்' : 'Household & Income', icon: Home },
    { num: 4, title: isTa ? 'சமூகத் தகுதி' : 'Social Eligibility', icon: ShieldCheck },
    { num: 5, title: isTa ? 'வேலை & கல்வி' : 'Work & Education', icon: Briefcase },
    { num: 6, title: isTa ? 'சுகாதாரம் & சூழ்நிலை' : 'Health & Circumstances', icon: HeartPulse },
    { num: 7, title: isTa ? 'பயன்கள் & தேவைகள்' : 'Benefits & Needs', icon: Gift },
    { num: 8, title: isTa ? 'சரிபார்த்து தேடல்' : 'Review & Find', icon: CheckCircle2 },
  ];

  return (
    <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden">
      {/* Top Wizard Header with Hero Prompt */}
      <div className="bg-gradient-to-r from-healthcare-800 to-navy-900 text-white p-6 md:p-8">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-white text-xs font-semibold backdrop-blur-xs mb-3">
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            <span>{isTa ? 'அரசு நலத்திட்ட வழிகாட்டி' : 'NALAM Welfare Scheme Finder'}</span>
          </div>

          <h1 className="text-xl md:text-2xl font-bold tracking-tight mb-2">
            {isTa ? 'அரசு நலத்திட்ட உதவிகளைக் கண்டறிய சில கேள்விகளுக்குப் பதிலளிக்கவும்.' : 'Answer a few questions to discover government welfare schemes that may be relevant to you.'}
          </h1>

          <p className="text-slate-200 text-xs md:text-sm leading-relaxed">
            {isTa
              ? 'உங்கள் வசிப்பிடம், வருமானம், குடும்ப நிலை மற்றும் தேவைகளின் அடிப்படையில் மத்திய மற்றும் தமிழ்நாடு அரசு வழங்கும் மானியங்கள், உதவித்தொகைகள் மற்றும் மருத்துவக் காப்பீடுகளை உடனடியாக அறியலாம்.'
              : 'Discover Central and Tamil Nadu government subsidies, maternal benefits, scholarships, and healthcare assistance tailored to your personal and household circumstances.'}
          </p>
        </div>

        {/* 8-Step Visual Progress Bar */}
        <div className="mt-8 pt-6 border-t border-white/10">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-healthcare-100">
              {isTa ? `படிநிலை ${currentStep} / 8: ${stepsMeta[currentStep - 1].title}` : `Step ${currentStep} of 8: ${stepsMeta[currentStep - 1].title}`}
            </span>
            <span className="text-xs font-bold text-amber-300">{Math.round((currentStep / 8) * 100)}% {isTa ? 'நிறைவு' : 'Completed'}</span>
          </div>

          <div className="w-full bg-white/20 h-2 rounded-full overflow-hidden">
            <div
              className="bg-amber-400 h-full rounded-full transition-all duration-300 ease-out"
              style={{ width: `${(currentStep / 8) * 100}%` }}
            />
          </div>

          {/* Step Pill Indicators for Desktop */}
          <div className="hidden md:grid grid-cols-8 gap-1 mt-3">
            {stepsMeta.map((s) => {
              const isPassed = s.num < currentStep;
              const isCurrent = s.num === currentStep;
              return (
                <button
                  key={s.num}
                  type="button"
                  onClick={() => {
                    if (s.num < currentStep) setCurrentStep(s.num);
                  }}
                  disabled={s.num > currentStep}
                  className={`text-center py-1 px-1 rounded-md text-[11px] font-medium transition-colors ${
                    isCurrent
                      ? 'bg-white/20 text-white font-bold'
                      : isPassed
                      ? 'text-emerald-300 hover:bg-white/10 cursor-pointer'
                      : 'text-slate-400 cursor-not-allowed opacity-60'
                  }`}
                >
                  {s.num}. {s.title}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Form Body */}
      <div className="p-6 md:p-8 max-w-4xl mx-auto">
        {/* ========================================================================= */}
        {/* STEP 1: LOCATION */}
        {/* ========================================================================= */}
        {currentStep === 1 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-lg font-bold text-navy-900 mb-1 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-healthcare-600" />
                <span>{isTa ? 'படி 1: உங்கள் இருப்பிட விவரங்கள்' : 'Step 1: Location & Residence'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa ? 'மாநில மற்றும் மாவட்ட அளவிலான அரசு நலத்திட்டங்களை கண்டறிய உதவுகிறது.' : 'Used to determine territory-specific Central and Tamil Nadu district welfare schemes.'}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'மாநிலம் / State' : 'State'}
                </label>
                <select
                  value={answers.state}
                  onChange={(e) => updateAnswer('state', e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                >
                  <option value="Tamil Nadu">Tamil Nadu (தமிழ்நாடு)</option>
                  <option value="Puducherry">Puducherry (புதுச்சேரி)</option>
                  <option value="Kerala">Kerala</option>
                  <option value="Karnataka">Karnataka</option>
                  <option value="Andhra Pradesh">Andhra Pradesh</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'மாவட்டம் (District)' : 'District'} *
                </label>
                <select
                  value={answers.district}
                  onChange={(e) => updateAnswer('district', e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                >
                  {TN_DISTRICTS.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'அஞ்சல் குறியீடு (PIN Code)' : 'Postal PIN Code'}
                </label>
                <input
                  type="text"
                  maxLength={6}
                  placeholder="e.g. 637211"
                  value={answers.pincode}
                  onChange={(e) => updateAnswer('pincode', e.target.value)}
                  className={`w-full bg-slate-50 border rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500 ${
                    validationErrors.pincode ? 'border-rose-400 bg-rose-50/50' : 'border-slate-300'
                  }`}
                />
                {validationErrors.pincode && (
                  <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>{validationErrors.pincode}</span>
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'கிராமம் அல்லது நகரம் (விருப்பம்)' : 'Town or Village (Optional)'}
                </label>
                <input
                  type="text"
                  placeholder="e.g. Tiruchengode / திருச்செங்கோடு"
                  value={answers.town_or_village}
                  onChange={(e) => updateAnswer('town_or_village', e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 2: PERSONAL PROFILE */}
        {/* ========================================================================= */}
        {currentStep === 2 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-lg font-bold text-navy-900 mb-1 flex items-center gap-2">
                <User className="w-5 h-5 text-healthcare-600" />
                <span>{isTa ? 'படி 2: தனிநபர் சுயவிவரம்' : 'Step 2: Personal Profile'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa ? 'வயது மற்றும் பாலினத்திற்குரிய சிறப்பு நலத்திட்டங்களை கண்டறிய உதவுகிறது.' : 'Determines age and gender-restricted schemes like scholarships, maternal aid, and senior pensions.'}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'வயது (Age)' : 'Age'}
                </label>
                <input
                  type="number"
                  min={1}
                  max={120}
                  placeholder="e.g. 35"
                  value={answers.age}
                  onChange={(e) => updateAnswer('age', e.target.value)}
                  className={`w-full bg-slate-50 border rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500 ${
                    validationErrors.age ? 'border-rose-400 bg-rose-50/50' : 'border-slate-300'
                  }`}
                />
                {validationErrors.age && (
                  <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>{validationErrors.age}</span>
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'பாலினம் (Gender)' : 'Gender'}
                </label>
                <select
                  value={answers.gender}
                  onChange={(e) => updateAnswer('gender', e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                >
                  <option value="FEMALE">{isTa ? 'பெண் (Female)' : 'Female'}</option>
                  <option value="MALE">{isTa ? 'ஆண் (Male)' : 'Male'}</option>
                  <option value="TRANSGENDER">{isTa ? 'திருநங்கை / திருநம்பி (Transgender)' : 'Transgender'}</option>
                  <option value="PREFER_NOT_TO_SAY">{isTa ? 'கூற விரும்பவில்லை (Prefer not to say)' : 'Prefer not to say'}</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'குடியிருப்பு வகை (Residence)' : 'Residence Type'}
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => updateAnswer('residence', 'RURAL')}
                    className={`py-2.5 px-3 rounded-xl border text-xs font-semibold text-center transition-all ${
                      answers.residence === 'RURAL'
                        ? 'bg-healthcare-50 border-healthcare-500 text-healthcare-800 shadow-xs'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    🏡 {isTa ? 'கிராமப்புறம் (Rural)' : 'Rural Area'}
                  </button>
                  <button
                    type="button"
                    onClick={() => updateAnswer('residence', 'URBAN')}
                    className={`py-2.5 px-3 rounded-xl border text-xs font-semibold text-center transition-all ${
                      answers.residence === 'URBAN'
                        ? 'bg-healthcare-50 border-healthcare-500 text-healthcare-800 shadow-xs'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    🏢 {isTa ? 'நகர்ப்புறம் (Urban)' : 'Urban Area'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 3: HOUSEHOLD & INCOME */}
        {/* ========================================================================= */}
        {currentStep === 3 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-lg font-bold text-navy-900 mb-1 flex items-center gap-2">
                <Home className="w-5 h-5 text-healthcare-600" />
                <span>{isTa ? 'படி 3: குடும்பம் மற்றும் வருமான விவரங்கள்' : 'Step 3: Household & Income'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'காப்பீடு, வீட்டு வசதி மற்றும் மகளிர் உரிமைத்தொகைக்கான வருமான உச்சவரம்பை சரிபார்க்கிறது.'
                  : 'Checks statutory income ceilings for health insurance (CMCHIS), basic income transfers (KMUT), and housing.'}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="md:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'குடும்ப ஆண்டு வருமான வரம்பு' : 'Annual Household Income Range'}
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  {[
                    { key: 'BELOW_72K', label_ta: 'ஆண்டுக்கு ₹72,000 வரை (வறுமைக்கோடு)', label_en: '≤ ₹72,000 / year (BPL)' },
                    { key: '72K_TO_120K', label_ta: '₹72,001 - ₹1,20,000 (CMCHIS தகுதி)', label_en: '₹72,001 - ₹1,20,000 (CMCHIS)' },
                    { key: '120K_TO_250K', label_ta: '₹1,20,001 - ₹2,50,000 (KMUT தகுதி)', label_en: '₹1,20,001 - ₹2,50,000 (KMUT)' },
                    { key: '250K_TO_500K', label_ta: '₹2,50,001 - ₹5,00,000', label_en: '₹2,50,001 - ₹5,00,000' },
                    { key: 'ABOVE_500K', label_ta: '₹5,00,000க்கு மேல்', label_en: '> ₹5,00,000' },
                  ].map((range) => (
                    <button
                      key={range.key}
                      type="button"
                      onClick={() => updateAnswer('income_range', range.key)}
                      className={`p-3 rounded-xl border text-left text-xs font-medium transition-all ${
                        answers.income_range === range.key
                          ? 'bg-healthcare-50 border-healthcare-600 text-healthcare-900 font-bold shadow-xs'
                          : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      {isTa ? range.label_ta : range.label_en}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'குடும்ப உறுப்பினர்கள் எண்ணிக்கை' : 'Family Size (Members)'}
                </label>
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={answers.family_size}
                  onChange={(e) => updateAnswer('family_size', Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'குடும்ப அட்டை வகை (Ration Card Type)' : 'Ration Card Type'}
                </label>
                <select
                  value={answers.ration_card_type}
                  onChange={(e) => updateAnswer('ration_card_type', e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                >
                  <option value="PHH">{isTa ? 'முன்னுரிமை குடும்ப அட்டை (PHH - அரிசி)' : 'Priority Household (PHH - Rice)'}</option>
                  <option value="PHH_AAY">{isTa ? 'அந்தியோதயா அன்ன யோஜனா (PHH-AAY)' : 'Antyodaya Anna Yojana (PHH-AAY)'}</option>
                  <option value="NPHH">{isTa ? 'முன்னுரிமையற்ற அட்டை (NPHH - சர்க்கரை)' : 'Non-Priority Household (NPHH)'}</option>
                  <option value="NONE">{isTa ? 'குடும்ப அட்டை இல்லை (No Ration Card)' : 'No Ration Card'}</option>
                </select>
              </div>

              <div className="md:col-span-2 pt-2">
                <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={answers.is_woman_head_of_household}
                    onChange={(e) => updateAnswer('is_woman_head_of_household', e.target.checked)}
                    className="mt-0.5 rounded text-healthcare-600 focus:ring-healthcare-500 w-4 h-4"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-800 block">
                      {isTa ? 'குடும்பத் தலைவி / குடும்பப் பெண் தலைவர் (Woman Head of Household)' : 'Woman Head of Household'}
                    </span>
                    <span className="text-[11px] text-slate-500 block">
                      {isTa ? 'கலைஞர் மகளிர் உரிமைத் திட்டத்திற்கு (KMUT) இந்த விவரம் அவசியமானது.' : 'Required for Kalaignar Magalir Urimai Thittam (KMUT ₹1,000/month basic income transfer).'}
                    </span>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 4: SOCIAL ELIGIBILITY */}
        {/* ========================================================================= */}
        {currentStep === 4 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-lg font-bold text-navy-900 mb-1 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-healthcare-600" />
                <span>{isTa ? 'படி 4: சமூக மற்றும் சிறப்புத் தகுதிகள்' : 'Step 4: Social Eligibility & Category'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa ? 'சட்டரீதியான சிறப்பு இடஒதுக்கீடு மற்றும் நலவாரிய உதவிகளுக்காக மட்டுமே இது பயன்படுகிறது.' : 'Used solely to check statutory eligibility for government welfare quotas and allowances.'}
              </p>
            </div>

            {/* Privacy Explanation Banner */}
            <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 flex items-start gap-3 text-xs text-blue-900">
              <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">{isTa ? 'தனியுரிமை மற்றும் பாதுகாப்பு விளக்கம்' : 'Privacy & Voluntary Disclosure'}</p>
                <p className="text-blue-800/90 text-[11px] mt-0.5">
                  {isTa
                    ? 'இப்பிரிவில் கேட்கப்படும் கேள்விகள் அரசு திட்டங்களின் சட்டப்பூர்வ தகுதிகளை அறிவதற்காக மட்டுமே கேட்கப்படுகின்றன. உங்கள் தகவல் எப்போதும் பாதுகாப்பாக இருக்கும்.'
                    : 'Information requested here is strictly voluntary and used only to determine eligibility under affirmative action welfare programs.'}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'சமூகப் பிரிவு (Social Category)' : 'Social Category (Optional)'}
                </label>
                <select
                  value={answers.caste_category}
                  onChange={(e) => updateAnswer('caste_category', e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                >
                  <option value="MBC">{isTa ? 'மிகவும் பிற்படுத்தப்பட்டோர் (MBC / DNC)' : 'Most Backward Class (MBC / DNC)'}</option>
                  <option value="BC">{isTa ? 'பிற்படுத்தப்பட்டோர் (BC / BCM)' : 'Backward Class (BC / BCM)'}</option>
                  <option value="SC">{isTa ? 'பட்டியலினத்தவர் (SC / SCA)' : 'Scheduled Caste (SC / SCA)'}</option>
                  <option value="ST">{isTa ? 'பழங்குடியினர் (ST)' : 'Scheduled Tribe (ST)'}</option>
                  <option value="GENERAL">{isTa ? 'பொதுப் பிரிவு (General / OC)' : 'General Category (OC)'}</option>
                  <option value="PREFER_NOT_TO_SAY">{isTa ? 'கூற விரும்பவில்லை (Prefer not to say)' : 'Prefer not to say'}</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'மாற்றுத்திறனாளி தகுதி (Disability Status)' : 'Disability Status'}
                </label>
                <select
                  value={answers.is_differently_abled ? (answers.disability_percentage ? 'YES_PCT' : 'YES') : 'NO'}
                  onChange={(e) => {
                    const isYes = e.target.value.startsWith('YES');
                    updateAnswer('is_differently_abled', isYes);
                    if (!isYes) updateAnswer('disability_percentage', '');
                  }}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                >
                  <option value="NO">{isTa ? 'இல்லை (No)' : 'No disability'}</option>
                  <option value="YES_PCT">{isTa ? 'ஆம் - 40% அல்லது அதற்கு மேற்பட்ட மாற்றுத்திறன்' : 'Yes - 40% or higher benchmark disability'}</option>
                  <option value="YES">{isTa ? 'ஆம் - 40% க்கும் குறைவான மாற்றுத்திறன்' : 'Yes - Less than 40% disability'}</option>
                </select>
              </div>

              {answers.is_differently_abled && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    {isTa ? 'மாற்றுத்திறன் சதவீதம் (%)' : 'Disability Percentage (%)'}
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    placeholder="e.g. 45"
                    value={answers.disability_percentage}
                    onChange={(e) => updateAnswer('disability_percentage', e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    {isTa ? 'மாதாந்திர ₹2,000 பராமரிப்பு உதவித்தொகை பெற 40% அல்லது அதற்கு மேல் இருக்க வேண்டும்.' : 'TN monthly maintenance allowance requires 40% or higher benchmark disability.'}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 5: EMPLOYMENT & EDUCATION */}
        {/* ========================================================================= */}
        {currentStep === 5 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-lg font-bold text-navy-900 mb-1 flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-healthcare-600" />
                <span>{isTa ? 'படி 5: வேலைவாய்ப்பு மற்றும் கல்வி நிலை' : 'Step 5: Employment & Education'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'மாணவர் கல்வி உதவித்தொகை (புதுமைப் பெண், தமிழ்ப் புதல்வன்) மற்றும் முத்ரா கடன் உதவிகளை அறிய.'
                  : 'Assesses eligibility for higher education scholarships (Pudhumai Penn, Tamil Pudhalvan) and MUDRA enterprise credit.'}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'வேலை நிலை (Employment Status)' : 'Employment Status'}
                </label>
                <select
                  value={answers.employment_status}
                  onChange={(e) => updateAnswer('employment_status', e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                >
                  <option value="DAILY_WAGE">{isTa ? 'தினக்கூலி / விவசாயத் தொழிலாளி (Daily Wage)' : 'Daily Wage Worker / Laborer'}</option>
                  <option value="SELF_EMPLOYED">{isTa ? 'சிறு தொழில் / சுயதொழில் (Self-Employed / Artisan)' : 'Self-Employed / Micro-business'}</option>
                  <option value="STUDENT">{isTa ? 'மாணவர் (Student)' : 'Student'}</option>
                  <option value="EMPLOYED">{isTa ? 'தனியார் / மாத சம்பளம் (Salaried)' : 'Salaried Employee'}</option>
                  <option value="UNEMPLOYED">{isTa ? 'வேலையில்லாதவர் (Unemployed)' : 'Unemployed'}</option>
                  <option value="RETIRED">{isTa ? 'ஓய்வு பெற்றவர் (Retired)' : 'Retired'}</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'தற்போதைய படிப்பு நிலை (Student Status)' : 'Current Student Status'}
                </label>
                <select
                  value={answers.student_status}
                  onChange={(e) => updateAnswer('student_status', e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                >
                  <option value="NOT_STUDYING">{isTa ? 'தற்போது படிக்கவில்லை (Not Studying)' : 'Not currently studying'}</option>
                  <option value="GOVT_COLLEGE">{isTa ? 'அரசு கல்லூரி / பாலிடெக்னிக் மாணவர்' : 'Government College / University / Polytechnic'}</option>
                  <option value="PRIVATE_COLLEGE">{isTa ? 'தனியார் கல்லூரி மாணவர்' : 'Private College / Higher Education'}</option>
                  <option value="HIGHER_SECONDARY">{isTa ? '11ஆம் அல்லது 12ஆம் வகுப்பு பள்ளி மாணவர்' : '11th or 12th Standard School'}</option>
                  <option value="SCHOOL">{isTa ? 'பள்ளி மாணவர் (1 முதல் 10ஆம் வகுப்பு)' : 'School Student (1st to 10th)'}</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={answers.studied_in_govt_school}
                    onChange={(e) => updateAnswer('studied_in_govt_school', e.target.checked)}
                    className="mt-0.5 rounded text-healthcare-600 focus:ring-healthcare-500 w-4 h-4"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-800 block">
                      {isTa
                        ? 'தமிழ்நாடு அரசுப் பள்ளியில் 6 முதல் 12-ஆம் வகுப்பு வரை பயின்றவர்'
                        : 'Studied from 6th to 12th standard in a Tamil Nadu Government School'}
                    </span>
                    <span className="text-[11px] text-slate-500 block">
                      {isTa
                        ? 'புதுமைப் பெண் (மாணவிகளுக்கு ₹1,000/மாதம்) மற்றும் தமிழ்ப் புதல்வன் (மாணவர்களுக்கு ₹1,000/மாதம்) திட்டங்களுக்கு இந்த நிபந்தனை முக்கியமானது.'
                        : 'Prerequisite for Pudhumai Penn (girls ₹1,000/mo) and Tamil Pudhalvan (boys ₹1,000/mo) higher education scholarships.'}
                    </span>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 6: HEALTH & FAMILY CIRCUMSTANCES */}
        {/* ========================================================================= */}
        {currentStep === 6 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-lg font-bold text-navy-900 mb-1 flex items-center gap-2">
                <HeartPulse className="w-5 h-5 text-healthcare-600" />
                <span>{isTa ? 'படி 6: சுகாதாரம் மற்றும் குடும்பச் சூழ்நிலை' : 'Step 6: Health & Family Circumstances'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'டாக்டர் முத்துலட்சுமி ரெட்டி மகப்பேறு உதவி, விவசாய மானியம் (PM-KISAN), மற்றும் முதியோர் ஓய்வூதியத் தகுதியை சரிபார்க்க.'
                  : 'Evaluates maternity benefits (MRMBS), PM-KISAN agricultural support, and senior citizen pensions.'}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'தாய்மை மற்றும் மகப்பேறு நிலை' : 'Pregnancy & Maternity Status'}
                </label>
                <select
                  value={answers.pregnancy_status}
                  onChange={(e) => updateAnswer('pregnancy_status', e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                >
                  <option value="NONE">{isTa ? 'பொருந்தாது (None)' : 'None'}</option>
                  <option value="PREGNANT">{isTa ? 'கர்ப்பிணித் தாய் (Pregnant Woman)' : 'Pregnant Woman'}</option>
                  <option value="LACTATING">{isTa ? 'பாலூட்டும் தாய் (Lactating Mother)' : 'Lactating Mother'}</option>
                  <option value="CHILD_UNDER_2">{isTa ? '2 வயதுக்குட்பட்ட குழந்தை உள்ளது' : 'Mother with child under 2 years'}</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  {isTa ? 'டாக்டர் முத்துலட்சுமி ரெட்டி மகப்பேறு திட்டம் மூலம் ₹18,000 + ஊட்டச்சத்து பெட்டகம் வழங்கப்படுகிறது.' : 'MRMBS provides ₹18,000 cash assistance and nutrition kits for institutional deliveries.'}
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'விவசாய சாகுபடி நிலம் உள்ளதா?' : 'Cultivable Agricultural Landholding?'}
                </label>
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <button
                    type="button"
                    onClick={() => updateAnswer('is_farmer', true)}
                    className={`py-2 px-3 rounded-xl border text-xs font-semibold text-center transition-all ${
                      answers.is_farmer
                        ? 'bg-healthcare-50 border-healthcare-500 text-healthcare-800 shadow-xs'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    🌾 {isTa ? 'ஆம் (நிலம் உள்ளது)' : 'Yes (Owns Land)'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      updateAnswer('is_farmer', false);
                      updateAnswer('landholding_acres', '');
                    }}
                    className={`py-2 px-3 rounded-xl border text-xs font-semibold text-center transition-all ${
                      !answers.is_farmer
                        ? 'bg-healthcare-50 border-healthcare-500 text-healthcare-800 shadow-xs'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    🚫 {isTa ? 'நிலமில்லை (No Land)' : 'No Land'}
                  </button>
                </div>

                {answers.is_farmer && (
                  <div>
                    <input
                      type="number"
                      step="0.5"
                      placeholder={isTa ? 'நில அளவு (ஏக்கரில்) e.g. 2.0' : 'Land extent in acres e.g. 2.0'}
                      value={answers.landholding_acres}
                      onChange={(e) => updateAnswer('landholding_acres', e.target.value)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-800"
                    />
                    <p className="text-[11px] text-slate-500 mt-1">
                      {isTa ? 'பிரதம மந்திரி கிசான் சம்மான் நிதி (PM-KISAN) திட்டத்திற்கு நிலப்பட்டா அவசியமானது.' : 'PM-KISAN ₹6,000/yr is restricted to farmers with cultivable landholdings.'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 7: EXISTING BENEFITS & PRIORITIES (ALLOWS SKIP) */}
        {/* ========================================================================= */}
        {currentStep === 7 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-navy-900 mb-1 flex items-center gap-2">
                  <Gift className="w-5 h-5 text-healthcare-600" />
                  <span>{isTa ? 'படி 7: ஏற்கனவே பெறும் பலன்கள் & தற்போதைய தேவைகள்' : 'Step 7: Existing Benefits & Assistance Priorities'}</span>
                </h2>
                <p className="text-xs text-slate-500">
                  {isTa ? 'நீங்கள் விரும்பும் உதவி வகைகளைத் தேர்ந்தெடுக்கவும் (தெரியவில்லை என்றால் தவிர்க்கலாம்).' : 'Select target welfare services. Unknown questions can be skipped.'}
                </p>
              </div>

              <button
                type="button"
                onClick={handleSkipStep7}
                className="text-xs text-slate-500 hover:text-navy-900 underline font-medium"
              >
                {isTa ? 'இப்படியைத் தவிர்க்க (Skip)' : 'Skip this step'}
              </button>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-2">
                {isTa ? 'நீங்கள் அறிய அல்லது பெற விரும்பும் அரசு உதவிகள்:' : 'Types of welfare assistance you are looking for:'}
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {[
                  { key: 'HEALTHCARE', icon: '🏥', label_ta: 'மருத்துவக் காப்பீடு & அறுவை சிகிச்சை நிதி', label_en: 'Healthcare Treatment & Surgery Insurance' },
                  { key: 'MATERNITY', icon: '👶', label_ta: 'கர்ப்பிணித் தாய் ஊட்டச்சத்து & மகப்பேறு நிதி', label_en: 'Maternity Financial Aid & Nutrition' },
                  { key: 'EDUCATION', icon: '🎓', label_ta: 'உயர்கல்வி மாணவர் உதவித்தொகை', label_en: 'Higher Education Scholarships' },
                  { key: 'AGRICULTURE', icon: '🌾', label_ta: 'விவசாய வருமான ஆதரவு & மானியம்', label_en: 'Farmer Income Support & Crop Aid' },
                  { key: 'LOAN', icon: '💼', label_ta: 'சிறு தொழில் தொடங்க பிணையமில்லா கடன்', label_en: 'Collateral-free Small Business Credit (MUDRA)' },
                  { key: 'PENSION', icon: '👵', label_ta: 'முதியோர் / ஆதரவற்றோர் மாதாந்திர ஓய்வூதியம்', label_en: 'Senior Citizen & Destitute Pension' },
                ].map((item) => {
                  const isSelected = (answers.desired_assistance || []).includes(item.key);
                  return (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() => toggleArrayItem('desired_assistance', item.key)}
                      className={`p-3 rounded-xl border text-left text-xs transition-all flex items-center gap-2.5 ${
                        isSelected
                          ? 'bg-healthcare-50 border-healthcare-600 text-healthcare-900 font-bold shadow-xs'
                          : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      <span className="text-base">{item.icon}</span>
                      <span>{isTa ? item.label_ta : item.label_en}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 8: REVIEW & FIND SCHEMES */}
        {/* ========================================================================= */}
        {currentStep === 8 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-lg font-bold text-navy-900 mb-1 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <span>{isTa ? 'படி 8: பதில்களைச் சரிபார்த்து தகுதியான திட்டங்களைக் கண்டறிக' : 'Step 8: Review Answers & Find Schemes'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'கீழே உள்ள உங்கள் விவரங்களை சரிபார்க்கவும். தேவைப்பட்டால் திருத்திக் கொள்ளலாம்.'
                  : 'Review your details below before running the deterministic scheme matcher.'}
              </p>
            </div>

            {/* Answer Summary Cards with Edit shortcuts */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-healthcare-600" />
                    {isTa ? 'இருப்பிடம்' : 'Location'}
                  </span>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(1)}
                    className="text-[11px] text-healthcare-700 hover:underline flex items-center gap-1 font-semibold"
                  >
                    <Edit2 className="w-3 h-3" />
                    {isTa ? 'திருத்து' : 'Edit'}
                  </button>
                </div>
                <p className="text-xs text-slate-600">
                  {answers.district}, {answers.state} {answers.pincode ? `(${answers.pincode})` : ''}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {answers.residence === 'RURAL' ? (isTa ? 'கிராமப்புறம்' : 'Rural') : (isTa ? 'நகர்ப்புறம்' : 'Urban')}
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-healthcare-600" />
                    {isTa ? 'சுயவிவரம் & குடும்பம்' : 'Profile & Household'}
                  </span>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(2)}
                    className="text-[11px] text-healthcare-700 hover:underline flex items-center gap-1 font-semibold"
                  >
                    <Edit2 className="w-3 h-3" />
                    {isTa ? 'திருத்து' : 'Edit'}
                  </button>
                </div>
                <p className="text-xs text-slate-600">
                  {answers.age ? `${answers.age} ${isTa ? 'வயது' : 'Years'}` : (isTa ? 'வயது குறிப்பிடப்படவில்லை' : 'Age not specified')}, {answers.gender}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {isTa ? `குடும்ப உறுப்பினர்கள்: ${answers.family_size}` : `Family Size: ${answers.family_size} members`}
                  {answers.is_woman_head_of_household ? ` • ${isTa ? 'பெண் குடும்பத் தலைவர்' : 'Female Head'}` : ''}
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <Home className="w-3.5 h-3.5 text-healthcare-600" />
                    {isTa ? 'வருமானம் & குடும்ப அட்டை' : 'Income & Ration Card'}
                  </span>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(3)}
                    className="text-[11px] text-healthcare-700 hover:underline flex items-center gap-1 font-semibold"
                  >
                    <Edit2 className="w-3 h-3" />
                    {isTa ? 'திருத்து' : 'Edit'}
                  </button>
                </div>
                <p className="text-xs text-slate-600 font-medium">
                  {answers.income_range}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {isTa ? `குடும்ப அட்டை: ${answers.ration_card_type}` : `Ration Card: ${answers.ration_card_type}`}
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <Briefcase className="w-3.5 h-3.5 text-healthcare-600" />
                    {isTa ? 'வேலை & சிறப்பு தகுதிகள்' : 'Work & Special Circumstances'}
                  </span>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(5)}
                    className="text-[11px] text-healthcare-700 hover:underline flex items-center gap-1 font-semibold"
                  >
                    <Edit2 className="w-3 h-3" />
                    {isTa ? 'திருத்து' : 'Edit'}
                  </button>
                </div>
                <p className="text-xs text-slate-600">
                  {answers.employment_status} • {answers.student_status}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {answers.studied_in_govt_school ? (isTa ? 'அரசுப் பள்ளி மாணவர்' : 'TN Govt School Alum') : ''}
                  {answers.is_differently_abled ? ` • ${isTa ? 'மாற்றுத்திறனாளி' : 'Differently Abled'}` : ''}
                </p>
              </div>
            </div>

            {/* Privacy Disclaimers */}
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-[11px] text-slate-600 leading-relaxed">
              <span className="font-semibold text-slate-700 block mb-0.5">
                {isTa ? 'சட்டரீதியான பொறுப்புத் துறப்பு:' : 'Statutory Transparency Notice:'}
              </span>
              {isTa
                ? 'நலம் AI வழங்கும் மதிப்பீடுகள் அரசு விதிகளின் அடிப்படையிலான கணிப்பு மட்டுமே. இறுதி ஒப்புதல் அரசுத் துறையின் அதிகாரப்பூர்வ ஆவண சரிபார்ப்புக்குப் பிறகே வழங்கப்படும்.'
                : 'Recommendations are simulated based on your questionnaire answers and officially published government criteria. NALAM AI does not guarantee statutory approval.'}
            </div>
          </div>
        )}

        {/* Wizard Navigation Footer */}
        <div className="mt-8 pt-5 border-t border-slate-200 flex items-center justify-between gap-3">
          <div>
            {currentStep > 1 && (
              <button
                type="button"
                onClick={handleBack}
                disabled={isSubmitting}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-slate-300 bg-white text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>{isTa ? 'முந்தைய படி' : 'Back'}</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-3">
            {onBrowseDirectly && currentStep < 8 && (
              <button
                type="button"
                onClick={onBrowseDirectly}
                className="text-xs text-slate-500 hover:text-navy-900 underline font-medium"
              >
                {isTa ? 'அனைத்து திட்டங்களையும் காண்க' : 'Browse All Schemes Directly'}
              </button>
            )}

            <button
              type="button"
              onClick={handleNext}
              disabled={isSubmitting}
              className={`inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold text-white transition-all shadow-sm ${
                currentStep === 8
                  ? 'bg-emerald-600 hover:bg-emerald-700 ring-2 ring-emerald-500/20'
                  : 'bg-healthcare-600 hover:bg-healthcare-700'
              }`}
            >
              <span>
                {currentStep === 8
                  ? isSubmitting
                    ? (isTa ? 'பரிசீலிக்கிறது...' : 'Evaluating Matches...')
                    : (isTa ? 'தகுதியான திட்டங்களைக் காண்க' : 'Find Eligible Schemes')
                  : (isTa ? 'தொடர்க' : 'Continue')}
              </span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
