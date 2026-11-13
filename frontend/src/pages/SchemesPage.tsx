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
} from 'lucide-react';
import { useTranslation } from '../context/LanguageContext';
import { schemeService } from '../services/schemeService';
import {
  GovernmentScheme,
  EligibilityEvaluation,
  SchemeRecommendationResponse,
  UserSchemeProfile,
  DocumentChecklistResponse,
} from '../types';
import { SchemeCard } from '../components/schemes/SchemeCard';
import { SchemeDetailModal } from '../components/schemes/SchemeDetailModal';
import { SchemeQuestionnaireModal } from '../components/schemes/SchemeQuestionnaireModal';
import { SchemeCompareModal } from '../components/schemes/SchemeCompareModal';
import { DocumentChecklistModal } from '../components/schemes/DocumentChecklistModal';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';

export const SchemesPage: React.FC = () => {
  const { language, t } = useTranslation();
  const isTa = language === 'ta';

  // State
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [recommendationsData, setRecommendationsData] = useState<SchemeRecommendationResponse | null>(null);
  const [userProfile, setUserProfile] = useState<UserSchemeProfile | null>(null);
  const [savedSchemeIds, setSavedSchemeIds] = useState<string[]>([]);
  const [comparedSchemeIds, setComparedSchemeIds] = useState<string[]>([]);

  // Filter & Search State
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedLevel, setSelectedLevel] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [viewOnlySaved, setViewOnlySaved] = useState<boolean>(false);

  // Modals
  const [selectedSchemeForModal, setSelectedSchemeForModal] = useState<GovernmentScheme | null>(null);
  const [isQuestionnaireOpen, setIsQuestionnaireOpen] = useState<boolean>(false);
  const [isCompareOpen, setIsCompareOpen] = useState<boolean>(false);
  const [isChecklistOpen, setIsChecklistOpen] = useState<boolean>(false);
  const [checklistData, setChecklistData] = useState<DocumentChecklistResponse | null>(null);

  // Initial Load
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [recs, profile, saved] = await Promise.all([
        schemeService.getRecommendations({ language }),
        schemeService.getUserProfile().catch(() => null),
        schemeService.getSavedSchemes().catch(() => []),
      ]);

      setRecommendationsData(recs);
      setUserProfile(profile);
      setSavedSchemeIds(saved.map((s) => s.scheme_id));
    } catch (err: any) {
      console.error('Failed to load schemes:', err);
      setError(err.message || 'Failed to load government scheme recommendations.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [language]);

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

  // Toggle Compare Scheme
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

  // Open Document Checklist
  const handleOpenChecklist = async () => {
    try {
      const data = await schemeService.getDocumentChecklist(
        savedSchemeIds.length > 0 ? savedSchemeIds : undefined
      );
      setChecklistData(data);
      setIsChecklistOpen(true);
    } catch (err) {
      console.error('Failed to fetch document checklist:', err);
    }
  };

  // Save Questionnaire Profile
  const handleSaveProfile = async (profileData: Record<string, any>) => {
    try {
      await schemeService.saveUserProfile({
        consent_given: true,
        step_progress: 8,
        profile_data: profileData,
      });
      await loadData();
    } catch (err) {
      console.error('Failed to save profile:', err);
    }
  };

  // Open AI Assistant with query
  const handleAskAI = (schemeName: string) => {
    const prompt = isTa
      ? `${schemeName} திட்டத்தைப் பற்றி விரிவாக விளக்குங்கள். தகுதி மற்றும் தேவையான ஆவணங்கள் என்ன?`
      : `Please explain ${schemeName} in detail. What are the eligibility criteria and documents required?`;
    window.dispatchEvent(new CustomEvent('open_ai_assistant', { detail: { prompt } }));
  };

  // Filtered List
  const filteredRecommendations = useMemo(() => {
    if (!recommendationsData) return [];

    return recommendationsData.recommendations.filter((item) => {
      const s = item.scheme;
      // Search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchesName = s.name.toLowerCase().includes(q) || s.name_ta.toLowerCase().includes(q);
        const matchesDept = s.department.toLowerCase().includes(q) || s.department_ta.toLowerCase().includes(q);
        const matchesDesc = s.short_description.toLowerCase().includes(q) || s.short_description_ta.toLowerCase().includes(q);
        if (!matchesName && !matchesDept && !matchesDesc) return false;
      }

      // Category
      if (selectedCategory !== 'ALL' && s.category !== selectedCategory) return false;

      // Level
      if (selectedLevel !== 'ALL' && s.level !== selectedLevel) return false;

      // Status
      if (selectedStatus !== 'ALL' && item.eligibility_status !== selectedStatus) return false;

      // Saved only
      if (viewOnlySaved && !savedSchemeIds.includes(s.id)) return false;

      return true;
    });
  }, [recommendationsData, searchQuery, selectedCategory, selectedLevel, selectedStatus, viewOnlySaved, savedSchemeIds]);

  // Compared Schemes Array
  const comparedSchemes = useMemo(() => {
    if (!recommendationsData) return [];
    return recommendationsData.recommendations
      .filter((r) => comparedSchemeIds.includes(r.scheme.id))
      .map((r) => r.scheme);
  }, [recommendationsData, comparedSchemeIds]);

  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <LoadingState message={isTa ? 'அரசு நலத்திட்டங்கள் கணக்கிடப்படுகின்றன...' : 'Evaluating government schemes and subsidies...'} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
        <ErrorState message={error} onRetry={loadData} />
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Hero Banner */}
      <div className="bg-gradient-to-br from-healthcare-800 via-navy-900 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-lg relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 rounded-full bg-white/5 blur-2xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 backdrop-blur-md border border-white/15 text-healthcare-200">
              <Landmark className="w-3.5 h-3.5" />
              <span>{isTa ? 'அரசு நலத்திட்ட உதவிகள்' : 'Government Benefits & Subsidies'}</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              {isTa ? 'நலம் அரசு நலத்திட்ட வழிகாட்டி' : 'NALAM Scheme Finder'}
            </h1>
            <p className="text-sm text-slate-300 leading-relaxed">
              {isTa
                ? 'உங்கள் குடும்ப வருமானம், தொழில், கல்வி மற்றும் மருத்துவத் தேவைகளுக்கான மத்திய மற்றும் தமிழ்நாடு அரசு மானியங்கள், உதவித்தொகைகள் மற்றும் மருத்துவக் காப்பீடுகளை உடனடியாக கண்டறியுங்கள்.'
                : 'Discover verified Central and Tamil Nadu government welfare, subsidies, scholarships, and healthcare assistance matching your personal circumstances.'}
            </p>
          </div>

          {/* Call-to-action button */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <button
              onClick={() => setIsQuestionnaireOpen(true)}
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-bold text-xs sm:text-sm bg-healthcare-500 hover:bg-healthcare-600 text-white shadow-md transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <Sparkles className="w-4 h-4" />
              <span>{isTa ? 'எனக்கான திட்டங்களை கணக்கிடுக' : 'Find Schemes for Me'}</span>
            </button>
            <button
              onClick={handleOpenChecklist}
              className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-semibold text-xs sm:text-sm bg-white/10 hover:bg-white/15 text-white border border-white/15 backdrop-blur-sm transition-colors"
            >
              <FileText className="w-4 h-4" />
              <span>{isTa ? 'ஆவணங்கள் பட்டியல்' : 'Checklist'}</span>
            </button>
          </div>
        </div>

        {/* Quick Stats Pill Row */}
        {recommendationsData && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-6 border-t border-white/10 text-xs">
            <div className="bg-white/5 backdrop-blur-xs rounded-xl p-3 border border-white/5">
              <span className="text-slate-300 block text-[11px] mb-0.5">
                {isTa ? 'மதிப்பிடப்பட்ட திட்டங்கள்' : 'Total Evaluated'}
              </span>
              <span className="text-lg font-bold text-white">{recommendationsData.total_evaluated}</span>
            </div>
            <div className="bg-emerald-500/10 backdrop-blur-xs rounded-xl p-3 border border-emerald-500/20">
              <span className="text-emerald-300 block text-[11px] mb-0.5">
                {isTa ? 'அதிக தகுதி வாய்ப்பு' : 'Likely Eligible'}
              </span>
              <span className="text-lg font-bold text-emerald-400">{recommendationsData.likely_eligible_count}</span>
            </div>
            <div className="bg-amber-500/10 backdrop-blur-xs rounded-xl p-3 border border-amber-500/20">
              <span className="text-amber-300 block text-[11px] mb-0.5">
                {isTa ? 'சாத்தியமான தகுதி' : 'Possibly Eligible'}
              </span>
              <span className="text-lg font-bold text-amber-400">{recommendationsData.possibly_eligible_count}</span>
            </div>
            <div className="bg-white/5 backdrop-blur-xs rounded-xl p-3 border border-white/5">
              <span className="text-slate-300 block text-[11px] mb-0.5">
                {isTa ? 'சேமிக்கப்பட்டவை' : 'Bookmarked'}
              </span>
              <span className="text-lg font-bold text-white">{savedSchemeIds.length}</span>
            </div>
          </div>
        )}
      </div>

      {/* Comparison Floating Tray Banner if schemes selected */}
      {comparedSchemeIds.length > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-2xl p-4 flex items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-2">
            <Scale className="w-5 h-5 text-indigo-700 flex-shrink-0" />
            <span className="text-xs sm:text-sm font-semibold text-indigo-950">
              {isTa
                ? `${comparedSchemeIds.length} திட்டங்கள் ஒப்பிடுவதற்கு தேர்ந்தெடுக்கப்பட்டுள்ளன.`
                : `${comparedSchemeIds.length} schemes selected for side-by-side comparison.`}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setComparedSchemeIds([])}
              className="text-xs font-semibold text-indigo-700 hover:text-indigo-900 px-3 py-1.5 rounded-lg hover:bg-indigo-100"
            >
              {isTa ? 'நீக்கு' : 'Clear'}
            </button>
            <button
              onClick={() => setIsCompareOpen(true)}
              className="text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 px-4 py-1.5 rounded-lg shadow-xs"
            >
              {isTa ? 'இப்போது ஒப்பிடுக' : 'Compare Now'}
            </button>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200 shadow-xs space-y-4">
        {/* Top search & level toggles */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={
                isTa
                  ? 'திட்டத்தின் பெயர் அல்லது துறையைத் தேடவும் (எ.கா: காப்பீடு, உதவித்தொகை, உழவர்)...'
                  : 'Search by scheme name or keywords (e.g. CMCHIS, scholarship, farmer)...'
              }
              className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-healthcare-500"
            />
          </div>

          {/* Level Filter Buttons */}
          <div className="flex items-center gap-1.5 flex-wrap sm:flex-nowrap">
            {[
              { id: 'ALL', label_en: 'All Levels', label_ta: 'அனைத்து நிலைகளும்' },
              { id: 'STATE', label_en: 'Tamil Nadu', label_ta: 'தமிழ்நாடு அரசு' },
              { id: 'CENTRAL', label_en: 'Central Govt', label_ta: 'மத்திய அரசு' },
            ].map((lvl) => (
              <button
                key={lvl.id}
                onClick={() => setSelectedLevel(lvl.id)}
                className={`px-3 py-2 rounded-xl text-xs font-semibold transition-colors ${
                  selectedLevel === lvl.id
                    ? 'bg-navy-900 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {isTa ? lvl.label_ta : lvl.label_en}
              </button>
            ))}

            {/* Saved Schemes Toggle */}
            <button
              onClick={() => setViewOnlySaved(!viewOnlySaved)}
              className={`inline-flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-semibold border transition-colors ${
                viewOnlySaved
                  ? 'bg-healthcare-50 text-healthcare-800 border-healthcare-300'
                  : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
              }`}
            >
              <Bookmark className={`w-3.5 h-3.5 ${viewOnlySaved ? 'fill-current' : ''}`} />
              <span>{isTa ? `சேமிக்கப்பட்டவை (${savedSchemeIds.length})` : `Saved (${savedSchemeIds.length})`}</span>
            </button>
          </div>
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          {[
            { id: 'ALL', label_en: 'All Categories', label_ta: 'அனைத்தும்' },
            { id: 'HEALTHCARE', label_en: 'Healthcare', label_ta: 'மருத்துவக் காப்பீடு' },
            { id: 'WOMEN_CHILD', label_en: 'Women & Child', label_ta: 'மகளிர் & தாய்மை' },
            { id: 'EDUCATION', label_en: 'Scholarships', label_ta: 'கல்வி உதவித்தொகை' },
            { id: 'AGRICULTURE', label_en: 'Farmers & Agri', label_ta: 'விவசாய மானியங்கள்' },
            { id: 'PENSION', label_en: 'Pensions', label_ta: 'ஓய்வூதியங்கள்' },
            { id: 'DISABILITY', label_en: 'Differently Abled', label_ta: 'மாற்றுத்திறனாளி' },
            { id: 'HOUSING', label_en: 'Housing Grants', label_ta: 'வீடு கட்டும் திட்டம்' },
            { id: 'EMPLOYMENT', label_en: 'Business Loans', label_ta: 'சிறு தொழில் கடன்' },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1.5 rounded-lg whitespace-nowrap font-medium transition-colors ${
                selectedCategory === cat.id
                  ? 'bg-healthcare-600 text-white font-semibold'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {isTa ? cat.label_ta : cat.label_en}
            </button>
          ))}
        </div>
      </div>

      {/* Schemes Grid */}
      {filteredRecommendations.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-200">
          <Landmark className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-navy-900 mb-1">
            {isTa ? 'பொருத்தமான திட்டங்கள் எதுவும் காணப்படவில்லை' : 'No matching schemes found'}
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mb-4">
            {isTa
              ? 'உங்கள் வடிகட்டிகளை மாற்றிப் பார்க்கவும் அல்லது புதிய தகவல்களுடன் சுயவிவரத்தை புதுப்பிக்கவும்.'
              : 'Try clearing your search query, adjusting your category filters, or updating your questionnaire profile.'}
          </p>
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedCategory('ALL');
              setSelectedLevel('ALL');
              setViewOnlySaved(false);
            }}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors"
          >
            {isTa ? 'அனைத்து வடிகட்டிகளையும் நீக்குக' : 'Reset All Filters'}
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredRecommendations.map((evalItem) => (
            <SchemeCard
              key={evalItem.scheme.id}
              evaluation={evalItem}
              onViewDetails={(s) => setSelectedSchemeForModal(s)}
              onToggleSave={handleToggleSave}
              onToggleCompare={handleToggleCompare}
              onAskAI={handleAskAI}
              isSaved={savedSchemeIds.includes(evalItem.scheme.id)}
              isCompared={comparedSchemeIds.includes(evalItem.scheme.id)}
            />
          ))}
        </div>
      )}

      {/* Mandatory Official Disclaimer Footer */}
      <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 text-xs text-slate-500 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-healthcare-700 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-slate-700 block mb-0.5">
            {isTa ? 'அரசு தகுதி அறிவிப்பு & பொறுப்புத் துறப்பு' : 'Government Verification Notice & Disclaimer'}
          </span>
          <p className="leading-relaxed">
            {isTa ? recommendationsData?.disclaimer_ta : recommendationsData?.disclaimer}
          </p>
        </div>
      </div>

      {/* Modals */}
      <SchemeDetailModal
        scheme={selectedSchemeForModal}
        isOpen={!!selectedSchemeForModal}
        onClose={() => setSelectedSchemeForModal(null)}
        onToggleSave={handleToggleSave}
        isSaved={selectedSchemeForModal ? savedSchemeIds.includes(selectedSchemeForModal.id) : false}
      />

      <SchemeQuestionnaireModal
        isOpen={isQuestionnaireOpen}
        onClose={() => setIsQuestionnaireOpen(false)}
        onSaveProfile={handleSaveProfile}
        initialProfile={userProfile}
      />

      <SchemeCompareModal
        isOpen={isCompareOpen}
        onClose={() => setIsCompareOpen(false)}
        schemes={comparedSchemes}
        onRemoveScheme={(id) => setComparedSchemeIds((prev) => prev.filter((sId) => sId !== id))}
        onClearAll={() => setComparedSchemeIds([])}
      />

      <DocumentChecklistModal
        isOpen={isChecklistOpen}
        onClose={() => setIsChecklistOpen(false)}
        checklist={checklistData}
      />
    </div>
  );
};
