import React, { useState } from 'react';
import {
  MapPin,
  User,
  Briefcase,
  Home,
  Gift,
  ShieldCheck,
  HeartPulse,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  AlertCircle,
  HelpCircle,
  Check,
  RotateCcw,
  Info,
} from 'lucide-react';
import { useTranslation } from '../../context/LanguageContext';
import { QuestionnaireFormAnswers } from '../../services/localSchemeMatcher';

export interface SchemeQuestionnaireWizardProps {
  initialAnswers?: QuestionnaireFormAnswers;
  onComplete: (answers: QuestionnaireFormAnswers) => void;
  onBrowseDirectly?: () => void;
  onBackToIntro?: () => void;
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
  onBackToIntro,
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
    age_range: initialAnswers.age_range || '',
    employment_status: initialAnswers.employment_status || '',
    income_range: initialAnswers.income_range || '',
    has_existing_benefits: initialAnswers.has_existing_benefits || '',
    ration_card_type: initialAnswers.ration_card_type || '',
    healthcare_needs: initialAnswers.healthcare_needs || [],
    residence: initialAnswers.residence || 'RURAL',
    gender: initialAnswers.gender || 'PREFER_NOT_TO_SAY',
    is_woman_head_of_household: initialAnswers.is_woman_head_of_household ?? false,
    is_farmer: initialAnswers.is_farmer ?? false,
    is_senior_citizen: initialAnswers.is_senior_citizen ?? false,
  });

  const updateField = (field: keyof QuestionnaireFormAnswers, value: any) => {
    setAnswers((prev) => {
      const next = { ...prev, [field]: value };

      // Synchronize age helper flags
      if (field === 'age_range') {
        if (value === '60_AND_ABOVE') {
          next.is_senior_citizen = true;
          next.age = 65;
        } else if (value === 'UNDER_18') {
          next.is_senior_citizen = false;
          next.age = 16;
        } else if (value === '18_TO_29') {
          next.is_senior_citizen = false;
          next.age = 24;
        } else if (value === '30_TO_44') {
          next.is_senior_citizen = false;
          next.age = 37;
        } else if (value === '45_TO_59') {
          next.is_senior_citizen = false;
          next.age = 52;
        }
      }

      // Synchronize occupation helper flags
      if (field === 'employment_status') {
        if (value === 'FARMER') {
          next.is_farmer = true;
          next.landholding_acres = 2.0;
        } else if (value === 'STUDENT') {
          next.student_status = 'GOVT_COLLEGE';
          next.studied_in_govt_school = true;
        }
      }

      // Synchronize income helper flags
      if (field === 'income_range') {
        if (value === 'BELOW_72K') next.annual_income = 60000;
        else if (value === '72K_TO_120K') next.annual_income = 100000;
        else if (value === '120K_TO_250K') next.annual_income = 180000;
        else if (value === '250K_TO_500K') next.annual_income = 350000;
        else if (value === 'ABOVE_500K') next.annual_income = 600000;
        else if (value === 'PREFER_NOT_TO_SAY') next.annual_income = undefined;
      }

      return next;
    });

    if (validationErrors[field]) {
      setValidationErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const toggleHealthcareNeed = (need: string) => {
    setAnswers((prev) => {
      const current = prev.healthcare_needs || [];
      const updated = current.includes(need) ? current.filter((x) => x !== need) : [...current, need];
      const next = { ...prev, healthcare_needs: updated };

      if (updated.includes('MATERNAL_CHILD')) {
        next.pregnancy_status = 'PREGNANT';
        next.gender = 'FEMALE';
        next.is_woman_head_of_household = true;
      }
      return next;
    });

    if (validationErrors.healthcare_needs) {
      setValidationErrors((prev) => {
        const next = { ...prev };
        delete next.healthcare_needs;
        return next;
      });
    }
  };

  // Step Validation
  const validateStep = (step: number): boolean => {
    const errors: Record<string, string> = {};

    if (step === 1) {
      if (!answers.district || answers.district.trim() === '') {
        errors.district = isTa ? 'மாவட்டத்தைத் தேர்ந்தெடுக்கவும்' : 'Please select your district';
      }
      if (answers.pincode && !/^[1-9][0-9]{5}$/.test(answers.pincode.toString().trim())) {
        errors.pincode = isTa
          ? 'சரியான 6 இலக்க அஞ்சல் குறியீட்டை (PIN code) உள்ளிடவும்'
          : 'Please enter a valid 6-digit Indian PIN code (e.g. 637211)';
      }
    }

    if (step === 2) {
      if (!answers.age_range) {
        errors.age_range = isTa ? 'உங்கள் வயது வரம்பைத் தேர்ந்தெடுக்கவும்' : 'Please select your age group';
      }
    }

    if (step === 3) {
      if (!answers.employment_status) {
        errors.employment_status = isTa ? 'உங்கள் தொழிலைத் தேர்ந்தெடுக்கவும்' : 'Please select your occupation or employment status';
      }
    }

    if (step === 4) {
      if (!answers.income_range) {
        errors.income_range = isTa ? 'வருமான வரம்பைத் தேர்ந்தெடுக்கவும்' : 'Please select your household income bracket';
      }
    }

    if (step === 5) {
      if (!answers.has_existing_benefits) {
        errors.has_existing_benefits = isTa ? 'ஒரு விருப்பத்தைத் தேர்ந்தெடுக்கவும்' : 'Please indicate if you receive existing government benefits';
      }
    }

    if (step === 6) {
      if (!answers.ration_card_type) {
        errors.ration_card_type = isTa ? 'ரேஷன் கார்டு வகையைத் தேர்ந்தெடுக்கவும்' : 'Please select your ration card or household category';
      }
    }

    if (step === 7) {
      if (!answers.healthcare_needs || answers.healthcare_needs.length === 0) {
        errors.healthcare_needs = isTa
          ? 'குறைந்தது ஒரு மருத்துவத் தேவையைத் தேர்ந்தெடுக்கவும்'
          : 'Please select at least one healthcare requirement';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      if (currentStep < 7) {
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
    } else if (onBackToIntro) {
      onBackToIntro();
    }
  };

  const stepsMeta = [
    { num: 1, title: isTa ? 'இருப்பிடம்' : 'Location', icon: MapPin },
    { num: 2, title: isTa ? 'வயது' : 'Age', icon: User },
    { num: 3, title: isTa ? 'தொழில்' : 'Employment', icon: Briefcase },
    { num: 4, title: isTa ? 'வருமானம்' : 'Income', icon: Home },
    { num: 5, title: isTa ? 'முந்தைய பயன்கள்' : 'Benefits', icon: Gift },
    { num: 6, title: isTa ? 'ரேஷன் கார்டு' : 'Ration Card', icon: ShieldCheck },
    { num: 7, title: isTa ? 'சுகாதாரத் தேவை' : 'Healthcare', icon: HeartPulse },
  ];

  return (
    <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden">
      {/* Top Header with Progress */}
      <div className="bg-gradient-to-r from-healthcare-800 to-navy-900 text-white p-6 md:p-8">
        <div className="max-w-3xl">
          <div className="flex items-center justify-between mb-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-white text-xs font-semibold backdrop-blur-xs">
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span>{isTa ? 'அரசு நலத்திட்ட வழிகாட்டி' : 'NALAM Welfare Scheme Finder'}</span>
            </div>
            {onBrowseDirectly && (
              <button
                type="button"
                onClick={onBrowseDirectly}
                className="text-xs text-slate-300 hover:text-white underline decoration-slate-400 underline-offset-4"
              >
                {isTa ? 'அனைத்து திட்டங்களையும் காண்க' : 'Browse All Schemes Directly'}
              </button>
            )}
          </div>

          <h1 className="text-xl md:text-2xl font-bold tracking-tight mb-2">
            {isTa ? 'தகுதியான அரசு நலத்திட்டங்களைக் கண்டறிய கேள்விகளுக்குப் பதிலளிக்கவும்' : 'Identify Eligible Government Healthcare & Welfare Schemes'}
          </h1>
          <p className="text-slate-200 text-xs md:text-sm leading-relaxed">
            {isTa
              ? 'உங்கள் பதில்களின் அடிப்படையில் முதலமைச்சரின் காப்பீடு (CMCHIS), கலைஞர் மகளிர் உரிமைத் திட்டம், PM-JAY மற்றும் தமிழ்நாடு அரசு திட்டங்களின் தகுதி சரிபார்க்கப்படும்.'
              : 'Answer each question below. NALAM AI will evaluate your answers against statutory criteria for CMCHIS, PM-JAY, KMUT, and Tamil Nadu state welfare programs.'}
          </p>

          {/* Progress Bar & Indicators */}
          <div className="mt-6 pt-5 border-t border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-healthcare-100">
                {isTa
                  ? `கேள்வி ${currentStep} / 7: ${stepsMeta[currentStep - 1].title}`
                  : `Question ${currentStep} of 7: ${stepsMeta[currentStep - 1].title}`}
              </span>
              <span className="text-xs font-bold text-amber-300">
                {Math.round((currentStep / 7) * 100)}% {isTa ? 'நிறைவு' : 'Completed'}
              </span>
            </div>

            <div className="w-full bg-white/20 h-2 rounded-full overflow-hidden">
              <div
                className="bg-amber-400 h-full rounded-full transition-all duration-300 ease-out"
                style={{ width: `${(currentStep / 7) * 100}%` }}
              />
            </div>

            {/* Step Pills for Quick Backward Navigation */}
            <div className="hidden md:grid grid-cols-7 gap-1 mt-3">
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
      </div>

      {/* Main Body: Questions 1 to 7 */}
      <div className="p-6 md:p-8 max-w-3xl mx-auto">
        {/* ========================================================================= */}
        {/* QUESTION 1: LOCATION */}
        {/* ========================================================================= */}
        {currentStep === 1 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-healthcare-600 mb-1">
                {isTa ? 'கேள்வி 1 / 7' : 'Question 1 of 7'}
              </div>
              <h2 className="text-xl font-bold text-navy-900 mb-1 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-healthcare-600" />
                <span>{isTa ? 'உங்கள் இருப்பிடம் எங்கே?' : 'Where do you live?'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'தமிழ்நாடு மற்றும் மத்திய அரசுத் திட்டங்களின் பிராந்திய தகுதியைச் சரிபார்க்க உங்கள் மாநிலம் மற்றும் மாவட்ட விவரங்களை உள்ளிடவும்.'
                  : 'State and district determine which Central and Tamil Nadu territorial schemes (such as CMCHIS and district welfare funds) apply to you.'}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'மாநிலம் / State' : 'State'} *
                </label>
                <select
                  value={answers.state}
                  onChange={(e) => updateField('state', e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                >
                  <option value="Tamil Nadu">Tamil Nadu (தமிழ்நாடு)</option>
                  <option value="Puducherry">Puducherry (புதுச்சேரி)</option>
                  <option value="Kerala">Kerala</option>
                  <option value="Karnataka">Karnataka</option>
                  <option value="Andhra Pradesh">Andhra Pradesh</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'மாவட்டம் (District)' : 'District'} *
                </label>
                <select
                  value={answers.district}
                  onChange={(e) => updateField('district', e.target.value)}
                  className={`w-full bg-slate-50 border rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500 ${
                    validationErrors.district ? 'border-rose-400 bg-rose-50/50' : 'border-slate-300'
                  }`}
                >
                  <option value="">{isTa ? '-- மாவட்டத்தைத் தேர்ந்தெடுக்கவும் --' : '-- Select District --'}</option>
                  {TN_DISTRICTS.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
                {validationErrors.district && (
                  <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>{validationErrors.district}</span>
                  </p>
                )}
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'அஞ்சல் குறியீடு (Postal PIN Code) - விருப்பத்திற்குரியது' : 'Postal PIN Code (Optional)'}
                </label>
                <input
                  type="text"
                  maxLength={6}
                  placeholder="e.g. 637211"
                  value={answers.pincode}
                  onChange={(e) => updateField('pincode', e.target.value)}
                  className={`w-full max-w-sm bg-slate-50 border rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-healthcare-500 ${
                    validationErrors.pincode ? 'border-rose-400 bg-rose-50/50' : 'border-slate-300'
                  }`}
                />
                {validationErrors.pincode && (
                  <p className="text-xs text-rose-600 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>{validationErrors.pincode}</span>
                  </p>
                )}
                <p className="text-[11px] text-slate-400 mt-1">
                  {isTa
                    ? 'உங்கள் கிராமம் அல்லது அஞ்சலகப் பகுதியில் உள்ள சிறப்பு மருத்துவ முகாம்களை இணைக்க உதவுகிறது.'
                    : 'Helps pinpoint nearby Primary Health Centres and district welfare camps.'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* QUESTION 2: AGE GROUP */}
        {/* ========================================================================= */}
        {currentStep === 2 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-healthcare-600 mb-1">
                {isTa ? 'கேள்வி 2 / 7' : 'Question 2 of 7'}
              </div>
              <h2 className="text-xl font-bold text-navy-900 mb-1 flex items-center gap-2">
                <User className="w-5 h-5 text-healthcare-600" />
                <span>{isTa ? 'உங்கள் வயது வரம்பு எது?' : 'What is your age group?'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'குழந்தைகள், இளைஞர்கள் மற்றும் முதியவர்களுக்கான பிரத்யேக மருத்துவ மற்றும் உதவித்தொகை திட்டங்களைத் தேர்ந்தெடுக்க உதவுகிறது.'
                  : 'Different government schemes target distinct life stages, including pediatric care, youth scholarships, and geriatric pensions.'}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
              {[
                {
                  id: 'UNDER_18',
                  label_en: 'Under 18',
                  label_ta: '18 வயதுக்குட்பட்டோர்',
                  desc_en: 'Minor / School child healthcare, immunization, scholarships',
                  desc_ta: 'பள்ளி மாணவர் நலம், தடுப்பூசி, கல்வி உதவித்தொகை',
                },
                {
                  id: '18_TO_29',
                  label_en: '18 – 29 years',
                  label_ta: '18 முதல் 29 வயது வரை',
                  desc_en: 'Higher education, youth skill development, career assistance',
                  desc_ta: 'கல்லூரி உயர்கல்வி, திறன் மேம்பாட்டு மானியம்',
                },
                {
                  id: '30_TO_44',
                  label_en: '30 – 44 years',
                  label_ta: '30 முதல் 44 வயது வரை',
                  desc_en: 'Working age adults, family welfare, maternity assistance',
                  desc_ta: 'குடும்ப நலம், மகப்பேறு உதவி, வாழ்வாதார திட்டங்கள்',
                },
                {
                  id: '45_TO_59',
                  label_en: '45 – 59 years',
                  label_ta: '45 முதல் 59 வயது வரை',
                  desc_en: 'Middle-aged individuals, chronic disease coverage, healthcare',
                  desc_ta: 'நடுத்தர வயது, நீண்டகால நோய் சிகிச்சை காப்பீடு',
                },
                {
                  id: '60_AND_ABOVE',
                  label_en: '60 and above',
                  label_ta: '60 வயது மற்றும் அதற்கு மேற்பட்டோர்',
                  desc_en: 'Senior citizens, geriatric healthcare, old-age pensions',
                  desc_ta: 'முதியோர் நலம், ஓய்வூதியம், சிறப்பு முதியோர் காப்பீடு',
                },
              ].map((opt) => {
                const isSelected = answers.age_range === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => updateField('age_range', opt.id)}
                    className={`text-left p-4 rounded-2xl border transition-all flex items-start gap-3.5 ${
                      isSelected
                        ? 'border-healthcare-600 bg-healthcare-50/70 shadow-xs ring-2 ring-healthcare-500/20'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full border mt-0.5 flex items-center justify-center flex-shrink-0 ${
                        isSelected ? 'border-healthcare-600 bg-healthcare-600 text-white' : 'border-slate-300'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-800">{isTa ? opt.label_ta : opt.label_en}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{isTa ? opt.desc_ta : opt.desc_en}</div>
                    </div>
                  </button>
                );
              })}
            </div>

            {validationErrors.age_range && (
              <p className="text-xs text-rose-600 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{validationErrors.age_range}</span>
              </p>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* QUESTION 3: EMPLOYMENT / OCCUPATION */}
        {/* ========================================================================= */}
        {currentStep === 3 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-healthcare-600 mb-1">
                {isTa ? 'கேள்வி 3 / 7' : 'Question 3 of 7'}
              </div>
              <h2 className="text-xl font-bold text-navy-900 mb-1 flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-healthcare-600" />
                <span>{isTa ? 'உங்கள் முதன்மை தொழில் அல்லது வேலை நிலை என்ன?' : 'What is your primary occupation or employment?'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'விவசாயிகள், தொழிலாளர்கள், மாணவர்கள் மற்றும் சுயதொழில் செய்பவர்களுக்கான பிரத்யேக நல வாரிய திட்டங்களை அறிய உதவுகிறது.'
                  : 'Schemes like PM-KISAN, Pudhumai Penn, Tamil Pudhalvan, and unorganized workers welfare boards depend on occupation.'}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
              {[
                {
                  id: 'EMPLOYED',
                  label_en: 'Employed',
                  label_ta: 'மாதச் சம்பளப் பணியாளர்',
                  desc_en: 'Salaried employee in government or private enterprise',
                  desc_ta: 'அரசு அல்லது தனியார் நிறுவன மாதச் சம்பளப் பணி',
                },
                {
                  id: 'SELF_EMPLOYED',
                  label_en: 'Self-employed / Business',
                  label_ta: 'சுயதொழில் / வியாபாரம்',
                  desc_en: 'Small shop owner, artisan, micro-enterprise, trader',
                  desc_ta: 'சிறு வணிகம், கடை, கைவினைஞர், சிறு தொழில்',
                },
                {
                  id: 'UNEMPLOYED',
                  label_en: 'Unemployed',
                  label_ta: 'வேலை தேடுபவர் / வேலையின்றி',
                  desc_en: 'Currently seeking livelihood, eligible for unemployment assistance',
                  desc_ta: 'வேலை தேடும் இளைஞர்கள் மற்றும் உதவித்தொகை தேவைப்படுவோர்',
                },
                {
                  id: 'STUDENT',
                  label_en: 'Student',
                  label_ta: 'மாணவர் / மாணவி',
                  desc_en: 'Enrolled in school, higher secondary, college, or diploma',
                  desc_ta: 'பள்ளி, கல்லூரி அல்லது பாலிடெக்னிக் பயிலும் மாணவர்கள்',
                },
                {
                  id: 'DAILY_WAGE',
                  label_en: 'Daily-wage worker',
                  label_ta: 'தினக்கூலி / அமைப்புசாரா தொழிலாளர்',
                  desc_en: 'Construction, domestic, transport, unorganized manual labor',
                  desc_ta: 'கட்டுமானத் தொழில், சுமை தூக்குவோர், உடலுழைப்புத் தொழிலாளர்',
                },
                {
                  id: 'FARMER',
                  label_en: 'Farmer / Cultivator',
                  label_ta: 'விவசாயி / நில உரிமையாளர்',
                  desc_en: 'Cultivating crops, agricultural landholder (PM-KISAN eligible)',
                  desc_ta: 'விவசாய சாகுபடி செய்வோர், விவசாய நலத்திட்ட தகுதி',
                },
                {
                  id: 'OTHER',
                  label_en: 'Other',
                  label_ta: 'மற்றவை / குடும்பத் தலைவி / ஓய்வு',
                  desc_en: 'Homemaker, caregiver, retired, or other circumstances',
                  desc_ta: 'குடும்பத் தலைவி, இல்லத்தரசி அல்லது ஓய்வு பெற்றவர்',
                },
              ].map((opt) => {
                const isSelected = answers.employment_status === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => updateField('employment_status', opt.id)}
                    className={`text-left p-4 rounded-2xl border transition-all flex items-start gap-3.5 ${
                      isSelected
                        ? 'border-healthcare-600 bg-healthcare-50/70 shadow-xs ring-2 ring-healthcare-500/20'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full border mt-0.5 flex items-center justify-center flex-shrink-0 ${
                        isSelected ? 'border-healthcare-600 bg-healthcare-600 text-white' : 'border-slate-300'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-800">{isTa ? opt.label_ta : opt.label_en}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{isTa ? opt.desc_ta : opt.desc_en}</div>
                    </div>
                  </button>
                );
              })}
            </div>

            {validationErrors.employment_status && (
              <p className="text-xs text-rose-600 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{validationErrors.employment_status}</span>
              </p>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* QUESTION 4: HOUSEHOLD FINANCIAL CIRCUMSTANCES */}
        {/* ========================================================================= */}
        {currentStep === 4 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-healthcare-600 mb-1">
                {isTa ? 'கேள்வி 4 / 7' : 'Question 4 of 7'}
              </div>
              <h2 className="text-xl font-bold text-navy-900 mb-1 flex items-center gap-2">
                <Home className="w-5 h-5 text-healthcare-600" />
                <span>{isTa ? 'உங்கள் குடும்பத்தின் தோராயமான ஆண்டு வருமானம் என்ன?' : 'What is your approximate annual household income?'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'பெரும்பாலான அரசு மானியங்கள் மற்றும் முதலமைச்சரின் காப்பீட்டுத் திட்டம் குறிப்பிட்ட வருமான வரம்பிற்குள் மட்டுமே வழங்கப்படுகின்றன.'
                  : 'Schemes such as CMCHIS and KMUT require verification against statutory annual income ceilings.'}
              </p>
            </div>

            {/* Explanatory callout about Prefer Not to Say */}
            <div className="bg-amber-50/70 border border-amber-200 rounded-2xl p-4 flex items-start gap-3 text-xs text-amber-900">
              <Info className="w-4 h-4 text-amber-700 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-semibold">{isTa ? 'ஏன் கேட்கிறோம்:' : 'Why this matters:'}</span>{' '}
                {isTa
                  ? 'முதலமைச்சரின் காப்பீட்டுத் திட்டம் (CMCHIS) மற்றும் கலைஞர் மகளிர் உரிமைத் திட்டம் போன்ற திட்டங்கள் ஆண்டு வருமானம் ₹72,000 அல்லது ₹1,20,000-க்குக் குறைவாக உள்ள குடும்பங்களுக்கு மட்டுமே பொருந்தும். "சொல்ல விரும்பவில்லை" என்பதையும் தேர்ந்தெடுக்கலாம், ஆனால் வருமான வரம்புள்ள சில திட்டங்களின் தகுதிக்கு கூடுதல் சரிபார்ப்பு தேவைப்படலாம்.'
                  : 'Providing your income range allows NALAM AI to evaluate means-tested welfare programs like Chief Minister\'s Comprehensive Health Insurance (CMCHIS) and Kalaignar Magalir Urimai Thittam. Selecting "Prefer not to say" is permitted, but schemes with strict statutory income limits may require further verification.'}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-1">
              {[
                {
                  id: 'BELOW_72K',
                  label_en: 'Below ₹72,000 / year',
                  label_ta: 'ஆண்டுக்கு ₹72,000-க்குக் கீழ்',
                  desc_en: 'Priority welfare threshold (KMUT & lowest income aid)',
                  desc_ta: 'முன்னுரிமை ஏழை எளிய குடும்பங்கள் & மகளிர் உரிமைத்தொகை தகுதி',
                },
                {
                  id: '72K_TO_120K',
                  label_en: '₹72,000 – ₹1,20,000 / year',
                  label_ta: '₹72,000 முதல் ₹1,20,000 வரை',
                  desc_en: 'Eligible for CMCHIS cashless hospital coverage',
                  desc_ta: 'முதலமைச்சரின் விரிவான மருத்துவக் காப்பீட்டு உச்சவரம்பு',
                },
                {
                  id: '120K_TO_250K',
                  label_en: '₹1,20,000 – ₹2,50,000 / year',
                  label_ta: '₹1,20,000 முதல் ₹2,50,000 வரை',
                  desc_en: 'Lower-middle income household',
                  desc_ta: 'குறைந்த நடுத்தர வருமான குடும்பங்கள்',
                },
                {
                  id: '250K_TO_500K',
                  label_en: '₹2,50,000 – ₹5,00,000 / year',
                  label_ta: '₹2,50,000 முதல் ₹5,00,000 வரை',
                  desc_en: 'Middle income household',
                  desc_ta: 'நடுத்தர வருமான குடும்பங்கள்',
                },
                {
                  id: 'ABOVE_500K',
                  label_en: 'Above ₹5,00,000 / year',
                  label_ta: 'ஆண்டுக்கு ₹5,00,000-க்கு மேல்',
                  desc_en: 'Higher income household',
                  desc_ta: 'உயர் வருமானப் பிரிவு',
                },
                {
                  id: 'PREFER_NOT_TO_SAY',
                  label_en: 'Prefer not to say',
                  label_ta: 'கூற விரும்பவில்லை',
                  desc_en: 'Skip income evaluation; verify criteria independently',
                  desc_ta: 'வருமான வரம்பை இப்போது குறிப்பிடாமல் தொடரவும்',
                },
              ].map((opt) => {
                const isSelected = answers.income_range === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => updateField('income_range', opt.id)}
                    className={`text-left p-4 rounded-2xl border transition-all flex items-start gap-3.5 ${
                      isSelected
                        ? 'border-healthcare-600 bg-healthcare-50/70 shadow-xs ring-2 ring-healthcare-500/20'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full border mt-0.5 flex items-center justify-center flex-shrink-0 ${
                        isSelected ? 'border-healthcare-600 bg-healthcare-600 text-white' : 'border-slate-300'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-800">{isTa ? opt.label_ta : opt.label_en}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{isTa ? opt.desc_ta : opt.desc_en}</div>
                    </div>
                  </button>
                );
              })}
            </div>

            {validationErrors.income_range && (
              <p className="text-xs text-rose-600 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{validationErrors.income_range}</span>
              </p>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* QUESTION 5: EXISTING GOVERNMENT BENEFITS */}
        {/* ========================================================================= */}
        {currentStep === 5 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-healthcare-600 mb-1">
                {isTa ? 'கேள்வி 5 / 7' : 'Question 5 of 7'}
              </div>
              <h2 className="text-xl font-bold text-navy-900 mb-1 flex items-center gap-2">
                <Gift className="w-5 h-5 text-healthcare-600" />
                <span>
                  {isTa
                    ? 'நீங்கள் தற்போது அரசு மருத்துவ அல்லது நலத்திட்ட உதவிகளைப் பெறுகிறீர்களா?'
                    : 'Do you currently receive benefits from any government scheme?'}
                </span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'ஏற்கனவே பெற்று வரும் திட்டங்களுடன் இணைந்து நீங்கள் கூடுதலாகப் பெறக்கூடிய நலத்திட்டங்களை அடையாளம் காண உதவுகிறது.'
                  : 'Helps prevent duplicate applications and identifies complementary schemes you are also eligible to receive.'}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
              {[
                {
                  id: 'YES',
                  label_en: 'Yes',
                  label_ta: 'ஆம்',
                  desc_en: 'Currently enrolled in one or more government welfare/health programs',
                  desc_ta: 'தற்போது ஒன்று அல்லது அதற்கு மேற்பட்ட அரசுத் திட்டங்களில் பயன் பெறுகிறேன்',
                },
                {
                  id: 'NO',
                  label_en: 'No',
                  label_ta: 'இல்லை',
                  desc_en: 'Not currently receiving benefits from any government scheme',
                  desc_ta: 'எந்தவொரு அரசு நலத்திட்ட உதவியும் தற்போது பெறவில்லை',
                },
                {
                  id: 'NOT_SURE',
                  label_en: 'Not sure',
                  label_ta: 'தெரியவில்லை / உறுதியில்லை',
                  desc_en: 'Uncertain of current enrollment or past card validity',
                  desc_ta: 'பதிவு நிலை அல்லது குடும்ப அட்டை பயன்கள் பற்றி உறுதியாகத் தெரியவில்லை',
                },
              ].map((opt) => {
                const isSelected = answers.has_existing_benefits === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => updateField('has_existing_benefits', opt.id)}
                    className={`text-left p-4 rounded-2xl border transition-all flex flex-col justify-between ${
                      isSelected
                        ? 'border-healthcare-600 bg-healthcare-50/70 shadow-xs ring-2 ring-healthcare-500/20'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full mb-2">
                      <span className="text-base font-bold text-slate-800">{isTa ? opt.label_ta : opt.label_en}</span>
                      <div
                        className={`w-5 h-5 rounded-full border flex items-center justify-center flex-shrink-0 ${
                          isSelected ? 'border-healthcare-600 bg-healthcare-600 text-white' : 'border-slate-300'
                        }`}
                      >
                        {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                      </div>
                    </div>
                    <span className="text-xs text-slate-500 leading-relaxed">{isTa ? opt.desc_ta : opt.desc_en}</span>
                  </button>
                );
              })}
            </div>

            {validationErrors.has_existing_benefits && (
              <p className="text-xs text-rose-600 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{validationErrors.has_existing_benefits}</span>
              </p>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* QUESTION 6: RATION CARD / HOUSEHOLD ELIGIBILITY */}
        {/* ========================================================================= */}
        {currentStep === 6 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-healthcare-600 mb-1">
                {isTa ? 'கேள்வி 6 / 7' : 'Question 6 of 7'}
              </div>
              <h2 className="text-xl font-bold text-navy-900 mb-1 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-healthcare-600" />
                <span>
                  {isTa
                    ? 'உங்கள் குடும்பத்திற்கு எந்த வகை ரேஷன் கார்டு உள்ளது?'
                    : 'What ration card or household category applies to your family?'}
                </span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'தமிழ்நாடு ஸ்மார்ட் ரேஷன் கார்டு வகை (PHH, AAY, NPHH) தமிழ்நாடு நலத்திட்டங்களின் முக்கிய ஆவணமாகும்.'
                  : 'Ration card category is the primary verification key used by the Tamil Nadu Civil Supplies and Health Department.'}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
              {[
                {
                  id: 'PHH',
                  label_en: 'Priority Household (PHH / Rice Card)',
                  label_ta: 'முன்னுரிமை குடும்ப அட்டை (PHH - அரிசி அட்டை)',
                  desc_en: 'Eligible for all subsidized food, health insurance & welfare schemes',
                  desc_ta: 'அனைத்து இலவச அரிசி, மளிகைப் பொருட்கள் மற்றும் மருத்துவக் காப்பீடு',
                },
                {
                  id: 'PHH_AAY',
                  label_en: 'Antyodaya Anna Yojana (AAY)',
                  label_ta: 'அந்தியோதயா அன்ன யோஜனா (AAY - வறுமைக் கோட்டிற்கு கீழ்)',
                  desc_en: 'Poorest of poor households; highest priority state & central aid',
                  desc_ta: 'மிகவும் பின்தங்கிய ஏழைக் குடும்பங்கள், மிக முன்னுரிமை உதவி',
                },
                {
                  id: 'NPHH',
                  label_en: 'Non-Priority Household (NPHH)',
                  label_ta: 'முன்னுரிமையற்ற குடும்ப அட்டை (NPHH - சர்க்கரை அட்டை)',
                  desc_en: 'Standard household sugar/commodity card',
                  desc_ta: 'சர்க்கரை அட்டை அல்லது பொருட்கள் இல்லாத குடும்ப அட்டை',
                },
                {
                  id: 'NOT_SURE',
                  label_en: 'Not sure',
                  label_ta: 'தெரியவில்லை / அட்டை வகை தெரியாது',
                  desc_en: 'Card category unknown, pending application or verification',
                  desc_ta: 'குடும்ப அட்டை வகை விவரம் தெரியவில்லை அல்லது விண்ணப்ப நிலையில் உள்ளது',
                },
                {
                  id: 'NOT_APPLICABLE',
                  label_en: 'Not applicable / No ration card',
                  label_ta: 'பொருந்தாது / ரேஷன் கார்டு இல்லை',
                  desc_en: 'Do not have an active ration card in Tamil Nadu',
                  desc_ta: 'தற்போது குடும்ப அட்டை கைவசம் இல்லை',
                },
              ].map((opt) => {
                const isSelected = answers.ration_card_type === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => updateField('ration_card_type', opt.id)}
                    className={`text-left p-4 rounded-2xl border transition-all flex items-start gap-3.5 ${
                      isSelected
                        ? 'border-healthcare-600 bg-healthcare-50/70 shadow-xs ring-2 ring-healthcare-500/20'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full border mt-0.5 flex items-center justify-center flex-shrink-0 ${
                        isSelected ? 'border-healthcare-600 bg-healthcare-600 text-white' : 'border-slate-300'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-800">{isTa ? opt.label_ta : opt.label_en}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{isTa ? opt.desc_ta : opt.desc_en}</div>
                    </div>
                  </button>
                );
              })}
            </div>

            {validationErrors.ration_card_type && (
              <p className="text-xs text-rose-600 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{validationErrors.ration_card_type}</span>
              </p>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* QUESTION 7: HEALTHCARE REQUIREMENT (MULTI-SELECT) */}
        {/* ========================================================================= */}
        {currentStep === 7 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-healthcare-600 mb-1">
                {isTa ? 'கேள்வி 7 / 7' : 'Question 7 of 7'}
              </div>
              <h2 className="text-xl font-bold text-navy-900 mb-1 flex items-center gap-2">
                <HeartPulse className="w-5 h-5 text-healthcare-600" />
                <span>
                  {isTa
                    ? 'உங்களுக்கு என்ன வகையான மருத்துவ அல்லது சுகாதார உதவி தேவை?'
                    : 'What specific healthcare or medical assistance are you looking for?'}
                </span>
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'பொருந்தக்கூடிய அனைத்தையும் தேர்ந்தெடுக்கலாம் (ஒன்றுக்கு மேற்பட்டவற்றைத் தேர்வு செய்யலாம்):'
                  : 'Select all that apply to you or your family members:'}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
              {[
                {
                  id: 'HOSPITALISATION',
                  label_en: 'Hospitalisation',
                  label_ta: 'மருத்துவமனையில் தங்கி சிகிச்சை',
                  desc_en: 'Inpatient hospital admission, bed care, ICU, cashless treatment',
                  desc_ta: 'உள்நோயாளி படுக்கை சிகிச்சை, முதலமைச்சரின் காப்பீடு',
                },
                {
                  id: 'SURGERY',
                  label_en: 'Surgery',
                  label_ta: 'அறுவை சிகிச்சை (Surgery)',
                  desc_en: 'Major or minor surgical procedures, cardiac, ortho, eye surgery',
                  desc_ta: 'இதயம், கண், எலும்பு முறிவு மற்றும் பொது அறுவை சிகிச்சைகள்',
                },
                {
                  id: 'DIAGNOSTICS',
                  label_en: 'Diagnostic tests',
                  label_ta: 'பரிசோதனைகள் (MRI, CT, Lab Tests)',
                  desc_en: 'Diagnostic scans, blood investigations, pathology tests',
                  desc_ta: 'ரத்தப் பரிசோதனை, ஸ்கேன் மற்றும் மருத்துவ ஆய்வகச் சோதனைகள்',
                },
                {
                  id: 'MEDICINES',
                  label_en: 'Medicines',
                  label_ta: 'மருந்து மாத்திரைகள் உதவி',
                  desc_en: 'Prescription medicines for diabetes, hypertension, chronic illness',
                  desc_ta: 'நீரிழிவு, ரத்த அழுத்தம் மற்றும் நீண்டகால நோய்களுக்கான மருந்துகள்',
                },
                {
                  id: 'MATERNAL_CHILD',
                  label_en: 'Maternal and child healthcare',
                  label_ta: 'தாய் சேய் நலம் & கர்ப்பகால உதவி',
                  desc_en: 'Pregnancy assistance, hospital delivery, Dr. Muthulakshmi Reddy scheme',
                  desc_ta: 'டாக்டர் முத்துலட்சுமி ரெட்டி மகப்பேறு நிதி உதவி, ஊட்டச்சத்து பெட்டகம்',
                },
                {
                  id: 'PREVENTIVE',
                  label_en: 'Preventive healthcare',
                  label_ta: 'முன்னெச்சரிக்கை பரிசோதனை & முகாம்கள்',
                  desc_en: 'General health checkups, cancer screenings, eye & dental camps',
                  desc_ta: 'மக்களைத் தேடி மருத்துவம், ஆரம்ப சுகாதார நிலைய பரிசோதனைகள்',
                },
                {
                  id: 'GENERAL',
                  label_en: 'General healthcare assistance',
                  label_ta: 'பொது மருத்துவ உதவி & மருத்துவர் ஆலோசனை',
                  desc_en: 'Outpatient consultation (OPD), fever, seasonal ailments',
                  desc_ta: 'அரசு ஆரம்ப சுகாதார நிலைய நேரடி மருத்துவ ஆலோசனை',
                },
                {
                  id: 'OTHER',
                  label_en: 'Other',
                  label_ta: 'மற்றவை / மாற்றுத்திறன் உபகரணங்கள்',
                  desc_en: 'Assistive devices, disability aids, emergency ambulance coverage',
                  desc_ta: 'மாற்றுத்திறனாளி உபகரணங்கள், அவசர கால உதவி',
                },
              ].map((opt) => {
                const isSelected = (answers.healthcare_needs || []).includes(opt.id);
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => toggleHealthcareNeed(opt.id)}
                    className={`text-left p-4 rounded-2xl border transition-all flex items-start gap-3.5 ${
                      isSelected
                        ? 'border-healthcare-600 bg-healthcare-50/70 shadow-xs ring-2 ring-healthcare-500/20'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-md border mt-0.5 flex items-center justify-center flex-shrink-0 ${
                        isSelected ? 'border-healthcare-600 bg-healthcare-600 text-white' : 'border-slate-300'
                      }`}
                    >
                      {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-800">{isTa ? opt.label_ta : opt.label_en}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{isTa ? opt.desc_ta : opt.desc_en}</div>
                    </div>
                  </button>
                );
              })}
            </div>

            {validationErrors.healthcare_needs && (
              <p className="text-xs text-rose-600 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{validationErrors.healthcare_needs}</span>
              </p>
            )}

            {/* Privacy Guarantee Note */}
            <div className="text-[11px] text-slate-400 border-t border-slate-100 pt-3">
              🛡️ {isTa ? 'தனியுரிமை உறுதி: ஆதார் எண், கடவுச்சொல் அல்லது வங்கி கணக்கு எண்களை நாங்கள் ஒருபோதும் கேட்பதில்லை.' : 'Privacy Guarantee: We never collect Aadhaar numbers, passwords, or bank account details.'}
            </div>
          </div>
        )}

        {/* Bottom Wizard Navigation Buttons */}
        <div className="mt-8 pt-6 border-t border-slate-200 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={handleBack}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>
              {currentStep === 1
                ? isTa
                  ? 'முகப்புக்குத் திரும்பு'
                  : 'Back to Intro'
                : isTa
                ? 'முந்தைய கேள்வி'
                : 'Back'}
            </span>
          </button>

          <div className="text-xs text-slate-400 font-medium">
            {isTa ? `படி ${currentStep} / 7` : `Step ${currentStep} of 7`}
          </div>

          <button
            type="button"
            onClick={handleNext}
            disabled={isSubmitting}
            className={`inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold text-white shadow-sm transition-all ${
              currentStep === 7
                ? 'bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-700 hover:to-teal-800 ring-2 ring-emerald-500/20'
                : 'bg-healthcare-600 hover:bg-healthcare-700'
            }`}
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>{isTa ? 'மதிப்பிடப்படுகிறது...' : 'Evaluating Matches...'}</span>
              </>
            ) : currentStep === 7 ? (
              <>
                <Sparkles className="w-4 h-4 text-amber-300" />
                <span>{isTa ? 'பொருத்தமான திட்டங்களைக் கண்டறியவும்' : 'Find Matching Schemes'}</span>
              </>
            ) : (
              <>
                <span>{isTa ? 'அடுத்த கேள்வி' : 'Next Question'}</span>
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
