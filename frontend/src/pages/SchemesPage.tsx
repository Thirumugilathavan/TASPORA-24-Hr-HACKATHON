import React, { useState, useEffect, useMemo } from 'react';
import {
  Landmark,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  FileText,
  Scale,
  Bookmark,
  Sparkles,
  HelpCircle,
  RefreshCw,
  Award,
  ShieldCheck,
  ChevronRight,
  ExternalLink,
  Edit2,
  RotateCcw,
  WifiOff,
  XCircle,
  Layers,
  Clock,
  ArrowRight,
  HeartPulse,
} from 'lucide-react';
import { useTranslation } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { schemeService } from '../services/schemeService';
import {
  GovernmentScheme,
  SchemeMatchResponse,
  SchemeMatchItemOut,
  DocumentChecklistResponse,
} from '../types';
import { SchemeCard } from '../components/schemes/SchemeCard';
import { SchemeDetailModal } from '../components/schemes/SchemeDetailModal';
import { SchemeCompareModal } from '../components/schemes/SchemeCompareModal';
import { DocumentChecklistModal } from '../components/schemes/DocumentChecklistModal';
import { SchemeQuestionnaireWizard } from '../components/schemes/SchemeQuestionnaireWizard';
import { AIAssistantModal } from '../components/assistant/AIAssistantModal';
import { QuestionnaireFormAnswers } from '../services/localSchemeMatcher';

export const SchemesPage: React.FC = () => {
  const { language, t } = useTranslation();
  const isTa = language === 'ta';

  const { currentPatient } = useAuth();

  // View Mode: 'intro' | 'wizard' | 'results' | 'catalog'
  const [viewMode, setViewMode] = useState<'intro' | 'wizard' | 'results' | 'catalog'>('intro');
  const [loading, setLoading] = useState<boolean>(false);
  const [isOfflineMode, setIsOfflineMode] = useState<boolean>(false);
  const [matchResults, setMatchResults] = useState<SchemeMatchResponse | null>(null);
  const [allSchemes, setAllSchemes] = useState<GovernmentScheme[]>([]);
  const [savedSchemeIds, setSavedSchemeIds] = useState<string[]>([]);
  const [comparedSchemeIds, setComparedSchemeIds] = useState<string[]>([]);

  // Stored Questionnaire Answers
  const [answers, setAnswers] = useState<QuestionnaireFormAnswers>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('nalam_scheme_form_answers');
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch {
          // ignore
        }
      }
    }
    return {
      state: 'Tamil Nadu',
      district: 'Namakkal',
      pincode: '',
      gender: 'FEMALE',
      residence: 'RURAL',
      income_range: 'BELOW_72K',
      family_size: 4,
      is_woman_head_of_household: true,
      ration_card_type: 'PHH',
      employment_status: 'DAILY_WAGE',
      desired_assistance: ['HEALTHCARE', 'FINANCIAL'],
    };
  });

  // Prefill location from patient profile if available
  useEffect(() => {
    if (currentPatient?.village) {
      setAnswers((prev) => ({
        ...prev,
        district: prev.district || currentPatient.village?.district || 'Namakkal',
        state: prev.state || currentPatient.village?.state || 'Tamil Nadu',
        pincode: prev.pincode || (currentPatient.village as any)?.pincode || '',
      }));
    }
  }, [currentPatient]);

  // Filter & Search State
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedLevel, setSelectedLevel] = useState<string>('ALL');
  const [selectedMatchStatus, setSelectedMatchStatus] = useState<string>('ALL'); // ALL, LIKELY_MATCH, MORE_INFO_NEEDED, NOT_MATCHING
  const [viewOnlySaved, setViewOnlySaved] = useState<boolean>(false);

  // Modals
  const [selectedSchemeForModal, setSelectedSchemeForModal] = useState<GovernmentScheme | null>(null);
  const [isCompareOpen, setIsCompareOpen] = useState<boolean>(false);
  const [isChecklistOpen, setIsChecklistOpen] = useState<boolean>(false);
  const [checklistData, setChecklistData] = useState<DocumentChecklistResponse | null>(null);
  const [isAIAssistantOpen, setIsAIAssistantOpen] = useState<boolean>(false);
  const [initialAIQuery, setInitialAIQuery] = useState<string>('');

  // Initial Load of Saved Schemes
  useEffect(() => {
    schemeService.getSavedSchemes().then((saved) => {
      setSavedSchemeIds(saved.map((s) => s.scheme_id));
    });
  }, [language]);

  // Execute Scheme Matching
  const handleRunMatching = async (formAnswers: QuestionnaireFormAnswers) => {
    setLoading(true);
    setAnswers(formAnswers);
    if (typeof window !== 'undefined') {
      localStorage.setItem('nalam_scheme_form_answers', JSON.stringify(formAnswers));
      localStorage.setItem('nalam_scheme_completed', 'true');
    }

    try {
      const res = await schemeService.matchSchemes(formAnswers, language);
      setMatchResults(res.data);
      setIsOfflineMode(res.isOffline);
      setViewMode('results');
    } catch (err) {
      console.error('Error evaluating matches:', err);
    } finally {
      setLoading(false);
    }
  };

  // Browse Full Catalog Directly
  const handleBrowseCatalog = async () => {
    setLoading(true);
    try {
      const res = await schemeService.getSchemes({ limit: 50 });
      setAllSchemes(res.data);
      setIsOfflineMode(res.isOffline);
      setViewMode('catalog');
    } catch (err) {
      console.error('Error fetching catalog:', err);
    } finally {
      setLoading(false);
    }
  };

  // Reset Search / Questionnaire
  const handleStartNewSearch = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('nalam_scheme_completed');
    }
    setViewMode('wizard');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Toggle Save Scheme
  const handleToggleSave = async (schemeId: string) => {
    const isSaved = savedSchemeIds.includes(schemeId);
    try {
      if (isSaved) {
        await schemeService.removeSavedScheme(schemeId);
        setSavedSchemeIds((prev) => prev.filter((id) => id !== schemeId));
      } else {
        await schemeService.saveScheme(schemeId);
        setSavedSchemeIds((prev) => [...prev, schemeId]);
      }
    } catch (err) {
      console.error('Error toggling save scheme:', err);
    }
  };

  // Toggle Comparison
  const handleToggleCompare = (schemeId: string) => {
    setComparedSchemeIds((prev) => {
      if (prev.includes(schemeId)) {
        return prev.filter((id) => id !== schemeId);
      }
      if (prev.length >= 3) {
        alert(isTa ? 'அதிகபட்சம் 3 திட்டங்களை மட்டுமே ஒப்பிட முடியும்.' : 'You can compare up to 3 schemes at once.');
        return prev;
      }
      return [...prev, schemeId];
    });
  };

  // Open Document Checklist Modal
  const handleOpenChecklist = async () => {
    try {
      const data = await schemeService.getDocumentChecklist();
      setChecklistData(data);
      setIsChecklistOpen(true);
    } catch (err) {
      console.error('Error loading checklist:', err);
    }
  };

  // Open AI Assistant with Scheme Query
  const handleAskAI = (schemeName: string) => {
    const query = isTa
      ? `${schemeName} திட்டத்திற்கான தகுதி, விண்ணப்பிக்கும் முறை மற்றும் தேவையான ஆவணங்கள் என்னென்ன?`
      : `What are the eligibility criteria, application process, and documents required for ${schemeName}?`;
    setInitialAIQuery(query);
    setIsAIAssistantOpen(true);
  };

  // Filtered Results for Results View
  const filteredMatchItems = useMemo(() => {
    if (!matchResults) return [];
    let items: SchemeMatchItemOut[] = [];

    if (selectedMatchStatus === 'ALL') {
      items = matchResults.all_results;
    } else if (selectedMatchStatus === 'LIKELY_MATCH') {
      items = matchResults.likely_matches;
    } else if (selectedMatchStatus === 'MORE_INFO_NEEDED') {
      items = matchResults.more_info_needed;
    } else if (selectedMatchStatus === 'NOT_MATCHING') {
      items = matchResults.not_matching;
    }

    return items.filter((item) => {
      // Category filter
      if (selectedCategory !== 'ALL' && item.scheme.category !== selectedCategory) return false;
      // Level filter
      if (selectedLevel !== 'ALL' && item.scheme.level !== selectedLevel) return false;
      // Saved filter
      if (viewOnlySaved && !savedSchemeIds.includes(item.scheme.id)) return false;
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const name = (item.scheme.name || '').toLowerCase();
        const nameTa = (item.scheme.name_ta || '').toLowerCase();
        const dept = (item.scheme.department || '').toLowerCase();
        const desc = (item.scheme.short_description || '').toLowerCase();
        return name.includes(q) || nameTa.includes(q) || dept.includes(q) || desc.includes(q);
      }
      return true;
    });
  }, [matchResults, selectedMatchStatus, selectedCategory, selectedLevel, viewOnlySaved, searchQuery, savedSchemeIds]);

  // Schemes selected for comparison
  const comparedSchemes = useMemo(() => {
    if (matchResults) {
      return matchResults.all_results
        .filter((item) => comparedSchemeIds.includes(item.scheme.id))
        .map((item) => item.scheme);
    }
    return allSchemes.filter((s) => comparedSchemeIds.includes(s.id));
  }, [matchResults, allSchemes, comparedSchemeIds]);

  // Categories list
  const categories = [
    { key: 'ALL', label_en: 'All Schemes', label_ta: 'அனைத்து திட்டங்கள்' },
    { key: 'HEALTHCARE', label_en: 'Healthcare & Insurance', label_ta: 'மருத்துவம் & காப்பீடு' },
    { key: 'MATERNITY', label_en: 'Maternity & Child', label_ta: 'மகப்பேறு & குழந்தை நலம்' },
    { key: 'EDUCATION', label_en: 'Education & Scholarships', label_ta: 'கல்வி உதவித்தொகை' },
    { key: 'AGRICULTURE', label_en: 'Agriculture & Farmers', label_ta: 'விவசாயம் & உழவர் நலன்' },
    { key: 'FINANCIAL', label_en: 'Small Business & Credit', label_ta: 'சிறு தொழில் & கடன்' },
    { key: 'PENSION', label_en: 'Social Security Pension', label_ta: 'முதியோர் ஓய்வூதியம்' },
    { key: 'HOUSING', label_en: 'Rural Housing Subsidy', label_ta: 'வீட்டு வசதி மானியம்' },
    { key: 'DISABILITY', label_en: 'Disability Welfare', label_ta: 'மாற்றுத்திறனாளி நலன்' },
  ];

  return (
    <div className="min-h-screen bg-slate-50/60 pb-16">
      {/* Offline Mode Banner */}
      {isOfflineMode && (
        <div className="bg-amber-500/10 border-b border-amber-300 text-amber-900 px-4 py-2.5 text-xs">
          <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <WifiOff className="w-4 h-4 text-amber-700 flex-shrink-0" />
              <span>
                {isTa
                  ? 'கவனிக்க: நேரடி சேவையகம் தற்காலிகமாக இணைக்கப்படவில்லை. சரிபார்க்கப்பட்ட அரசு நலத்திட்ட பதிவுகளின் அடிப்படையில் மதிப்பீடுகள் காட்டப்படுகின்றன (சரிபார்க்கப்பட்டது: நவம்பர் 2026).'
                  : 'Notice: Live backend is currently offline. Recommendations are evaluated against verified official government scheme records (Last verified: November 2026).'}
              </span>
            </div>
            <button
              onClick={() => handleRunMatching(answers)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-amber-600 text-white font-semibold text-[11px] hover:bg-amber-700 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              <span>{isTa ? 'மீண்டும் முயற்சிக்க' : 'Retry'}</span>
            </button>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {/* ========================================================================= */}
        {/* VIEW 0: INTRODUCTORY SCREEN */}
        {/* ========================================================================= */}
        {viewMode === 'intro' && (
          <div className="max-w-4xl mx-auto space-y-8 animate-fadeIn">
            {/* Hero Card */}
            <div className="bg-gradient-to-r from-healthcare-800 via-healthcare-900 to-navy-950 rounded-3xl p-8 md:p-10 text-white shadow-lg relative overflow-hidden">
              <div className="absolute top-0 right-0 w-80 h-80 bg-healthcare-500/10 rounded-full blur-3xl pointer-events-none" />
              <div className="relative z-10 max-w-2xl">
                <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/10 text-emerald-300 text-xs font-semibold backdrop-blur-md mb-4 border border-white/10">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>{isTa ? 'சரிபார்க்கப்பட்ட அதிகாரப்பூர்வ அரசு நலத்திட்டங்கள்' : 'Verified Official Government Schemes'}</span>
                </div>

                <h1 className="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight leading-tight mb-3">
                  {isTa ? 'நலம் AI அரசு நலத்திட்ட வழிகாட்டி' : 'NALAM AI Government Healthcare Scheme Finder'}
                </h1>

                <p className="text-slate-200 text-sm md:text-base leading-relaxed mb-6">
                  {isTa
                    ? 'உங்கள் குடும்ப நிலை, இருப்பிடம் மற்றும் மருத்துவத் தேவைகளின் அடிப்படையில் தமிழ்நாடு மற்றும் மத்திய அரசு வழங்கும் மருத்துவக் காப்பீடு, மானியங்கள் மற்றும் நலத்திட்டங்களை உடனடியாகக் கண்டறியுங்கள்.'
                    : 'Discover Central and Tamil Nadu government healthcare assistance, maternity coverage, cashless hospital insurance, and welfare subsidies tailored to your household circumstances.'}
                </p>

                {/* Main Action Buttons */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3.5">
                  <button
                    type="button"
                    onClick={() => {
                      setViewMode('wizard');
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    className="inline-flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-2xl bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold text-sm shadow-md transition-all hover:scale-[1.02] active:scale-[0.98]"
                  >
                    <Sparkles className="w-4 h-4 text-slate-950" />
                    <span>{isTa ? 'தகுதியான திட்டங்களைக் காண்க' : 'Find Eligible Schemes'}</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>

                  <button
                    type="button"
                    onClick={handleBrowseCatalog}
                    className="inline-flex items-center justify-center gap-2 px-5 py-3.5 rounded-2xl bg-white/10 hover:bg-white/15 text-white font-semibold text-sm border border-white/20 transition-colors"
                  >
                    <Landmark className="w-4 h-4 text-slate-300" />
                    <span>{isTa ? 'அனைத்து திட்டங்களையும் காண்க' : 'Browse All Schemes Directly'}</span>
                  </button>
                </div>

                {matchResults && (
                  <div className="mt-6 pt-5 border-t border-white/10 flex items-center justify-between text-xs text-slate-300">
                    <span>{isTa ? 'முந்தைய மதிப்பீட்டு முடிவுகள் கிடைக்கின்றன.' : 'Previous matching results available.'}</span>
                    <button
                      type="button"
                      onClick={() => setViewMode('results')}
                      className="text-amber-300 hover:underline font-semibold flex items-center gap-1"
                    >
                      <span>{isTa ? 'முடிவுகளைக் காண்க' : 'View Results'}</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* 4 Feature Highlights Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="w-9 h-9 rounded-xl bg-healthcare-50 text-healthcare-600 flex items-center justify-center mb-3">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 mb-1">
                  {isTa ? 'சரியான தகுதி சரிபார்ப்பு' : 'Statutory Eligibility'}
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {isTa
                    ? 'CMCHIS, PM-JAY மற்றும் கலைஞர் மகளிர் உரிமைத் திட்டங்களின் சட்டப்பூர்வ விதிகளுடன் துல்லியமாக பொருந்துகிறது.'
                    : 'Evaluated deterministically against official criteria for CMCHIS, PM-JAY, KMUT, and more.'}
                </p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 mb-1">
                  {isTa ? '100% தனியுரிமை உறுதி' : 'Strict Privacy First'}
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {isTa
                    ? 'ஆதார் எண், கடவுச்சொற்கள் அல்லது வங்கிக் கணக்கு எண்களை நாங்கள் ஒருபோதும் கேட்பதில்லை.'
                    : 'Zero collection of Aadhaar numbers, passwords, bank details, or unnecessary personal info.'}
                </p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mb-3">
                  <Clock className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 mb-1">
                  {isTa ? '1 நிமிடத்தில் 7 கேள்விகள்' : 'Takes Under 1 Min'}
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {isTa
                    ? '7 எளிய கேள்விகள் மூலமாக உங்களுக்குப் பொருத்தமான நலத்திட்டங்களை உடனடியாக அறியலாம்.'
                    : '7 structured, step-by-step multiple-choice questions with full backward navigation.'}
                </p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="w-9 h-9 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-3">
                  <FileText className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 mb-1">
                  {isTa ? 'ஆவண சரிபார்ப்பு பட்டியல்' : 'Document Checklists'}
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {isTa
                    ? 'தேவையான ஆவணப் பட்டியல் மற்றும் நேரடி அரசு விண்ணப்ப இணையதள இணைப்புகள் வழங்கப்படும்.'
                    : 'Instant aggregated document checklists and direct official government application portal links.'}
                </p>
              </div>
            </div>

            {/* Popular Verified Schemes Showcase */}
            <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-xs">
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Award className="w-4 h-4 text-healthcare-600" />
                <span>{isTa ? 'முக்கிய அரசு நலத்திட்டங்கள்' : 'Popular Verified Government Schemes'}</span>
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-2xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                  <span className="text-[11px] font-bold text-healthcare-700 bg-healthcare-50 px-2 py-0.5 rounded-md">
                    Tamil Nadu Health
                  </span>
                  <div className="text-sm font-bold text-slate-900 mt-2 mb-1">
                    {isTa ? 'முதலமைச்சரின் விரிவான மருத்துவக் காப்பீட்டுத் திட்டம் (CMCHIS)' : "Chief Minister's Comprehensive Health Insurance (CMCHIS)"}
                  </div>
                  <div className="text-xs text-emerald-700 font-semibold mb-1">
                    {isTa ? 'ஆண்டுக்கு ₹5,00,000 வரை ரொக்கமில்லா சிகிச்சை' : 'Up to ₹5,00,000/year cashless hospital treatment'}
                  </div>
                  <div className="text-xs text-slate-500">
                    {isTa ? 'குடும்ப ஆண்டு வருமானம் ₹1,20,000-க்குள் உள்ள குடும்பங்களுக்கு' : 'Income ceiling under ₹1,20,000/year with Smart Ration Card'}
                  </div>
                </div>

                <div className="p-4 rounded-2xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                  <span className="text-[11px] font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-md">
                    Tamil Nadu Social Welfare
                  </span>
                  <div className="text-sm font-bold text-slate-900 mt-2 mb-1">
                    {isTa ? 'கலைஞர் மகளிர் உரிமைத் திட்டம் (KMUT)' : 'Kalaignar Magalir Urimai Thittam (KMUT)'}
                  </div>
                  <div className="text-xs text-emerald-700 font-semibold mb-1">
                    {isTa ? 'மாதம் ₹1,000 அடிப்படை உரிமைத்தொகை' : '₹1,000/month basic income for female head of household'}
                  </div>
                  <div className="text-xs text-slate-500">
                    {isTa ? 'ஆண்டு வருமானம் ₹2.5 லட்சத்திற்குள் உள்ள தகுதியான பெண்கள்' : 'Family income under ₹2.5 Lakhs & electricity under 3,600 units'}
                  </div>
                </div>

                <div className="p-4 rounded-2xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                  <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md">
                    National Health Mission
                  </span>
                  <div className="text-sm font-bold text-slate-900 mt-2 mb-1">
                    {isTa ? 'டாக்டர் முத்துலட்சுமி ரெட்டி மகப்பேறு நிதி உதவி' : 'Dr. Muthulakshmi Reddy Maternity Benefit Scheme'}
                  </div>
                  <div className="text-xs text-emerald-700 font-semibold mb-1">
                    {isTa ? '₹18,000 நிதி உதவி + அம்மா தாய்-சேய் ஊட்டச்சத்து பெட்டகம்' : '₹18,000 financial aid + Nutrition Kit'}
                  </div>
                  <div className="text-xs text-slate-500">
                    {isTa ? 'கர்ப்பிணித் தாய்மார்களுக்கு அரசு மருத்துவமனை பிரசவ உதவி' : 'For pregnant & lactating mothers registered in PICME'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 1: QUESTIONNAIRE WIZARD */}
        {/* ========================================================================= */}
        {viewMode === 'wizard' && (
          <div className="max-w-4xl mx-auto">
            <SchemeQuestionnaireWizard
              initialAnswers={answers}
              onComplete={handleRunMatching}
              onBrowseDirectly={handleBrowseCatalog}
              onBackToIntro={() => setViewMode('intro')}
              isSubmitting={loading}
            />
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 2: RESULTS SCREEN */}
        {/* ========================================================================= */}
        {viewMode === 'results' && matchResults && (
          <div className="space-y-6">
            {/* Top Bar with Profile Summary & Actions */}
            <div className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 shadow-xs">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-100">
                <div>
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-healthcare-50 text-healthcare-800 border border-healthcare-200 mb-2">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{isTa ? 'தனிப்பயனாக்கப்பட்ட அரசு நலத்திட்ட முடிவுகள்' : 'Personalized Scheme Discovery Results'}</span>
                  </div>
                  <h1 className="text-xl md:text-2xl font-bold text-navy-900 tracking-tight">
                    {isTa ? 'உங்களுக்குப் பொருந்தக்கூடிய அரசு நலத்திட்டங்கள்' : 'Government Welfare Schemes Recommended for You'}
                  </h1>
                  <p className="text-xs text-slate-500 mt-1">
                    {isTa
                      ? `வசிப்பிடம்: ${answers.district || 'தமிழ்நாடு'} • பாலினம்: ${answers.gender} • வருமான வரம்பு: ${answers.income_range}`
                      : `Location: ${answers.district || 'Tamil Nadu'} • Gender: ${answers.gender} • Income Range: ${answers.income_range}`}
                  </p>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {/* Edit Answers Button */}
                  <button
                    onClick={() => setViewMode('wizard')}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
                  >
                    <Edit2 className="w-3.5 h-3.5 text-healthcare-600" />
                    <span>{isTa ? 'விடைகளைத் திருத்து' : 'Edit Answers'}</span>
                  </button>

                  {/* New Search Button */}
                  <button
                    onClick={handleStartNewSearch}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
                  >
                    <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
                    <span>{isTa ? 'புதிய தேடல்' : 'New Search'}</span>
                  </button>

                  {/* Document Checklist Modal Trigger */}
                  <button
                    onClick={handleOpenChecklist}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-healthcare-600 text-white hover:bg-healthcare-700 transition-colors shadow-xs"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>{isTa ? 'ஆவண சரிபார்ப்பு பட்டியல்' : 'Document Checklist'}</span>
                  </button>
                </div>
              </div>

              {/* Status Metric Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6">
                <button
                  onClick={() => setSelectedMatchStatus('LIKELY_MATCH')}
                  className={`p-4 rounded-2xl border text-left transition-all ${
                    selectedMatchStatus === 'LIKELY_MATCH'
                      ? 'bg-emerald-50 border-emerald-500 ring-2 ring-emerald-500/20'
                      : 'bg-slate-50 border-slate-200 hover:bg-slate-100/70'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-emerald-800 flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      {isTa ? 'பொருத்தமானது' : 'Likely Matches'}
                    </span>
                    <span className="text-lg font-bold text-emerald-900">{matchResults.likely_matches_count}</span>
                  </div>
                  <p className="text-[11px] text-emerald-700/80">
                    {isTa ? 'நிபந்தனைகள் முழுமையாக பொருந்துகின்றன' : 'Satisfies statutory rules'}
                  </p>
                </button>

                <button
                  onClick={() => setSelectedMatchStatus('MORE_INFO_NEEDED')}
                  className={`p-4 rounded-2xl border text-left transition-all ${
                    selectedMatchStatus === 'MORE_INFO_NEEDED'
                      ? 'bg-amber-50 border-amber-500 ring-2 ring-amber-500/20'
                      : 'bg-slate-50 border-slate-200 hover:bg-slate-100/70'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-amber-800 flex items-center gap-1.5">
                      <AlertCircle className="w-4 h-4 text-amber-600" />
                      {isTa ? 'கூடுதல் தகவல் தேவை' : 'More Info Needed'}
                    </span>
                    <span className="text-lg font-bold text-amber-900">{matchResults.more_info_needed_count}</span>
                  </div>
                  <p className="text-[11px] text-amber-700/80">
                    {isTa ? 'ஆவண சரிபார்ப்பு தேவைப்படலாம்' : 'Verification or answers needed'}
                  </p>
                </button>

                <button
                  onClick={() => setSelectedMatchStatus('NOT_MATCHING')}
                  className={`p-4 rounded-2xl border text-left transition-all ${
                    selectedMatchStatus === 'NOT_MATCHING'
                      ? 'bg-rose-50 border-rose-500 ring-2 ring-rose-500/20'
                      : 'bg-slate-50 border-slate-200 hover:bg-slate-100/70'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-rose-800 flex items-center gap-1.5">
                      <XCircle className="w-4 h-4 text-rose-600" />
                      {isTa ? 'தகுதி பொருந்தவில்லை' : 'Not Matching'}
                    </span>
                    <span className="text-lg font-bold text-rose-900">{matchResults.not_matching_count}</span>
                  </div>
                  <p className="text-[11px] text-rose-700/80">
                    {isTa ? 'கட்டாய நிபந்தனை பூர்த்தியாகவில்லை' : 'Mandatory criteria unmet'}
                  </p>
                </button>

                <button
                  onClick={() => setSelectedMatchStatus('ALL')}
                  className={`p-4 rounded-2xl border text-left transition-all ${
                    selectedMatchStatus === 'ALL'
                      ? 'bg-slate-100 border-slate-400 ring-2 ring-slate-400/20'
                      : 'bg-slate-50 border-slate-200 hover:bg-slate-100/70'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                      <Layers className="w-4 h-4 text-slate-600" />
                      {isTa ? 'அனைத்து திட்டங்கள்' : 'All Evaluated'}
                    </span>
                    <span className="text-lg font-bold text-slate-900">{matchResults.total_evaluated}</span>
                  </div>
                  <p className="text-[11px] text-slate-600">
                    {isTa ? 'மதிப்பிடப்பட்ட அனைத்து திட்டங்கள்' : 'Total verified catalog'}
                  </p>
                </button>
              </div>
            </div>

            {/* Filter and Search Bar */}
            <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-2xs space-y-3">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
                {/* Search Input */}
                <div className="relative w-full sm:w-80">
                  <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                  <input
                    type="text"
                    placeholder={isTa ? 'திட்டத்தின் பெயர் அல்லது துறையைத் தேடுக...' : 'Search by scheme name or department...'}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-healthcare-500"
                  />
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap">
                  {/* Level Filter */}
                  <select
                    value={selectedLevel}
                    onChange={(e) => setSelectedLevel(e.target.value)}
                    className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-700"
                  >
                    <option value="ALL">{isTa ? 'மத்திய & மாநில அரசு' : 'All Governments'}</option>
                    <option value="STATE">{isTa ? 'தமிழ்நாடு அரசு' : 'Tamil Nadu State'}</option>
                    <option value="CENTRAL">{isTa ? 'மத்திய அரசு' : 'Central Government'}</option>
                  </select>

                  {/* Saved Filter */}
                  <button
                    onClick={() => setViewOnlySaved(!viewOnlySaved)}
                    className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition-colors ${
                      viewOnlySaved
                        ? 'bg-healthcare-50 border-healthcare-500 text-healthcare-800'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <Bookmark className={`w-3.5 h-3.5 ${viewOnlySaved ? 'fill-current text-healthcare-700' : ''}`} />
                    <span>{isTa ? 'சேமிக்கப்பட்டவை' : 'Saved Only'}</span>
                  </button>
                </div>
              </div>

              {/* Horizontal Category Pills */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-1 no-scrollbar">
                {categories.map((c) => (
                  <button
                    key={c.key}
                    onClick={() => setSelectedCategory(c.key)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                      selectedCategory === c.key
                        ? 'bg-navy-900 text-white font-semibold'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {isTa ? c.label_ta : c.label_en}
                  </button>
                ))}
              </div>
            </div>

            {/* Scheme Cards Grid */}
            {filteredMatchItems.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredMatchItems.map((item) => (
                  <SchemeCard
                    key={item.scheme.id}
                    evaluation={item}
                    onViewDetails={(s) => setSelectedSchemeForModal(s)}
                    onToggleSave={handleToggleSave}
                    onToggleCompare={handleToggleCompare}
                    onAskAI={handleAskAI}
                    isSaved={savedSchemeIds.includes(item.scheme.id)}
                    isCompared={comparedSchemeIds.includes(item.scheme.id)}
                  />
                ))}
              </div>
            ) : (
              /* Helpful Empty Results State with Directory Links */
              <div className="bg-white rounded-3xl border border-slate-200 p-10 text-center max-w-xl mx-auto space-y-4">
                <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
                  <Search className="w-6 h-6" />
                </div>
                <h3 className="text-base font-bold text-navy-900">
                  {isTa ? 'பொருத்தமான திட்டங்கள் எதுவும் காணப்படவில்லை' : 'No Matching Schemes Found for Current Filters'}
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {isTa
                    ? 'தேர்ந்தெடுக்கப்பட்ட வடிகட்டிகளில் திட்டங்கள் இல்லை. பிற பிரிவுகளைத் தேர்ந்தெடுக்கவும் அல்லது அதிகாரப்பூர்வ அரசு தளங்களை பார்வையிடவும்.'
                    : 'No verified schemes matched your exact active filter selection. Try adjusting your filters or browse official government welfare portals directly.'}
                </p>

                {/* Official Directory Links */}
                <div className="pt-2 text-left bg-slate-50 rounded-2xl p-4 border border-slate-200/80">
                  <span className="text-xs font-bold text-slate-700 block mb-2">
                    {isTa ? 'அதிகாரப்பூர்வ அரசு நலத்திட்ட இணையதளங்கள்:' : 'Official Government Scheme Portals:'}
                  </span>
                  <ul className="space-y-1.5 text-xs">
                    <li>
                      <a
                        href="https://www.myscheme.gov.in/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-healthcare-700 hover:underline flex items-center gap-1 font-semibold"
                      >
                        <span>myScheme Government of India (myscheme.gov.in)</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </li>
                    <li>
                      <a
                        href="https://services.india.gov.in/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-healthcare-700 hover:underline flex items-center gap-1 font-semibold"
                      >
                        <span>National Government Services Portal (services.india.gov.in)</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </li>
                    <li>
                      <a
                        href="https://www.tnega.tn.gov.in/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-healthcare-700 hover:underline flex items-center gap-1 font-semibold"
                      >
                        <span>Tamil Nadu e-Governance Agency (tnega.tn.gov.in)</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </li>
                    <li>
                      <a
                        href="https://www.cmchistn.com/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-healthcare-700 hover:underline flex items-center gap-1 font-semibold"
                      >
                        <span>CMCHIS Health Insurance Tamil Nadu (cmchistn.com)</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </li>
                  </ul>
                </div>

                <button
                  onClick={() => {
                    setSelectedCategory('ALL');
                    setSelectedLevel('ALL');
                    setSelectedMatchStatus('ALL');
                    setSearchQuery('');
                    setViewOnlySaved(false);
                  }}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-healthcare-600 text-white text-xs font-semibold hover:bg-healthcare-700 transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>{isTa ? 'வடிகட்டிகளை மீட்டமைக்க' : 'Reset All Filters'}</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 3: CATALOG BROWSER (NO QUESTIONNAIRE) */}
        {/* ========================================================================= */}
        {viewMode === 'catalog' && (
          <div className="space-y-6">
            <div className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-semibold text-healthcare-700 block mb-1">
                  {isTa ? 'அரசு நலத்திட்டங்கள் நேரடிப் பட்டியல்' : 'Official Scheme Catalog'}
                </span>
                <h1 className="text-xl md:text-2xl font-bold text-navy-900 tracking-tight">
                  {isTa ? 'அனைத்து அரசு நலத்திட்டங்களின் பட்டியல் (11 திட்டங்கள்)' : 'All Verified Government Schemes (11 Schemes)'}
                </h1>
                <p className="text-xs text-slate-500 mt-1">
                  {isTa
                    ? 'மத்திய மற்றும் தமிழ்நாடு அரசின் அதிகாரப்பூர்வ தகவல்கள், விதிகள் மற்றும் விண்ணப்ப இணைப்புகள்.'
                    : 'Traceable official information from myscheme.gov.in, cmchistn.com, and tnega.tn.gov.in.'}
                </p>
              </div>

              <button
                onClick={() => setViewMode('wizard')}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 transition-colors shadow-xs"
              >
                <Sparkles className="w-4 h-4 text-amber-300" />
                <span>{isTa ? 'என் தகுதியை அறிய வினாடி வினா' : 'Find Schemes for My Profile'}</span>
              </button>
            </div>

            {/* Catalog Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {allSchemes.map((scheme) => (
                <SchemeCard
                  key={scheme.id}
                  evaluation={{
                    scheme,
                    match_status: 'MORE_INFO_NEEDED',
                    match_status_label_en: 'General Catalog',
                    match_status_label_ta: 'பொதுப் பட்டியல்',
                    match_score: 80,
                    reasons: [isTa ? 'அங்கீகரிக்கப்பட்ட அரசு நலத்திட்டம்' : 'Officially verified government scheme'],
                    missing_information: [isTa ? 'தனிநபர் தகுதியை அறிய வினாடி வினாவுக்கு பதிலளிக்கவும்' : 'Answer questionnaire to check your personalized eligibility'],
                    unmet_criteria: [],
                    required_documents: scheme.required_documents || [],
                    official_source_url: scheme.official_source_url,
                    official_portal_url: scheme.official_portal_url,
                    last_verified_date: 'November 2026',
                    application_status: scheme.application_status || 'OPEN',
                    is_saved: savedSchemeIds.includes(scheme.id),
                  }}
                  onViewDetails={(s) => setSelectedSchemeForModal(s)}
                  onToggleSave={handleToggleSave}
                  onToggleCompare={handleToggleCompare}
                  onAskAI={handleAskAI}
                  isSaved={savedSchemeIds.includes(scheme.id)}
                  isCompared={comparedSchemeIds.includes(scheme.id)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Floating Comparison Drawer */}
      {comparedSchemeIds.length > 0 && (
        <div className="fixed bottom-4 right-4 z-40 bg-navy-900 text-white rounded-2xl shadow-xl border border-white/10 px-5 py-3 flex items-center gap-4">
          <div className="text-xs">
            <span className="font-bold text-amber-300">{comparedSchemeIds.length} / 3</span>{' '}
            <span>{isTa ? 'திட்டங்கள் ஒப்பிட தேர்ந்தெடுக்கப்பட்டுள்ளன' : 'schemes in compare'}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsCompareOpen(true)}
              className="px-3 py-1.5 bg-healthcare-600 hover:bg-healthcare-500 rounded-lg text-xs font-bold text-white transition-colors"
            >
              {isTa ? 'ஒப்பிடுக' : 'Compare Now'}
            </button>
            <button
              onClick={() => setComparedSchemeIds([])}
              className="text-xs text-slate-400 hover:text-white"
            >
              {isTa ? 'நீக்கு' : 'Clear'}
            </button>
          </div>
        </div>
      )}

      {/* Modals */}
      {selectedSchemeForModal && (
        <SchemeDetailModal
          scheme={selectedSchemeForModal}
          isOpen={true}
          onClose={() => setSelectedSchemeForModal(null)}
          onToggleSave={handleToggleSave}
          isSaved={savedSchemeIds.includes(selectedSchemeForModal.id)}
        />
      )}

      {isCompareOpen && (
        <SchemeCompareModal
          schemes={comparedSchemes}
          isOpen={true}
          onClose={() => setIsCompareOpen(false)}
          onRemoveScheme={(id) => setComparedSchemeIds((prev) => prev.filter((x) => x !== id))}
          onClearAll={() => setComparedSchemeIds([])}
        />
      )}

      {isChecklistOpen && checklistData && (
        <DocumentChecklistModal
          checklist={checklistData}
          isOpen={true}
          onClose={() => setIsChecklistOpen(false)}
        />
      )}

      {isAIAssistantOpen && (
        <AIAssistantModal
          isOpen={isAIAssistantOpen}
          onClose={() => setIsAIAssistantOpen(false)}
          initialQuery={initialAIQuery}
        />
      )}
    </div>
  );
};

export default SchemesPage;
