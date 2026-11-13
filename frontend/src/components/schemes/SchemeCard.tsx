import React from 'react';
import {
  Award,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Bookmark,
  Scale,
  FileText,
  Sparkles,
  HelpCircle,
  XCircle,
  Calendar,
  ShieldCheck,
} from 'lucide-react';
import { EligibilityEvaluation, SchemeMatchItemOut } from '../../types';
import { useTranslation } from '../../context/LanguageContext';

interface SchemeCardProps {
  evaluation: EligibilityEvaluation | SchemeMatchItemOut;
  onViewDetails: (scheme: any) => void;
  onToggleSave: (schemeId: string) => void;
  onToggleCompare: (schemeId: string) => void;
  onAskAI: (schemeName: string) => void;
  isSaved: boolean;
  isCompared: boolean;
}

export const SchemeCard: React.FC<SchemeCardProps> = ({
  evaluation,
  onViewDetails,
  onToggleSave,
  onToggleCompare,
  onAskAI,
  isSaved,
  isCompared,
}) => {
  const { language } = useTranslation();
  const isTa = language === 'ta';
  const scheme = evaluation.scheme;

  const title = isTa ? scheme.name_ta || scheme.name : scheme.name;
  const shortDesc = isTa ? scheme.short_description_ta || scheme.short_description : scheme.short_description;
  const dept = isTa ? scheme.department_ta || scheme.department : scheme.department;
  const benefitDesc = isTa ? scheme.benefit_amount_desc_ta || scheme.benefit_amount_desc : scheme.benefit_amount_desc;

  // Normalize status and reasons across EligibilityEvaluation and SchemeMatchItemOut
  const rawStatus = (evaluation as any).match_status || (evaluation as any).eligibility_status || 'MORE_INFO_NEEDED';
  const reasons: string[] = (evaluation as any).reasons || (evaluation as any).matched_reasons || [];
  const missingInfo: string[] = (evaluation as any).missing_information || (evaluation as any).unverified_conditions || [];
  const unmetCriteria: string[] = (evaluation as any).unmet_criteria || [];

  const getStatusBadge = () => {
    switch (rawStatus) {
      case 'LIKELY_MATCH':
      case 'LIKELY_ELIGIBLE':
        return {
          label: isTa ? 'பொருத்தமானது (Likely Match)' : 'Likely Match',
          className: 'bg-emerald-50 text-emerald-800 border-emerald-200',
          icon: CheckCircle2,
        };
      case 'MORE_INFO_NEEDED':
      case 'POSSIBLY_ELIGIBLE':
      case 'MORE_INFO_REQUIRED':
        return {
          label: isTa ? 'கூடுதல் தகவல் தேவை' : 'More Information Needed',
          className: 'bg-amber-50 text-amber-800 border-amber-200',
          icon: AlertCircle,
        };
      case 'NOT_MATCHING':
      case 'NOT_ELIGIBLE':
      default:
        return {
          label: isTa ? 'தகுதி பொருந்தவில்லை' : 'Not Currently Matching',
          className: 'bg-rose-50 text-rose-800 border-rose-200',
          icon: XCircle,
        };
    }
  };

  const statusBadge = getStatusBadge();
  const StatusIcon = statusBadge.icon;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs hover:shadow-md transition-all duration-200 overflow-hidden flex flex-col justify-between">
      {/* Top Banner / Badges */}
      <div className="p-5">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                scheme.level === 'STATE'
                  ? 'bg-healthcare-50 text-healthcare-800 border-healthcare-200'
                  : 'bg-indigo-50 text-indigo-800 border-indigo-200'
              }`}
            >
              <Award className="w-3.5 h-3.5" />
              {scheme.level === 'STATE' ? (isTa ? 'தமிழ்நாடு அரசு' : 'Tamil Nadu State') : (isTa ? 'மத்திய அரசு' : 'Central Govt')}
            </span>

            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-700">
              {scheme.category}
            </span>
          </div>

          {/* Eligibility status badge */}
          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${statusBadge.className}`}>
            <StatusIcon className="w-3.5 h-3.5" />
            {statusBadge.label}
          </span>
        </div>

        {/* Scheme Title & Department */}
        <h3 className="text-base font-bold text-navy-900 leading-snug tracking-tight mb-1">
          {title}
        </h3>
        <p className="text-xs text-slate-500 font-medium mb-3 line-clamp-1">
          {dept}
        </p>

        {/* Highlighted Benefit Pill */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 mb-3">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-0.5">
            {isTa ? 'உதவித்தொகை / சலுகை' : 'Financial Benefit & Assistance'}
          </span>
          <p className="text-sm font-bold text-healthcare-800">
            {benefitDesc}
          </p>
        </div>

        <p className="text-xs text-slate-600 leading-relaxed mb-4 line-clamp-2">
          {shortDesc}
        </p>

        {/* NALAM AI Assessment Section */}
        <div className="bg-slate-50/70 border border-slate-100 rounded-xl p-3 mb-3 space-y-2">
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-700">
            <Sparkles className="w-3 h-3 text-healthcare-600" />
            <span>{isTa ? 'நலம் AI தகுதி மதிப்பீடு:' : 'NALAM AI Assessment:'}</span>
          </div>

          {/* Why Matched Points */}
          {reasons.length > 0 && (
            <div className="space-y-1">
              {reasons.slice(0, 2).map((reason, idx) => (
                <div key={idx} className="flex items-start gap-1.5 text-xs text-slate-600">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <span className="line-clamp-1">{reason}</span>
                </div>
              ))}
            </div>
          )}

          {/* Requirements to verify */}
          {missingInfo.length > 0 && (
            <div className="space-y-1 pt-1 border-t border-slate-200/50">
              <span className="text-[10px] font-semibold text-amber-800 block">
                {isTa ? 'சரிபார்க்க வேண்டிய நிபந்தனைகள்:' : 'To verify officially:'}
              </span>
              {missingInfo.slice(0, 1).map((cond, idx) => (
                <div key={idx} className="flex items-start gap-1.5 text-xs text-amber-700">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <span className="line-clamp-1">{cond}</span>
                </div>
              ))}
            </div>
          )}

          {/* Unmet Criteria */}
          {unmetCriteria.length > 0 && (
            <div className="space-y-1 pt-1 border-t border-slate-200/50">
              {unmetCriteria.slice(0, 1).map((u, idx) => (
                <div key={idx} className="flex items-start gap-1.5 text-xs text-rose-700">
                  <XCircle className="w-3.5 h-3.5 text-rose-600 flex-shrink-0 mt-0.5" />
                  <span className="line-clamp-1">{u}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Official Source & Verification Date */}
        <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            <span>{isTa ? 'சரிபார்க்கப்பட்டது: நவம்பர் 2026' : 'Verified: Nov 2026'}</span>
          </span>
          {scheme.official_portal_url && (
            <a
              href={scheme.official_portal_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-healthcare-700 hover:underline flex items-center gap-1 font-semibold"
            >
              <span>{isTa ? 'அரசு தளம்' : 'Official Portal'}</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>

      {/* Action Footer */}
      <div className="border-t border-slate-100 bg-slate-50/70 px-4 py-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          {/* Bookmark Button */}
          <button
            onClick={() => onToggleSave(scheme.id)}
            title={isSaved ? (isTa ? 'சேமிக்கப்பட்டது' : 'Saved') : (isTa ? 'திட்டத்தை சேமி' : 'Save Scheme')}
            className={`p-2 rounded-lg text-xs font-medium transition-colors ${
              isSaved
                ? 'bg-healthcare-100 text-healthcare-800 hover:bg-healthcare-200'
                : 'text-slate-500 hover:text-navy-900 hover:bg-white'
            }`}
          >
            <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-current' : ''}`} />
          </button>

          {/* Compare Checkbox */}
          <button
            onClick={() => onToggleCompare(scheme.id)}
            title={isCompared ? (isTa ? 'ஒப்பீட்டில் உள்ளது' : 'In comparison') : (isTa ? 'ஒப்பிட சேர்க்க' : 'Add to compare')}
            className={`p-2 rounded-lg text-xs font-medium transition-colors ${
              isCompared
                ? 'bg-indigo-100 text-indigo-800 hover:bg-indigo-200'
                : 'text-slate-500 hover:text-navy-900 hover:bg-white'
            }`}
          >
            <Scale className="w-4 h-4" />
          </button>

          {/* Ask AI button */}
          <button
            onClick={() => onAskAI(title)}
            title={isTa ? 'நலம் AI-யிடம் கேட்க' : 'Ask NALAM AI'}
            className="p-2 rounded-lg text-xs font-medium text-slate-500 hover:text-healthcare-700 hover:bg-white transition-colors"
          >
            <Sparkles className="w-4 h-4" />
          </button>
        </div>

        {/* View Details Button */}
        <button
          onClick={() => onViewDetails(scheme)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-healthcare-600 text-white hover:bg-healthcare-700 transition-colors shadow-xs"
        >
          <span>{isTa ? 'முழு விவரம்' : 'View Details'}</span>
        </button>
      </div>
    </div>
  );
};
