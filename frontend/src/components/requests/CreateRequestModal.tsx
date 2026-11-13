import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { HealthcareRequest, Medicine, RequestType, Urgency, Facility, HealthCamp } from '../../types';
import { medicineService } from '../../services/medicineService';
import { facilityService } from '../../services/facilityService';
import { campService } from '../../services/campService';
import { requestService } from '../../services/requestService';
import { useAuth } from '../../context/AuthContext';
import { useTranslation } from '../../context/LanguageContext';
import {
  X,
  Send,
  AlertCircle,
  Loader2,
  Stethoscope,
  Pill,
  Tent,
  Activity,
  FlaskConical,
  Building2,
  Landmark,
  CheckCircle2,
  Calendar,
  Phone,
  User as UserIcon,
  Clock,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';

interface CreateRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit?: (data: {
    request_type: RequestType;
    description: string;
    urgency: Urgency;
    title?: string;
    medicine_id?: string;
    facility_id?: string;
    camp_id?: string;
    preferred_date?: string;
    contact_phone?: string;
  }) => Promise<void>;
  onCreated?: (request: HealthcareRequest) => void;
  initialRequestType?: RequestType;
  initialMedicineId?: string;
  preselectedMedicineId?: string;
  initialCampId?: string;
  initialFacilityId?: string;
  initialTitle?: string;
}

export const CreateRequestModal: React.FC<CreateRequestModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  onCreated,
  initialRequestType,
  initialMedicineId,
  preselectedMedicineId,
  initialCampId,
  initialFacilityId,
  initialTitle,
}) => {
  const navigate = useNavigate();
  const { currentPatient, user, isAuthenticated } = useAuth();
  const { t, language } = useTranslation();

  const initMed = initialMedicineId || preselectedMedicineId || '';
  const initType = initialRequestType || (initMed ? 'REFILL' : initialCampId ? 'CAMP_FOLLOWUP' : 'CONSULTATION');

  const [requestType, setRequestType] = useState<RequestType>(initType);
  const [title, setTitle] = useState(initialTitle || '');
  const [description, setDescription] = useState('');
  const [urgency, setUrgency] = useState<Urgency>('NORMAL');
  const [medicineId, setMedicineId] = useState(initMed);
  const [facilityId, setFacilityId] = useState(initialFacilityId || '');
  const [campId, setCampId] = useState(initialCampId || '');
  const [preferredDate, setPreferredDate] = useState('');
  const [contactPhone, setContactPhone] = useState(user?.phone || currentPatient?.emergency_contact_phone || '');

  // Options lists
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [camps, setCamps] = useState<HealthCamp[]>([]);

  // State flags
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdRequest, setCreatedRequest] = useState<HealthcareRequest | null>(null);

  // Sync initial props when opened
  useEffect(() => {
    if (isOpen) {
      setCreatedRequest(null);
      setError(null);

      // Prefill contact phone if available
      if (user?.phone) {
        setContactPhone(user.phone);
      }

      // Initial type and values
      const med = initialMedicineId || preselectedMedicineId || '';
      if (med) {
        setRequestType('REFILL');
        setMedicineId(med);
      } else if (initialCampId) {
        setRequestType('CAMP_FOLLOWUP');
        setCampId(initialCampId);
      } else if (initialRequestType) {
        setRequestType(initialRequestType);
      }

      if (initialFacilityId) setFacilityId(initialFacilityId);
      if (initialTitle) setTitle(initialTitle);

      // Load reference datasets in parallel
      medicineService.getMedicines().then(setMedicines).catch(() => {});
      facilityService.getFacilities().then(setFacilities).catch(() => {});
      campService.getHealthCamps({ limit: 40 }).then((res) => setCamps(res.items || [])).catch(() => {});
    }
  }, [isOpen, initialMedicineId, preselectedMedicineId, initialCampId, initialFacilityId, initialRequestType, initialTitle, user]);

  // Handle Escape key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isSubmitting) {
        handleModalClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, isSubmitting]);

  if (!isOpen) return null;

  const handleModalClose = () => {
    if (isSubmitting) return;
    setError(null);
    setCreatedRequest(null);
    onClose();
  };

  const categories: Array<{
    type: RequestType;
    label: string;
    sublabel: string;
    icon: React.ReactNode;
  }> = [
    {
      type: 'CONSULTATION',
      label: t('reqConsultation', 'Doctor Consultation'),
      sublabel: language === 'ta' ? 'மருத்துவர் ஆலோசனை' : 'Medical doctor consultation',
      icon: <Stethoscope className="w-4 h-4 text-emerald-600" />,
    },
    {
      type: 'REFILL',
      label: t('reqRefill', 'Medicine Refill'),
      sublabel: language === 'ta' ? 'மருந்து மறுநிரப்பல்' : 'Essential drug supply & refill',
      icon: <Pill className="w-4 h-4 text-blue-600" />,
    },
    {
      type: 'CAMP_FOLLOWUP',
      label: t('reqCampFollowup', 'Camp Follow-up Care'),
      sublabel: language === 'ta' ? 'மருத்துவ முகாம் தொடர் சிகிச்சை' : 'Post-camp continuing care & tests',
      icon: <Tent className="w-4 h-4 text-teal-600" />,
    },
    {
      type: 'CHECKUP',
      label: t('reqCheckup', 'Routine Checkup'),
      sublabel: language === 'ta' ? 'வழக்கமான பொது பரிசோதனை' : 'General wellness check',
      icon: <Activity className="w-4 h-4 text-amber-600" />,
    },
    {
      type: 'DIAGNOSTIC',
      label: t('reqDiagnostic', 'Diagnostic Test'),
      sublabel: language === 'ta' ? 'ஆய்வகப் பரிசோதனை' : 'Blood sugar, BP, pathology',
      icon: <FlaskConical className="w-4 h-4 text-purple-600" />,
    },
    {
      type: 'FACILITY_ASSISTANCE',
      label: t('reqFacilityAssistance', 'Facility Assistance'),
      sublabel: language === 'ta' ? 'சுகாதார நிலைய உதவி' : 'PHC/CHC navigation & bed check',
      icon: <Building2 className="w-4 h-4 text-sky-600" />,
    },
    {
      type: 'SCHEME_ASSISTANCE',
      label: t('reqSchemeAssistance', 'Welfare Scheme Aid'),
      sublabel: language === 'ta' ? 'அரசு நலத்திட்ட உதவி' : 'CMCHIS, PM-KISAN, OAP assistance',
      icon: <Landmark className="w-4 h-4 text-indigo-600" />,
    },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // 1. Frontend validation
    const trimmedTitle = title.trim();
    const trimmedDesc = description.trim();

    if (!trimmedTitle) {
      setError(language === 'ta' ? 'தயவுசெய்து கோரிக்கையின் தலைப்பை உள்ளிடவும்.' : 'Please enter a request title or subject.');
      return;
    }

    if (!trimmedDesc) {
      setError(
        language === 'ta'
          ? 'தயவுசெய்து உங்கள் சுகாதாரத் தேவையை விரிவாக விவரிக்கவும்.'
          : 'Please provide details about your symptoms or requested assistance.'
      );
      return;
    }

    if (requestType === 'REFILL' && !medicineId) {
      setError(language === 'ta' ? 'தயவுசெய்து மறுநிரப்ப வேண்டிய மருந்தைத் தேர்ந்தெடுக்கவும்.' : 'Please select the medicine you need refilled.');
      return;
    }

    if (requestType === 'CAMP_FOLLOWUP' && !campId && camps.length > 0) {
      setError(language === 'ta' ? 'தயவுசெய்து தொடர்புடைய மருத்துவ முகாமைத் தேர்ந்தெடுக்கவும்.' : 'Please select the associated health camp.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      if (onSubmit) {
        await onSubmit({
          request_type: requestType,
          title: trimmedTitle,
          description: trimmedDesc,
          urgency,
          medicine_id: requestType === 'REFILL' && medicineId ? medicineId : undefined,
          facility_id: facilityId || undefined,
          camp_id: requestType === 'CAMP_FOLLOWUP' && campId ? campId : undefined,
          preferred_date: preferredDate || undefined,
          contact_phone: contactPhone.trim() || undefined,
        });
        handleModalClose();
      } else {
        // Authenticated patient association
        const patientId = currentPatient?.id || user?.id || 'pat-sample-1';

        const payload = {
          patient_id: patientId,
          request_type: requestType,
          title: trimmedTitle,
          description: trimmedDesc,
          urgency,
          medicine_id: requestType === 'REFILL' && medicineId ? medicineId : undefined,
          facility_id: facilityId || undefined,
          camp_id: requestType === 'CAMP_FOLLOWUP' && campId ? campId : undefined,
          preferred_date: preferredDate || undefined,
          contact_phone: contactPhone.trim() || undefined,
        };

        const newReq = await requestService.createRequest(payload);
        setCreatedRequest(newReq);

        if (onCreated) {
          onCreated(newReq);
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('errorTitle', 'Failed to submit healthcare request');
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Min date for preferred date picker is today
  const todayStr = new Date().toISOString().split('T')[0];

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs p-3 sm:p-6 flex items-start sm:items-center justify-center min-h-screen"
      onClick={handleModalClose}
      role="presentation"
    >
      <div
        className="relative w-full max-w-xl max-h-[90vh] flex flex-col bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden my-auto animate-in fade-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-request-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Fixed Header */}
        <div className="shrink-0 bg-gradient-to-r from-emerald-800 to-teal-900 p-5 sm:p-6 text-white relative">
          <button
            onClick={handleModalClose}
            disabled={isSubmitting}
            className="absolute top-4 right-4 p-2 text-emerald-100 hover:text-white hover:bg-white/10 rounded-full transition-colors disabled:opacity-50"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex flex-wrap items-center gap-2 mb-2 pr-8">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/30 text-emerald-100 border border-emerald-400/30 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-300" />
              {language === 'ta' ? 'நலம் AI நேரடிச் சேவை' : 'NALAM AI Care Coordination'}
            </span>
            {user?.name && (
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-white/20 text-white backdrop-blur-xs flex items-center gap-1">
                <UserIcon className="w-3 h-3 text-emerald-200" />
                {user.name}
              </span>
            )}
          </div>

          <h2 id="create-request-modal-title" className="text-lg sm:text-xl font-bold leading-snug">
            {language === 'ta' ? 'புதிய மருத்துவக் கோரிக்கை உருவாக்கு' : 'Create New Healthcare Request'}
          </h2>
          <p className="text-emerald-100 text-xs mt-1">
            {language === 'ta'
              ? 'உங்கள் தேவையைப் பதிவுசெய்க. அருகிலுள்ள சுகாதார நிலையங்கள் மற்றும் மருந்துகள் உடனடியாக ஆய்வு செய்யப்படும்.'
              : 'Submit a verified request for clinical consultation, medicine refill, or health camp follow-up.'}
          </p>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-5">
          {/* SUCCESS SCREEN */}
          {createdRequest ? (
            <div className="py-6 text-center space-y-4 animate-in fade-in zoom-in-95 duration-200">
              <div className="w-16 h-16 mx-auto rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shadow-inner">
                <CheckCircle2 className="w-9 h-9" />
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  {language === 'ta' ? 'கோரிக்கை வெற்றிகரமாகச் சமர்ப்பிக்கப்பட்டது!' : 'Healthcare Request Created Successfully!'}
                </h3>
                <p className="text-xs text-slate-600 mt-1 max-w-md mx-auto">
                  {language === 'ta'
                    ? 'உங்கள் கோரிக்கை நலம் AI தரவுத்தளத்தில் சேமிக்கப்பட்டு வரிசைப்படுத்தப்பட்டுள்ளது.'
                    : 'Your request has been verified and registered in the NALAM AI queue for care routing.'}
                </p>
              </div>

              {/* Request Details Box */}
              <div className="max-w-md mx-auto p-4 rounded-xl bg-slate-50 border border-slate-200 text-left text-xs space-y-2.5">
                <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                  <span className="text-slate-500 font-medium">Request ID:</span>
                  <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                    #{createdRequest.id.length > 12 ? createdRequest.id.slice(0, 8) : createdRequest.id}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Subject:</span>
                  <span className="font-semibold text-slate-900">{createdRequest.title || title}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Category:</span>
                  <span className="font-semibold text-slate-900">{createdRequest.request_type}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Status:</span>
                  <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-amber-100 text-amber-800 border border-amber-200">
                    {createdRequest.status || 'PENDING'}
                  </span>
                </div>
                {createdRequest.preferred_date && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-medium">Target Date:</span>
                    <span className="font-semibold text-slate-800">{createdRequest.preferred_date}</span>
                  </div>
                )}
              </div>

              <div className="pt-3 flex flex-wrap items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={handleModalClose}
                  className="px-5 py-2.5 text-xs font-semibold rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 transition-colors shadow-sm"
                >
                  {language === 'ta' ? 'முடிந்தது / முகப்பிற்குத் திரும்புக' : 'Done / Return to Dashboard'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    handleModalClose();
                    navigate('/requests');
                  }}
                  className="px-4 py-2.5 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors flex items-center gap-1.5"
                >
                  <span>{language === 'ta' ? 'கோரிக்கைகளைக் காண்க' : 'View in Requests Directory'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ) : (
            /* FORM SCREEN */
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2.5 animate-in fade-in">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <strong className="block font-semibold">
                      {language === 'ta' ? 'கோரிக்கை பதிவு பிழை:' : 'Submission Error:'}
                    </strong>
                    <span>{error}</span>
                  </div>
                </div>
              )}

              {/* 1. Request Category Selector */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  {language === 'ta' ? '1. கோரிக்கை வகை' : '1. Request Category'}
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {categories.map((cat) => {
                    const isSelected = requestType === cat.type;
                    return (
                      <button
                        key={cat.type}
                        type="button"
                        onClick={() => {
                          setRequestType(cat.type);
                          if (!title) {
                            setTitle(cat.label);
                          }
                        }}
                        className={`p-2.5 rounded-xl border text-left transition-all flex items-start gap-2.5 ${
                          isSelected
                            ? 'border-emerald-600 bg-emerald-50/80 ring-1 ring-emerald-500 shadow-xs'
                            : 'border-slate-200 bg-white hover:bg-slate-50'
                        }`}
                      >
                        <span className="p-1 rounded-lg bg-white border border-slate-200 shadow-2xs mt-0.5 shrink-0">
                          {cat.icon}
                        </span>
                        <div className="min-w-0">
                          <p className={`text-xs font-bold ${isSelected ? 'text-emerald-950' : 'text-slate-800'}`}>
                            {cat.label}
                          </p>
                          <p className="text-[11px] text-slate-500 truncate">{cat.sublabel}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 2. Request Subject / Title */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  {language === 'ta' ? '2. கோரிக்கையின் தலைப்பு *' : '2. Request Subject / Title *'}
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder={
                    requestType === 'REFILL'
                      ? 'e.g. Monthly Metformin and Amlodipine Refill'
                      : requestType === 'CAMP_FOLLOWUP'
                      ? 'e.g. Salem Eye Camp Follow-up Consultation'
                      : 'e.g. Persistent fever and body pain since 2 days'
                  }
                  className="w-full text-xs rounded-xl border border-slate-300 p-2.5 text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 bg-white"
                />
              </div>

              {/* 3. Conditional Fields based on Request Type */}
              {/* Conditional: Medicine Selection if REFILL */}
              {requestType === 'REFILL' && (
                <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl space-y-2">
                  <label className="block text-xs font-bold text-blue-900 flex items-center gap-1.5">
                    <Pill className="w-3.5 h-3.5 text-blue-700" />
                    {language === 'ta' ? 'தேவையான அத்தியாவசிய மருந்து *' : 'Select Essential Medicine *'}
                  </label>
                  <select
                    value={medicineId}
                    onChange={(e) => setMedicineId(e.target.value)}
                    required
                    className="w-full text-xs rounded-lg border border-blue-300 p-2.5 bg-white text-slate-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="">{t('selectMedicinePlaceholder', 'Select from essential medicine list...')}</option>
                    {medicines.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.code}) — {m.category}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Conditional: Camp Selection if CAMP_FOLLOWUP */}
              {requestType === 'CAMP_FOLLOWUP' && (
                <div className="p-3.5 bg-teal-50/70 border border-teal-200 rounded-xl space-y-2">
                  <label className="block text-xs font-bold text-teal-900 flex items-center gap-1.5">
                    <Tent className="w-3.5 h-3.5 text-teal-700" />
                    {language === 'ta' ? 'தொடர்புடைய மருத்துவ முகாம் *' : 'Associated Tamil Nadu Health Camp *'}
                  </label>
                  <select
                    value={campId}
                    onChange={(e) => setCampId(e.target.value)}
                    required
                    className="w-full text-xs rounded-lg border border-teal-300 p-2.5 bg-white text-slate-900 focus:border-teal-500 focus:ring-1 focus:ring-teal-500"
                  >
                    <option value="">
                      {language === 'ta' ? 'அங்கீகரிக்கப்பட்ட முகாமைத் தேர்ந்தெடுக்கவும்...' : 'Select verified health camp...'}
                    </option>
                    {camps.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.title} ({c.district} — {c.venue_name})
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-teal-700">
                    {language === 'ta'
                      ? 'முகாமில் கலந்துகொண்டதற்கான தொடர் சிகிச்சை அல்லது அறிக்கை பரிசீலனை.'
                      : 'Links your request to the camp roster for PHC continuation token issuance.'}
                  </p>
                </div>
              )}

              {/* Conditional: Healthcare Facility (Optional for Consultation/Checkup/Facility assistance) */}
              {(requestType === 'CONSULTATION' ||
                requestType === 'CHECKUP' ||
                requestType === 'DIAGNOSTIC' ||
                requestType === 'FACILITY_ASSISTANCE') && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <Building2 className="w-3.5 h-3.5 text-slate-500" />
                      {language === 'ta' ? 'விருப்பமான சுகாதார நிலையம் (விருப்பத்தேர்வு)' : 'Preferred Facility (Optional)'}
                    </span>
                    <span className="text-[10px] text-slate-400 font-normal">Auto-assigned if left blank</span>
                  </label>
                  <select
                    value={facilityId}
                    onChange={(e) => setFacilityId(e.target.value)}
                    className="w-full text-xs rounded-xl border border-slate-300 p-2.5 bg-white text-slate-900 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                  >
                    <option value="">
                      {language === 'ta' ? 'அருகிலுள்ள சிறந்த மையத்தை NALAM AI தேர்ந்தெடுக்கட்டும்' : 'Auto-match closest facility with verified stock'}
                    </option>
                    {facilities.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name} ({f.facility_type || 'PHC'}) — {f.district || f.subdistrict || ''}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* 4. Detailed Description */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  {language === 'ta' ? '3. விரிவான அறிகுறிகள் அல்லது தேவை விவரம் *' : '3. Symptoms & Request Details *'}
                </label>
                <textarea
                  rows={3}
                  required
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={
                    language === 'ta'
                      ? 'எ.கா: சர்க்கரை நோய் மருந்துகள் தீர்ந்துவிட்டன, அல்லது 2 நாட்களாக காய்ச்சல் மற்றும் தொண்டை வலி உள்ளது...'
                      : 'Describe symptoms, duration, dosage needed, or special assistance requirements in detail...'
                  }
                  className="w-full text-xs rounded-xl border border-slate-300 p-3 text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 leading-relaxed bg-white"
                />
              </div>

              {/* 5. Priority / Urgency Level */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center justify-between">
                  <span>{language === 'ta' ? '4. அவசர நிலை' : '4. Priority Level'}</span>
                  <span className="text-[10px] text-slate-400 font-normal">Triage guidance</span>
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    {
                      val: 'NORMAL',
                      label: language === 'ta' ? 'இயல்பு' : 'Routine (Normal)',
                      desc: language === 'ta' ? 'வழக்கமான பராமரிப்பு' : 'Routine care',
                      color: 'border-emerald-600 bg-emerald-50 text-emerald-950 font-bold',
                    },
                    {
                      val: 'PRIORITY',
                      label: language === 'ta' ? 'முன்னுரிமை' : 'Priority (1-2 days)',
                      desc: language === 'ta' ? 'விரைவு கவனிப்பு' : 'Needs attention',
                      color: 'border-amber-600 bg-amber-50 text-amber-950 font-bold',
                    },
                    {
                      val: 'URGENT',
                      label: language === 'ta' ? 'அவசரம்' : 'Urgent (Today)',
                      desc: language === 'ta' ? 'இன்றே தேவை' : 'Immediate routing',
                      color: 'border-rose-600 bg-rose-50 text-rose-950 font-bold',
                    },
                  ].map((u) => (
                    <button
                      key={u.val}
                      type="button"
                      onClick={() => setUrgency(u.val as Urgency)}
                      className={`p-2 rounded-xl border text-center transition-all ${
                        urgency === u.val
                          ? `${u.color} shadow-xs`
                          : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <p className="text-xs font-bold">{u.label}</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">{u.desc}</p>
                    </button>
                  ))}
                </div>
                <p className="mt-1 text-[11px] text-slate-400 italic">
                  {language === 'ta'
                    ? 'குறிப்பு: அவசர சிகிச்சைக்கு உடனடி உதவி எண் 108 ஐத் தொடர்பு கொள்ளவும்.'
                    : 'Note: Priority selection guides administrative routing. For life-threatening emergencies, dial 108.'}
                </p>
              </div>

              {/* 6. Contact Phone & Preferred Date Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 border-t border-slate-100">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-slate-500" />
                    {language === 'ta' ? 'தொடர்பு தொலைபேசி எண்' : 'Contact Phone'}
                  </label>
                  <input
                    type="tel"
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    placeholder="10-digit mobile number"
                    className="w-full text-xs rounded-xl border border-slate-300 p-2.5 text-slate-900 bg-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    {language === 'ta' ? 'விருப்பமான தேதி (விருப்பத்தேர்வு)' : 'Preferred Date (Optional)'}
                  </label>
                  <input
                    type="date"
                    min={todayStr}
                    value={preferredDate}
                    onChange={(e) => setPreferredDate(e.target.value)}
                    className="w-full text-xs rounded-xl border border-slate-300 p-2.5 text-slate-900 bg-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                  />
                </div>
              </div>

              {/* Modal Buttons */}
              <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={handleModalClose}
                  disabled={isSubmitting}
                  className="px-4 py-2.5 text-xs font-semibold text-slate-600 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors disabled:opacity-50"
                >
                  {t('cancel', 'Cancel')}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2.5 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-xl transition-all shadow-sm flex items-center gap-2 disabled:opacity-50 cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>{language === 'ta' ? 'பதிவு செய்யப்படுகிறது...' : 'Submitting to Queue...'}</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      <span>{language === 'ta' ? 'கோரிக்கையைச் சமர்ப்பி' : 'Submit Healthcare Request'}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
