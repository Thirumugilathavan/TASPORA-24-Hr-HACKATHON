import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  Calendar,
  Clock,
  MapPin,
  Building2,
  Phone,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  HeartHandshake,
  Navigation,
  FileText,
  Info,
  Send,
  Loader2,
  User as UserIcon,
  LogIn,
  History,
  ArrowRight,
  AlertCircle,
} from 'lucide-react';
import { HealthCamp, HealthcareRequest, Urgency } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useTranslation } from '../../context/LanguageContext';
import { requestService } from '../../services/requestService';

interface CampDetailModalProps {
  camp: HealthCamp | null;
  onClose: () => void;
  onRequestCreated?: (request: HealthcareRequest) => void;
}

export const CampDetailModal: React.FC<CampDetailModalProps> = ({
  camp,
  onClose,
  onRequestCreated,
}) => {
  const navigate = useNavigate();
  const { user, currentPatient, isAuthenticated } = useAuth();
  const { t, language } = useTranslation();

  // Follow-up form state
  const [activeTab, setActiveTab] = useState<'details' | 'followup'>('details');
  const [followupSubject, setFollowupSubject] = useState('');
  const [followupDescription, setFollowupDescription] = useState('');
  const [followupUrgency, setFollowupUrgency] = useState<Urgency>('NORMAL');
  const [preferredDate, setPreferredDate] = useState('');
  const [contactPhone, setContactPhone] = useState(user?.phone || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccessReq, setFormSuccessReq] = useState<HealthcareRequest | null>(null);

  // Existing camp-linked requests for this user
  const [existingRequests, setExistingRequests] = useState<HealthcareRequest[]>([]);
  const [loadingExisting, setLoadingExisting] = useState(false);

  // Initialize and reset when camp changes
  useEffect(() => {
    if (camp) {
      setFormError(null);
      setFormSuccessReq(null);
      setFollowupSubject(`Follow-up: ${camp.title}`);
      setFollowupDescription('');
      setFollowupUrgency('NORMAL');
      setPreferredDate('');
      setContactPhone(user?.phone || '');
      setActiveTab('details');

      // Load existing requests linked to this camp if user logged in
      if (isAuthenticated) {
        setLoadingExisting(true);
        requestService
          .getRequests()
          .then((reqs: HealthcareRequest[]) => setExistingRequests((reqs || []).filter((r) => r.camp_id === camp.id)))
          .catch(() => setExistingRequests([]))
          .finally(() => setLoadingExisting(false));
      } else {
        setExistingRequests([]);
      }
    }
  }, [camp, isAuthenticated, user]);

  // Handle Escape key & body overflow lock
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && camp && !isSubmitting) {
        onClose();
      }
    };
    if (camp) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [camp, isSubmitting, onClose]);

  if (!camp) return null;

  // Event status evaluation
  const campDate = new Date(camp.end_date || camp.start_date);
  const isPastEvent = !isNaN(campDate.getTime()) && campDate.getTime() < Date.now();

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'MOBILE_MEDICAL_UNIT':
        return language === 'ta' ? 'நடமாடும் மருத்துவ ஊர்தி' : 'Mobile Medical Unit (Hospital on Wheels)';
      case 'NCD_SCREENING':
        return language === 'ta' ? 'தொற்றா நோய் பரிசோதனை' : 'NCD & Chronic Care Screening';
      case 'EYE_CAMP':
        return language === 'ta' ? 'கண் மருத்துவ முகாம்' : 'Specialist Eye & Cataract Camp';
      case 'MATERNAL_CHILD_HEALTH':
        return language === 'ta' ? 'தாய்-சேய் நல முகாம்' : 'Maternal & Child Health';
      case 'VACCINATION_DRIVE':
        return language === 'ta' ? 'தடுப்பூசி முகாம்' : 'Public Immunization Session';
      case 'SPECIALIST_OUTREACH':
        return language === 'ta' ? 'சிறப்பு மருத்துவ முகாம்' : 'Specialist Medical Outreach';
      default:
        return language === 'ta' ? 'பொது மருத்துவ முகாம்' : 'General Health Camp';
    }
  };

  const directionsUrl =
    camp.latitude && camp.longitude
      ? `https://www.google.com/maps/dir/?api=1&destination=${camp.latitude},${camp.longitude}`
      : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
          `${camp.venue_name}, ${camp.district}, Tamil Nadu`
        )}`;

  const handleSubmitFollowup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!followupDescription.trim()) {
      setFormError(
        language === 'ta'
          ? 'தயவுசெய்து உங்கள் தொடர் சிகிச்சைத் தேவையை விவரிக்கவும்.'
          : 'Please provide details of your symptoms or continuing care requirement.'
      );
      return;
    }

    if (!isAuthenticated) {
      setFormError(
        language === 'ta'
          ? 'தொடர் சிகிச்சைக் கோரிக்கையைப் பதிவு செய்ய தயவுசெய்து உள்நுழையவும்.'
          : 'Please sign in to submit a verified follow-up request linked to your profile.'
      );
      return;
    }

    setIsSubmitting(true);
    setFormError(null);

    try {
      const patientId = currentPatient?.id || user?.id || 'pat-sample-1';
      const payload = {
        patient_id: patientId,
        request_type: 'CAMP_FOLLOWUP',
        title: followupSubject.trim() || `Follow-up: ${camp.title}`,
        camp_id: camp.id,
        description: followupDescription.trim(),
        urgency: followupUrgency,
        preferred_date: preferredDate || undefined,
        contact_phone: contactPhone.trim() || undefined,
        extra_metadata: JSON.stringify({
          camp_title: camp.title,
          camp_district: camp.district,
          camp_venue: camp.venue_name,
          source_org: camp.source_org,
        }),
      };

      const newReq = await requestService.createRequest(payload);
      setFormSuccessReq(newReq);
      setExistingRequests((prev) => [newReq, ...prev]);

      if (onRequestCreated) {
        onRequestCreated(newReq);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit follow-up request. Please retry.';
      setFormError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const todayStr = new Date().toISOString().split('T')[0];

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs p-3 sm:p-6 md:p-8 flex items-start sm:items-center justify-center min-h-screen"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="relative w-full max-w-2xl max-h-[90vh] flex flex-col bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden my-auto animate-in fade-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
        aria-labelledby="camp-detail-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Fixed Header (Never shrunk, never clipped) */}
        <div className="shrink-0 bg-gradient-to-r from-emerald-800 to-teal-900 p-5 sm:p-6 text-white relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 text-emerald-100 hover:text-white hover:bg-white/10 rounded-full transition-colors focus:outline-hidden focus:ring-2 focus:ring-white"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Badges Row */}
          <div className="flex flex-wrap items-center gap-2 mb-2 pr-10">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/30 text-emerald-100 border border-emerald-400/30">
              {getCategoryLabel(camp.category)}
            </span>

            {/* Event Status: Past vs Upcoming */}
            {isPastEvent ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-700/80 text-slate-200 border border-slate-500">
                <Clock className="w-3.5 h-3.5 text-slate-300" />
                {language === 'ta' ? 'முடிவடைந்த முகாம்' : 'Past Event (Completed)'}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-400 text-emerald-950">
                <Calendar className="w-3.5 h-3.5" />
                {language === 'ta' ? 'வரவிருக்கும் முகாம்' : 'Upcoming Event'}
              </span>
            )}

            {/* Government Verification */}
            {camp.verification_status === 'VERIFIED' ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-400 text-teal-950">
                <ShieldCheck className="w-3.5 h-3.5" />
                {language === 'ta' ? 'அரசு அறிவிப்பு' : 'Verified Notice'}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-400 text-amber-950">
                <AlertTriangle className="w-3.5 h-3.5" />
                {language === 'ta' ? 'சரிபார்க்கப்படாத தகவல்' : 'Unverified'}
              </span>
            )}

            {camp.distance_km !== undefined && camp.distance_km !== null && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white/20 text-white backdrop-blur-xs">
                {camp.distance_km.toFixed(1)} km away
              </span>
            )}
          </div>

          <h2 id="camp-detail-title" className="text-lg sm:text-xl font-bold leading-snug pr-8">
            {camp.title}
          </h2>
          <p className="text-emerald-100 text-xs mt-1 flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 shrink-0" />
            {camp.organizing_dept}
          </p>

          {/* Navigation Tabs between Overview and Follow-up */}
          <div className="flex items-center gap-2 mt-4 pt-3 border-t border-emerald-700/60">
            <button
              type="button"
              onClick={() => setActiveTab('details')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'details'
                  ? 'bg-white text-emerald-900 shadow-xs'
                  : 'text-emerald-100 hover:bg-white/10'
              }`}
            >
              {language === 'ta' ? 'முகாம் விவரங்கள்' : 'Camp Details & Venue'}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('followup')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'followup'
                  ? 'bg-white text-emerald-900 shadow-xs'
                  : 'text-emerald-100 hover:bg-white/10'
              }`}
            >
              <HeartHandshake className="w-3.5 h-3.5" />
              <span>{language === 'ta' ? 'தொடர் சிகிச்சை & உதவி' : 'Details & Follow-up'}</span>
              {existingRequests.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-700 text-white font-bold">
                  {existingRequests.length}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Scrollable Modal Content */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6">
          {/* TAB 1: CAMP DETAILS */}
          {activeTab === 'details' && (
            <div className="space-y-6 animate-in fade-in duration-150">
              {/* Past Event Banner if Expired */}
              {isPastEvent && (
                <div className="p-3.5 rounded-xl bg-slate-100 border border-slate-300 text-slate-800 text-xs flex items-start gap-2.5">
                  <Clock className="w-4 h-4 text-slate-600 shrink-0 mt-0.5" />
                  <div>
                    <strong className="block font-semibold">
                      {language === 'ta' ? 'இந்த முகாம் நிறைவடைந்தது' : 'Notice: This health camp has concluded'}
                    </strong>
                    <p className="mt-0.5 text-slate-600">
                      {language === 'ta'
                        ? 'முகாமிற்கான நேரடி முன்பதிவு முடிந்தது. முகாமில் கலந்துகொண்ட நோயாளிகள் தங்கள் தொடர் சிகிச்சை அல்லது மருந்துத் தேவைக்கு "தொடர் சிகிச்சை & உதவி" பிரிவில் கோரிக்கையைச் சமர்ப்பிக்கலாம்.'
                        : 'Pre-event registration is closed. If you attended this camp and require continuation care, lab report review, or medicine refill, switch to the Follow-up tab to submit a request.'}
                    </p>
                  </div>
                </div>
              )}

              {/* Key Schedule & Venue Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm">
                <div className="space-y-1">
                  <span className="text-xs font-medium text-slate-500 flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-emerald-700" /> Date & Day
                  </span>
                  <p className="font-semibold text-slate-900">{formatDate(camp.start_date)}</p>
                  {camp.end_date && camp.end_date !== camp.start_date && (
                    <p className="text-xs text-slate-500">to {formatDate(camp.end_date)}</p>
                  )}
                </div>

                <div className="space-y-1">
                  <span className="text-xs font-medium text-slate-500 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-emerald-700" /> Timing
                  </span>
                  <p className="font-semibold text-slate-900">
                    {formatTime(camp.start_date) || '09:00 AM onwards'}
                    {camp.end_date && ` - ${formatTime(camp.end_date)}`}
                  </p>
                  <p className="text-[11px] text-slate-500">Subject to token availability</p>
                </div>

                <div className="space-y-1 md:col-span-2 pt-2 border-t border-slate-200">
                  <span className="text-xs font-medium text-slate-500 flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-emerald-700" /> Venue & Official Location
                  </span>
                  <p className="font-semibold text-slate-900">{camp.venue_name}</p>
                  <p className="text-xs text-slate-600">{camp.full_address}</p>
                  <p className="text-xs text-slate-500">
                    District: <strong className="text-slate-700">{camp.district}</strong>
                    {camp.taluk && ` • Taluk: ${camp.taluk}`}
                    {camp.village && ` • Village: ${camp.village}`}
                  </p>

                  <div className="pt-2 flex items-center gap-3">
                    <a
                      href={directionsUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200 transition-colors"
                    >
                      <Navigation className="w-3.5 h-3.5 text-emerald-600" />
                      Get Driving Directions
                    </a>
                    {camp.contact_info && (
                      <a
                        href={`tel:${camp.contact_info.replace(/[^0-9+]/g, '')}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200 transition-colors"
                      >
                        <Phone className="w-3.5 h-3.5 text-slate-600" />
                        Call {camp.contact_info}
                      </a>
                    )}
                  </div>
                </div>
              </div>

              {/* Description */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Official Camp Overview
                </h3>
                <p className="text-xs sm:text-sm text-slate-700 leading-relaxed bg-white border border-slate-100 p-3.5 rounded-xl shadow-2xs">
                  {camp.description}
                </p>
              </div>

              {/* Services Offered */}
              {camp.services_offered && camp.services_offered.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    Services Offered Free of Cost
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {camp.services_offered.map((svc, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-2 p-2.5 rounded-lg bg-emerald-50/70 border border-emerald-100 text-xs text-emerald-950 font-medium"
                      >
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                        <span>{svc}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Eligibility & Instructions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                {camp.eligibility && (
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="font-bold text-slate-700 block mb-1">Target Beneficiaries & Eligibility</span>
                    <p className="text-slate-600 leading-relaxed">{camp.eligibility}</p>
                  </div>
                )}

                {camp.registration_instructions && (
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="font-bold text-slate-700 block mb-1">Registration & Token Process</span>
                    <p className="text-slate-600 leading-relaxed">{camp.registration_instructions}</p>
                  </div>
                )}
              </div>

              {/* Follow-up Care Banner with Action Switch */}
              <div className="p-4 rounded-xl bg-teal-50 border border-teal-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-teal-900 font-bold text-sm">
                    <HeartHandshake className="w-4 h-4 text-teal-700" />
                    <span>Continuing Care & Post-Camp Referral</span>
                  </div>
                  <p className="text-xs text-teal-800 leading-relaxed">
                    {camp.followup_instructions ||
                      'Patients requiring continuing medication or specialist review can register for follow-up token coordination.'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('followup')}
                  className="px-4 py-2 text-xs font-bold rounded-lg bg-teal-700 text-white hover:bg-teal-800 transition-colors shrink-0 shadow-xs flex items-center gap-1.5"
                >
                  <span>Submit Follow-up</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Official Source Audit */}
              <div className="p-3.5 rounded-xl bg-slate-100 border border-slate-200 text-xs text-slate-600 space-y-1.5">
                <div className="flex items-center justify-between text-slate-700 font-semibold">
                  <span className="flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-slate-500" /> Official Government Provenance
                  </span>
                  <span className="text-[11px] text-slate-500">
                    Discovered: {new Date(camp.discovered_at).toLocaleDateString()}
                  </span>
                </div>
                <p>
                  <strong className="text-slate-700">Publishing Authority:</strong> {camp.source_org}
                </p>
                <p className="break-all">
                  <strong className="text-slate-700">Official Source Notice:</strong>{' '}
                  <a
                    href={camp.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-emerald-700 hover:underline inline-flex items-center gap-1 font-medium"
                  >
                    View Official Publication <ExternalLink className="w-3 h-3" />
                  </a>
                </p>
              </div>
            </div>
          )}

          {/* TAB 2: FUNCTIONAL FOLLOW-UP WORKFLOW */}
          {activeTab === 'followup' && (
            <div className="space-y-5 animate-in fade-in duration-150">
              {/* Context Banner */}
              <div className="p-4 rounded-xl bg-teal-50 border border-teal-200">
                <div className="flex items-center gap-2 mb-1 text-teal-950 font-bold text-sm">
                  <HeartHandshake className="w-4 h-4 text-teal-700" />
                  <span>
                    {language === 'ta'
                      ? 'மருத்துவ முகாம் தொடர் சிகிச்சை மற்றும் மருந்து உதவி'
                      : 'Health Camp Follow-up & Continuing Care Assistance'}
                  </span>
                </div>
                <p className="text-xs text-teal-800 leading-relaxed">
                  {language === 'ta'
                    ? 'இந்த முகாமில் பங்கேற்ற நோயாளிகள் தங்களின் மருந்து மறுநிரப்பல், ஆய்வகப் பரிசோதனை அல்லது தொடர் ஆலோசனைக்கான உதவி கோரிக்கையை இங்கு சமர்ப்பிக்கலாம். அருகிலுள்ள PHC/CHC மையத்துடன் இணைக்கப்படும்.'
                    : 'Submit a verified request for continuing medication, specialist referral, or lab report evaluation following this health camp. NALAM AI links your request directly to your nearest Primary Health Centre.'}
                </p>
              </div>

              {/* Existing Linked Requests for This Camp */}
              {isAuthenticated && existingRequests.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <History className="w-3.5 h-3.5 text-emerald-700" />
                      {language === 'ta' ? 'உங்கள் செயலில் உள்ள தொடர் கோரிக்கைகள்' : 'Your Active Follow-up Requests for this Camp'}
                    </span>
                    <span className="text-[11px] text-slate-500">{existingRequests.length} recorded</span>
                  </div>

                  <div className="space-y-2">
                    {existingRequests.map((req) => (
                      <div
                        key={req.id}
                        className="p-3.5 rounded-xl border border-emerald-200 bg-emerald-50/50 text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-emerald-200">
                            #{req.id.length > 12 ? req.id.slice(0, 8) : req.id}
                          </span>
                          <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-amber-100 text-amber-800 border border-amber-200">
                            {req.status}
                          </span>
                        </div>
                        <p className="font-semibold text-slate-900">{req.title || 'Follow-up Request'}</p>
                        <p className="text-slate-600 line-clamp-2">{req.description}</p>
                        <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-emerald-100">
                          <span>Urgency: <strong className="text-slate-700">{req.urgency}</strong></span>
                          <span>Submitted: {new Date(req.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Authentication Guard */}
              {!isAuthenticated ? (
                <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-3">
                  <div className="w-12 h-12 mx-auto rounded-full bg-slate-200 text-slate-600 flex items-center justify-center">
                    <LogIn className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">
                      {language === 'ta' ? 'தொடர் சிகிச்சைக்கு உள்நுழைவு தேவை' : 'Authentication Required for Follow-up'}
                    </h4>
                    <p className="text-xs text-slate-600 mt-1 max-w-sm mx-auto">
                      {language === 'ta'
                        ? 'உங்கள் மருத்துவ வரலாற்றுடன் தொடர் சிகிச்சை கோரிக்கையை இணைக்க தயவுசெய்து உள்நுழையவும்.'
                        : 'Sign in to associate continuing medical care with your verified patient profile and track token issuance.'}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      onClose();
                      navigate('/login');
                    }}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 transition-colors shadow-sm"
                  >
                    <LogIn className="w-3.5 h-3.5" />
                    <span>{language === 'ta' ? 'உள்நுழைக' : 'Sign In to Continue'}</span>
                  </button>
                </div>
              ) : formSuccessReq ? (
                /* Successful Submission Message */
                <div className="p-5 rounded-2xl bg-emerald-50 border border-emerald-200 text-center space-y-3 animate-in fade-in">
                  <div className="w-12 h-12 mx-auto rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                    <CheckCircle2 className="w-7 h-7" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-emerald-950">
                      {language === 'ta'
                        ? 'தொடர் சிகிச்சைக் கோரிக்கை பதிவு செய்யப்பட்டது!'
                        : 'Follow-up Request Submitted Successfully!'}
                    </h4>
                    <p className="text-xs text-emerald-800 mt-1">
                      {language === 'ta'
                        ? 'கோரிக்கை எண்: #' + (formSuccessReq.id.length > 12 ? formSuccessReq.id.slice(0, 8) : formSuccessReq.id)
                        : `Request Reference ID: #${formSuccessReq.id}`}
                    </p>
                    <p className="text-[11px] text-emerald-700 mt-1">
                      Your follow-up care token has been placed in the Primary Health Centre coordination queue.
                    </p>
                  </div>
                  <div className="pt-2 flex justify-center gap-2">
                    <button
                      type="button"
                      onClick={() => setFormSuccessReq(null)}
                      className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 transition-colors"
                    >
                      {language === 'ta' ? 'மற்றொரு கோரிக்கை சமர்ப்பி' : 'Submit Another Request'}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        onClose();
                        navigate('/requests');
                      }}
                      className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-white border border-emerald-300 text-emerald-800 hover:bg-emerald-100 transition-colors"
                    >
                      {language === 'ta' ? 'கோரிக்கையைக் காண்க' : 'View in Requests'}
                    </button>
                  </div>
                </div>
              ) : (
                /* Submit Follow-up Request Form */
                <form onSubmit={handleSubmitFollowup} className="p-4 rounded-xl bg-white border border-slate-200 space-y-4">
                  {formError && (
                    <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                      <span>{formError}</span>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      {language === 'ta' ? 'கோரிக்கையின் தலைப்பு *' : 'Follow-up Subject *'}
                    </label>
                    <input
                      type="text"
                      required
                      value={followupSubject}
                      onChange={(e) => setFollowupSubject(e.target.value)}
                      placeholder="e.g. Post-camp blood sugar report review"
                      className="w-full text-xs rounded-xl border border-slate-300 p-2.5 text-slate-900 bg-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      {language === 'ta' ? 'அறிகுறிகள் அல்லது தேவையான உதவி *' : 'Detailed Follow-up Need *'}
                    </label>
                    <textarea
                      rows={3}
                      required
                      value={followupDescription}
                      onChange={(e) => setFollowupDescription(e.target.value)}
                      placeholder={
                        language === 'ta'
                          ? 'முகாமில் கலந்து கொண்ட பிறகு மருத்துவர் பரிந்துரைத்த பரிசோதனை அல்லது மருந்து விவரங்கள்...'
                          : 'Describe any continuing symptoms, medication prescribed during the camp, or referral letter details...'
                      }
                      className="w-full text-xs rounded-xl border border-slate-300 p-3 text-slate-900 bg-white placeholder-slate-400 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 leading-relaxed"
                    />
                  </div>

                  {/* Urgency Selection */}
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      {language === 'ta' ? 'அவசர நிலை' : 'Urgency Level'}
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { val: 'NORMAL', label: 'Routine (Normal)' },
                        { val: 'PRIORITY', label: 'Priority (1-2 days)' },
                        { val: 'URGENT', label: 'Urgent (Today)' },
                      ].map((u) => (
                        <button
                          key={u.val}
                          type="button"
                          onClick={() => setFollowupUrgency(u.val as Urgency)}
                          className={`p-2 rounded-lg border text-center text-xs font-semibold transition-all ${
                            followupUrgency === u.val
                              ? 'border-emerald-600 bg-emerald-50 text-emerald-950 font-bold'
                              : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                          }`}
                        >
                          {u.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Phone & Date Row */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center gap-1.5">
                        <Phone className="w-3.5 h-3.5 text-slate-500" />
                        {language === 'ta' ? 'தொடர்பு எண்' : 'Callback Phone'}
                      </label>
                      <input
                        type="tel"
                        value={contactPhone}
                        onChange={(e) => setContactPhone(e.target.value)}
                        placeholder="10-digit phone"
                        className="w-full text-xs rounded-xl border border-slate-300 p-2.5 text-slate-900 bg-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        {language === 'ta' ? 'விருப்பமான தேதி' : 'Preferred Visit Date'}
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

                  <div className="pt-2 flex justify-end">
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-5 py-2.5 text-xs font-bold rounded-xl bg-emerald-700 text-white hover:bg-emerald-800 transition-colors shadow-sm flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Submitting Request...</span>
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          <span>Submit Follow-up Request</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}
        </div>

        {/* Fixed Footer (Never clipped) */}
        <div className="shrink-0 p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <div className="text-[11px] text-slate-500 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Tamil Nadu Health Systems Project • 108 Emergency</span>
          </div>

          <div className="flex items-center gap-2">
            {activeTab === 'details' && (
              <button
                type="button"
                onClick={() => setActiveTab('followup')}
                className="px-4 py-2 text-xs font-bold rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 transition-colors shadow-2xs"
              >
                {language === 'ta' ? 'தொடர் சிகிச்சைக்குச் செல்க' : 'Proceed to Follow-up'}
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-200 text-slate-700 hover:bg-slate-300 transition-colors"
            >
              {t('close', 'Close')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
