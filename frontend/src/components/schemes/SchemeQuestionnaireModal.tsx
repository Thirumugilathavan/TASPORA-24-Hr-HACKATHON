import React, { useState } from 'react';
import {
  X,
  ChevronRight,
  ChevronLeft,
  ShieldCheck,
  Check,
  Info,
  Sparkles,
} from 'lucide-react';
import { useTranslation } from '../../context/LanguageContext';
import { UserSchemeProfile } from '../../types';

interface SchemeQuestionnaireModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveProfile: (profileData: Record<string, any>) => Promise<void>;
  initialProfile?: UserSchemeProfile | null;
}

export const SchemeQuestionnaireModal: React.FC<SchemeQuestionnaireModalProps> = ({
  isOpen,
  onClose,
  onSaveProfile,
  initialProfile,
}) => {
  const { language } = useTranslation();
  const isTa = language === 'ta';

  const defaultData = initialProfile?.profile_data || {};

  const [step, setStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Form State across 8 Steps
  const [basic, setBasic] = useState({
    age: defaultData.basic?.age || 35,
    dob: defaultData.basic?.dob || '',
    state: defaultData.basic?.state || 'Tamil Nadu',
    district: defaultData.basic?.district || 'Namakkal',
    village_or_town: defaultData.basic?.village_or_town || 'Tiruchengode',
    residence_type: defaultData.basic?.residence_type || 'RURAL',
    is_indian_citizen: defaultData.basic?.is_indian_citizen !== false,
  });

  const [household, setHousehold] = useState({
    family_size: defaultData.household?.family_size || 4,
    earning_members: defaultData.household?.earning_members || 1,
    children_count: defaultData.household?.children_count || 2,
    senior_citizens_count: defaultData.household?.senior_citizens_count || 1,
    is_female_headed: defaultData.household?.is_female_headed || false,
    marital_status: defaultData.household?.marital_status || 'MARRIED',
    has_disabled_member: defaultData.household?.has_disabled_member || false,
  });

  const [financial, setFinancial] = useState({
    income_range: defaultData.financial?.income_range || 'BELOW_1_LAKH',
    annual_income: defaultData.financial?.annual_income || 90000,
    employment_status: defaultData.financial?.employment_status || 'DAILY_WAGE',
    income_source: defaultData.financial?.income_source || 'AGRICULTURE',
    has_ration_card: defaultData.financial?.has_ration_card !== false,
    ration_card_type: defaultData.financial?.ration_card_type || 'PHH',
  });

  const [social, setSocial] = useState({
    community_category: defaultData.social?.community_category || 'OBC',
    has_community_certificate: defaultData.social?.has_community_certificate !== false,
    has_disability_certificate: defaultData.social?.has_disability_certificate || false,
    is_widow: defaultData.social?.is_widow || false,
    is_senior_citizen: defaultData.social?.is_senior_citizen || false,
    is_student: defaultData.social?.is_student || false,
    is_woman_seeking_aid: defaultData.social?.is_woman_seeking_aid || false,
    is_farmer: defaultData.social?.is_farmer || false,
  });

  const [education, setEducation] = useState({
    highest_qualification: defaultData.education_employment?.highest_qualification || '12TH_PASS',
    current_education_status: defaultData.education_employment?.current_education_status || 'NOT_STUDYING',
    studied_in_govt_school: defaultData.education_employment?.studied_in_govt_school || false,
    seeking_scholarships: defaultData.education_employment?.seeking_scholarships || false,
    seeking_employment: defaultData.education_employment?.seeking_employment || false,
    interested_in_business: defaultData.education_employment?.interested_in_business || false,
  });

  const [agriculture, setAgriculture] = useState({
    owns_agricultural_land: defaultData.agriculture_business?.owns_agricultural_land || false,
    land_acres: defaultData.agriculture_business?.land_acres || 2.0,
    farmer_category: defaultData.agriculture_business?.farmer_category || 'SMALL_MARGINAL',
    has_business: defaultData.agriculture_business?.has_business || false,
    business_type: defaultData.agriculture_business?.business_type || '',
  });

  const [healthcare, setHealthcare] = useState({
    needs_health_insurance: defaultData.healthcare_needs?.needs_health_insurance !== false,
    needs_hospital_treatment_aid: defaultData.healthcare_needs?.needs_hospital_treatment_aid || false,
    needs_maternal_child_care: defaultData.healthcare_needs?.needs_maternal_child_care || false,
    needs_disability_support: defaultData.healthcare_needs?.needs_disability_support || false,
    needs_senior_care: defaultData.healthcare_needs?.needs_senior_care || false,
    needs_medicine_assistance: defaultData.healthcare_needs?.needs_medicine_assistance || false,
  });

  const [needs, setNeeds] = useState<string[]>(
    defaultData.financial_needs || ['HEALTHCARE', 'WOMEN_CHILD', 'PENSION', 'AGRICULTURE']
  );

  const toggleNeed = (cat: string) => {
    if (cat === 'ALL') {
      setNeeds(['ALL']);
      return;
    }
    const filtered = needs.filter((n) => n !== 'ALL');
    if (filtered.includes(cat)) {
      const next = filtered.filter((n) => n !== cat);
      setNeeds(next.length === 0 ? ['ALL'] : next);
    } else {
      setNeeds([...filtered, cat]);
    }
  };

  const handleFinish = async () => {
    setIsSubmitting(true);
    try {
      const payload = {
        basic,
        household,
        financial,
        social,
        education_employment: education,
        agriculture_business: agriculture,
        healthcare_needs: healthcare,
        financial_needs: needs,
      };
      await onSaveProfile(payload);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-navy-950/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-xl rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Wizard Header & Progress */}
        <div className="p-5 border-b border-slate-100 bg-slate-50/70">
          <div className="flex items-center justify-between mb-3">
            <div>
              <span className="text-[11px] uppercase font-bold text-healthcare-700 tracking-wider">
                {isTa ? `படி ${step} / 8` : `Step ${step} of 8`}
              </span>
              <h2 className="text-base font-bold text-navy-900 tracking-tight">
                {isTa ? 'எனக்கான அரசு நலத்திட்டங்களை கண்டறிக' : 'Find Government Schemes for Me'}
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
            <div
              className="bg-healthcare-600 h-full transition-all duration-300 rounded-full"
              style={{ width: `${(step / 8) * 100}%` }}
            />
          </div>
        </div>

        {/* Wizard Step Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-5 text-sm">
          {/* Step 1: Basic Information */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-xs text-blue-900 flex items-start gap-2">
                <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                <span>
                  {isTa
                    ? 'உங்கள் வசிப்பிடம் மற்றும் வயதை அடிப்படையாகக் கொண்டு மத்திய மற்றும் தமிழ்நாடு அரசு திட்டங்கள் கண்டறியப்படும்.'
                    : 'Territorial eligibility (Central vs Tamil Nadu State schemes) depends on your residential location and age.'}
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  {isTa ? 'உங்கள் வயது' : 'Age (Years)'}
                </label>
                <input
                  type="number"
                  min="0"
                  max="110"
                  value={basic.age}
                  onChange={(e) => setBasic({ ...basic, age: parseInt(e.target.value) || 0 })}
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-healthcare-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    {isTa ? 'மாநிலம்' : 'State'}
                  </label>
                  <input
                    type="text"
                    value={basic.state}
                    onChange={(e) => setBasic({ ...basic, state: e.target.value })}
                    className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-healthcare-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    {isTa ? 'மாவட்டம்' : 'District'}
                  </label>
                  <input
                    type="text"
                    value={basic.district}
                    onChange={(e) => setBasic({ ...basic, district: e.target.value })}
                    className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-healthcare-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  {isTa ? 'கிராமம் அல்லது நகரம்' : 'Village, Town, or City'}
                </label>
                <input
                  type="text"
                  value={basic.village_or_town}
                  onChange={(e) => setBasic({ ...basic, village_or_town: e.target.value })}
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-healthcare-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  {isTa ? 'வசிப்பிட வகை' : 'Residence Type'}
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setBasic({ ...basic, residence_type: 'RURAL' })}
                    className={`p-3 rounded-xl border text-xs font-semibold transition-all ${
                      basic.residence_type === 'RURAL'
                        ? 'border-healthcare-600 bg-healthcare-50 text-healthcare-800 shadow-xs'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    🏡 {isTa ? 'கிராமப்புறம் (Rural)' : 'Rural Area'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setBasic({ ...basic, residence_type: 'URBAN' })}
                    className={`p-3 rounded-xl border text-xs font-semibold transition-all ${
                      basic.residence_type === 'URBAN'
                        ? 'border-healthcare-600 bg-healthcare-50 text-healthcare-800 shadow-xs'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    🏢 {isTa ? 'நகர்ப்புறம் (Urban)' : 'Urban / Municipality'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Household Info */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    {isTa ? 'குடும்ப உறுப்பினர்கள் எண்ணிக்கை' : 'Family Size'}
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={household.family_size}
                    onChange={(e) => setHousehold({ ...household, family_size: parseInt(e.target.value) || 1 })}
                    className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    {isTa ? 'குழந்தைகள் எண்ணிக்கை' : 'Number of Children'}
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={household.children_count}
                    onChange={(e) => setHousehold({ ...household, children_count: parseInt(e.target.value) || 0 })}
                    className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  {isTa ? 'திருமண நிலை' : 'Marital Status'}
                </label>
                <select
                  value={household.marital_status}
                  onChange={(e) => setHousehold({ ...household, marital_status: e.target.value })}
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm bg-white"
                >
                  <option value="MARRIED">{isTa ? 'திருமணமானவர் (Married)' : 'Married'}</option>
                  <option value="SINGLE">{isTa ? 'திருமணமாகாதவர் (Single)' : 'Single'}</option>
                  <option value="WIDOWED">{isTa ? 'விதவை / விதவையாளர் (Widowed)' : 'Widowed'}</option>
                  <option value="DIVORCED">{isTa ? 'விவாகரத்து / பிரிந்து வாழ்பவர்' : 'Divorced / Deserted'}</option>
                </select>
              </div>

              <div className="space-y-2 pt-2">
                <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={household.is_female_headed}
                    onChange={(e) => setHousehold({ ...household, is_female_headed: e.target.checked })}
                    className="rounded text-healthcare-600 focus:ring-healthcare-500 h-4 w-4"
                  />
                  <div>
                    <span className="font-semibold text-xs text-navy-900 block">
                      {isTa ? 'குடும்பத் தலைவி பெண் (KMUT தகுதி)' : 'Female-Headed Household'}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      {isTa ? 'குடும்பத் தலைவராக பெண் உள்ள குடும்பம்' : 'Household where a woman is the primary decision maker'}
                    </span>
                  </div>
                </label>

                <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={household.has_disabled_member}
                    onChange={(e) => setHousehold({ ...household, has_disabled_member: e.target.checked })}
                    className="rounded text-healthcare-600 focus:ring-healthcare-500 h-4 w-4"
                  />
                  <div>
                    <span className="font-semibold text-xs text-navy-900 block">
                      {isTa ? 'குடும்பத்தில் மாற்றுத்திறனாளி உறுப்பினர் உள்ளார்' : 'Member with Disability in Family'}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      {isTa ? 'மாற்றுத்திறனாளி பராமரிப்பு உதவித்தொகைக்கு தகுதியானது' : 'Enables disability-related assistance'}
                    </span>
                  </div>
                </label>
              </div>
            </div>
          )}

          {/* Step 3: Financial & Ration Card */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-xs text-emerald-900 flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <span>
                  {isTa
                    ? 'ரகசியத்தன்மை: வங்கி கணக்கு எண்கள், கடவுச்சொற்கள் அல்லது OTP எப்போதும் கேட்கப்பட மாட்டாது. தோராயமான வருமான வரம்பு மட்டுமே தேவை.'
                    : 'Security Guarantee: We never request bank credentials, OTPs, or passwords. Only income brackets are evaluated.'}
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  {isTa ? 'ஆண்டு குடும்ப வருமான வரம்பு' : 'Annual Household Income Range'}
                </label>
                <select
                  value={financial.income_range}
                  onChange={(e) => setFinancial({ ...financial, income_range: e.target.value })}
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm bg-white"
                >
                  <option value="BELOW_1_LAKH">{isTa ? '₹1,00,000 வரை (Below ₹1 Lakh)' : 'Below ₹1,00,000 per year (BPL/Vulnerable)'}</option>
                  <option value="1_TO_2.5_LAKH">{isTa ? '₹1,00,000 முதல் ₹2,50,000 வரை' : '₹1,00,000 – ₹2,50,000 per year (EWS/Low Income)'}</option>
                  <option value="2.5_TO_5_LAKH">{isTa ? '₹2,50,000 முதல் ₹5,00,000 வரை' : '₹2,50,000 – ₹5,00,000 per year'}</option>
                  <option value="5_TO_8_LAKH">{isTa ? '₹5,00,000 முதல் ₹8,00,000 வரை' : '₹5,00,000 – ₹8,00,000 per year'}</option>
                  <option value="ABOVE_8_LAKH">{isTa ? '₹8,00,000-க்கு மேல்' : 'Above ₹8,00,000 per year'}</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  {isTa ? 'முக்கிய வருமான ஆதாரம்' : 'Main Household Income Source'}
                </label>
                <select
                  value={financial.income_source}
                  onChange={(e) => setFinancial({ ...financial, income_source: e.target.value })}
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm bg-white"
                >
                  <option value="AGRICULTURE">{isTa ? 'விவசாயம் / கூலி வேலை' : 'Agriculture / Farm Labor'}</option>
                  <option value="DAILY_WAGE">{isTa ? 'தினக்கூலி தொழிலாளி' : 'Daily Wage Worker'}</option>
                  <option value="BUSINESS">{isTa ? 'சிறு தொழில் / வியாபாரம்' : 'Small Business / Shop'}</option>
                  <option value="SALARIED">{isTa ? 'மாத ஊதியம்' : 'Salaried Employee'}</option>
                  <option value="PENSION">{isTa ? 'ஓய்வூதியம்' : 'Pensioner'}</option>
                  <option value="UNEMPLOYED">{isTa ? 'வேலையின்றி' : 'Unemployed'}</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  {isTa ? 'ரேஷன் அட்டை (Smart Card) வகை' : 'Ration Card Category'}
                </label>
                <select
                  value={financial.ration_card_type}
                  onChange={(e) => setFinancial({ ...financial, ration_card_type: e.target.value })}
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm bg-white"
                >
                  <option value="PHH">{isTa ? 'PHH - முன்னுரிமை குடும்ப அட்டை' : 'PHH (Priority Household - Green/White card)'}</option>
                  <option value="PHH_AAY">{isTa ? 'AAY - அந்தியோதயா அன்ன யோஜனா' : 'AAY (Antyodaya Anna Yojana - Extreme Poverty)'}</option>
                  <option value="NPHH">{isTa ? 'NPHH - முன்னுரிமையற்ற அட்டை' : 'NPHH (Non-Priority Household)'}</option>
                  <option value="NONE">{isTa ? 'ரேஷன் அட்டை இல்லை' : 'No Ration Card'}</option>
                </select>
              </div>
            </div>
          )}

          {/* Step 4: Social Eligibility */}
          {step === 4 && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'சிறப்பு தகுதிகள் அரசு திட்டங்களின் இடஒதுக்கீடு மற்றும் முன்னுரிமைகளுக்கு உதவும்.'
                  : 'Social eligibility parameters determine targeted welfare board and pension allocations.'}
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  {isTa ? 'சமூகப் பிரிவு (Community Category)' : 'Community Category'}
                </label>
                <select
                  value={social.community_category}
                  onChange={(e) => setSocial({ ...social, community_category: e.target.value })}
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm bg-white"
                >
                  <option value="OBC">OBC / BC / BCM</option>
                  <option value="MBC">MBC / DNC</option>
                  <option value="SC">SC (Scheduled Caste) / SC(A)</option>
                  <option value="ST">ST (Scheduled Tribe)</option>
                  <option value="GENERAL">General / Others</option>
                </select>
              </div>

              <div className="space-y-2 pt-2">
                <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={social.is_widow}
                    onChange={(e) => setSocial({ ...social, is_widow: e.target.checked })}
                    className="rounded text-healthcare-600 h-4 w-4"
                  />
                  <span className="text-xs font-semibold text-navy-900">
                    {isTa ? 'ஆதரவற்ற விதவை பெண் (விதவை ஓய்வூதியத் தகுதி)' : 'Widowed Woman (Widow Pension Eligibility)'}
                  </span>
                </label>

                <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={social.has_disability_certificate}
                    onChange={(e) => setSocial({ ...social, has_disability_certificate: e.target.checked })}
                    className="rounded text-healthcare-600 h-4 w-4"
                  />
                  <span className="text-xs font-semibold text-navy-900">
                    {isTa ? 'மாற்றுத்திறனாளி சான்றிதழ் அல்லது UDID அட்டை உள்ளது' : 'Holds Disability Certificate / UDID Card (40%+)'}
                  </span>
                </label>

                <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={social.is_senior_citizen}
                    onChange={(e) => setSocial({ ...social, is_senior_citizen: e.target.checked })}
                    className="rounded text-healthcare-600 h-4 w-4"
                  />
                  <span className="text-xs font-semibold text-navy-900">
                    {isTa ? '60 வயதுக்கு மேற்பட்ட முதியோர் (முதியோர் ஓய்வூதியத் தகுதி)' : 'Senior Citizen Aged 60+ (Old Age Pension)'}
                  </span>
                </label>

                <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={social.is_woman_seeking_aid}
                    onChange={(e) => setSocial({ ...social, is_woman_seeking_aid: e.target.checked })}
                    className="rounded text-healthcare-600 h-4 w-4"
                  />
                  <span className="text-xs font-semibold text-navy-900">
                    {isTa ? 'மகளிர் சுய உதவிக்குழு அல்லது நலத்திட்டம் நாடும் பெண்' : 'Woman Seeking Financial or Livelihood Assistance'}
                  </span>
                </label>
              </div>
            </div>
          )}

          {/* Step 5: Education & Employment */}
          {step === 5 && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  {isTa ? 'தற்போதைய கல்வி நிலை' : 'Current Education Status'}
                </label>
                <select
                  value={education.current_education_status}
                  onChange={(e) => setEducation({ ...education, current_education_status: e.target.value })}
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm bg-white"
                >
                  <option value="NOT_STUDYING">{isTa ? 'படிக்கவில்லை (Not studying)' : 'Not Currently Studying'}</option>
                  <option value="COLLEGE_UG">{isTa ? 'கல்லூரி இளங்கலை (UG Degree)' : 'College Undergraduate (UG)'}</option>
                  <option value="COLLEGE_PG">{isTa ? 'கல்லூரி முதுகலை (PG Degree)' : 'College Postgraduate (PG)'}</option>
                  <option value="ITI_DIPLOMA">{isTa ? 'டிப்ளமோ / ஐடிஐ (Polytechnic / ITI)' : 'Polytechnic / ITI Diploma'}</option>
                  <option value="SCHOOL">{isTa ? 'பள்ளி மாணவர் (School 1-12)' : 'School Student'}</option>
                </select>
              </div>

              <div className="space-y-2 pt-1">
                <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={education.studied_in_govt_school}
                    onChange={(e) => setEducation({ ...education, studied_in_govt_school: e.target.checked })}
                    className="rounded text-healthcare-600 h-4 w-4"
                  />
                  <div>
                    <span className="font-semibold text-xs text-navy-900 block">
                      {isTa ? 'அரசுப் பள்ளியில் 6 முதல் 12-ஆம் வகுப்பு வரை படித்தவர்' : 'Studied in Govt School (Classes 6 to 12)'}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      {isTa ? 'புதுமைப் பெண் & தமிழ்ப் புதல்வன் திட்டங்களுக்கான தகுதி' : 'Required for Pudhumai Penn & Tamil Pudhalvan (₹1,000/mo)'}
                    </span>
                  </div>
                </label>

                <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={education.seeking_scholarships}
                    onChange={(e) => setEducation({ ...education, seeking_scholarships: e.target.checked })}
                    className="rounded text-healthcare-600 h-4 w-4"
                  />
                  <span className="text-xs font-semibold text-navy-900">
                    {isTa ? 'கல்வி உதவித்தொகை நாடுபவர் (Scholarship Seeker)' : 'Seeking Higher Education Scholarships'}
                  </span>
                </label>
              </div>
            </div>
          )}

          {/* Step 6: Agriculture & Business */}
          {step === 6 && (
            <div className="space-y-4">
              <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={agriculture.owns_agricultural_land}
                  onChange={(e) => setAgriculture({ ...agriculture, owns_agricultural_land: e.target.checked })}
                  className="rounded text-healthcare-600 h-4 w-4"
                />
                <div>
                  <span className="font-semibold text-xs text-navy-900 block">
                    {isTa ? 'விவசாய நிலம் உள்ளது அல்லது உழவர் குடும்பம்' : 'Owns Agricultural Land / Farmer Family'}
                  </span>
                  <span className="text-[11px] text-slate-500">
                    {isTa ? 'PM-KISAN மற்றும் உழவர் நலத்திட்டங்களுக்கான தகுதி' : 'Unlocks PM-KISAN (₹6,000/yr) & State Farmer Security'}
                  </span>
                </div>
              </label>

              {agriculture.owns_agricultural_land && (
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      {isTa ? 'நிலப்பரப்பு (ஏக்கர்)' : 'Total Landholding (in Acres)'}
                    </label>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      value={agriculture.land_acres}
                      onChange={(e) => setAgriculture({ ...agriculture, land_acres: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white"
                    />
                  </div>
                </div>
              )}

              <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={agriculture.has_business}
                  onChange={(e) => setAgriculture({ ...agriculture, has_business: e.target.checked })}
                  className="rounded text-healthcare-600 h-4 w-4"
                />
                <div>
                  <span className="font-semibold text-xs text-navy-900 block">
                    {isTa ? 'சிறு தொழில் / கடை / சுயதொழில் செய்பவர்' : 'Micro-Enterprise / Shop / Self-Employed'}
                  </span>
                  <span className="text-[11px] text-slate-500">
                    {isTa ? 'பிரதமர் முத்ரா பிணையில்லா கடன் திட்டத்திற்கான தகுதி' : 'Unlocks PMMY Mudra collateral-free business loans'}
                  </span>
                </div>
              </label>
            </div>
          )}

          {/* Step 7: Healthcare & Welfare Needs */}
          {step === 7 && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">
                {isTa
                  ? 'நலம் தளம் முதன்மையாக சுகாதார அமைப்பாக இருப்பதால், உங்கள் மருத்துவத் தேவைகளுக்கு முன்னுரிமை அளிக்கப்படும்.'
                  : 'Select your healthcare and medical support interests to prioritize relevant health subsidies.'}
              </p>

              <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={healthcare.needs_health_insurance}
                  onChange={(e) => setHealthcare({ ...healthcare, needs_health_insurance: e.target.checked })}
                  className="rounded text-healthcare-600 h-4 w-4"
                />
                <span className="text-xs font-semibold text-navy-900">
                  {isTa ? 'அரசு மருத்துவக் காப்பீடு (CMCHIS - ₹5 லட்சம் இலவச சிகிச்சை)' : 'Government Health Insurance (CMCHIS / PM-JAY)'}
                </span>
              </label>

              <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={healthcare.needs_maternal_child_care}
                  onChange={(e) => setHealthcare({ ...healthcare, needs_maternal_child_care: e.target.checked })}
                  className="rounded text-healthcare-600 h-4 w-4"
                />
                <span className="text-xs font-semibold text-navy-900">
                  {isTa ? 'மகப்பேறு நிதி உதவி (டாக்டர் முத்துலட்சுமி ரெட்டி திட்டம் - ₹18,000)' : 'Maternity Financial Aid (MRMBS - ₹18,000 + Kits)'}
                </span>
              </label>

              <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={healthcare.needs_disability_support}
                  onChange={(e) => setHealthcare({ ...healthcare, needs_disability_support: e.target.checked })}
                  className="rounded text-healthcare-600 h-4 w-4"
                />
                <span className="text-xs font-semibold text-navy-900">
                  {isTa ? 'மாற்றுத்திறனாளி பராமரிப்பு உதவித்தொகை' : 'Disability Care & Maintenance Allowance'}
                </span>
              </label>

              <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={healthcare.needs_senior_care}
                  onChange={(e) => setHealthcare({ ...healthcare, needs_senior_care: e.target.checked })}
                  className="rounded text-healthcare-600 h-4 w-4"
                />
                <span className="text-xs font-semibold text-navy-900">
                  {isTa ? 'முதியோர் மருத்துவ உதவி & ஓய்வூதியம்' : 'Senior Citizen Healthcare & Pension'}
                </span>
              </label>
            </div>
          )}

          {/* Step 8: Desired Assistance Needs */}
          {step === 8 && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500 mb-2">
                {isTa
                  ? 'நீங்கள் கண்டறிய விரும்பும் அரசு நலத்திட்ட வகைகளைத் தேர்ந்தெடுக்கவும்:'
                  : 'Select the categories of benefits you would like to explore:'}
              </p>

              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'ALL', label_en: 'Show All Eligible', label_ta: 'அனைத்து திட்டங்களும்' },
                  { id: 'HEALTHCARE', label_en: 'Healthcare & Insurance', label_ta: 'மருத்துவக் காப்பீடு' },
                  { id: 'WOMEN_CHILD', label_en: 'Women & Child Welfare', label_ta: 'மகளிர் & குழந்தைகள் நலம்' },
                  { id: 'EDUCATION', label_en: 'Scholarships & Education', label_ta: 'கல்வி உதவித்தொகை' },
                  { id: 'PENSION', label_en: 'Pensions & Senior Aid', label_ta: 'ஓய்வூதியங்கள்' },
                  { id: 'AGRICULTURE', label_en: 'Agriculture & Farm Subsidies', label_ta: 'விவசாய மானியங்கள்' },
                  { id: 'HOUSING', label_en: 'Housing Grants (PMAY)', label_ta: 'வீடு கட்டும் திட்டம்' },
                  { id: 'BUSINESS_LOAN', label_en: 'Business Loans (Mudra)', label_ta: 'சிறு தொழில் கடன்கள்' },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => toggleNeed(item.id)}
                    className={`p-3 rounded-xl border text-xs font-medium text-left transition-all ${
                      needs.includes(item.id)
                        ? 'border-healthcare-600 bg-healthcare-50 text-healthcare-900 font-bold shadow-xs'
                        : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span>{isTa ? item.label_ta : item.label_en}</span>
                      {needs.includes(item.id) && <Check className="w-4 h-4 text-healthcare-600" />}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Wizard Footer Controls */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/80 flex items-center justify-between">
          {step > 1 ? (
            <button
              type="button"
              onClick={() => setStep(step - 1)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-200 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>{isTa ? 'முந்தையது' : 'Previous'}</span>
            </button>
          ) : (
            <div />
          )}

          {step < 8 ? (
            <button
              type="button"
              onClick={() => setStep(step + 1)}
              className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-xs font-bold bg-healthcare-600 text-white hover:bg-healthcare-700 transition-colors shadow-xs"
            >
              <span>{isTa ? 'அடுத்தது' : 'Next'}</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleFinish}
              className="inline-flex items-center gap-1.5 px-6 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors shadow-md disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              <span>{isSubmitting ? (isTa ? 'கணக்கிடுகிறது...' : 'Calculating...') : (isTa ? 'திட்டங்களைக் கண்டறிக' : 'Discover My Schemes')}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
