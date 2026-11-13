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
} from 'lucide-react';
import { EligibilityEvaluation } from '../../types';
import { useTranslation } from '../../context/LanguageContext';

interface SchemeCardProps {
  evaluation: EligibilityEvaluation;
  onViewDetails: (scheme: EligibilityEvaluation['scheme']) => void;
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
  const { language, t } = useTranslation();
  const isTa = language === 'ta';
  const scheme = evaluation.scheme;

  const title = isTa ? scheme.name_ta || scheme.name : scheme.name;
  const shortDesc = isTa ? scheme.short_description_ta || scheme.short_description : scheme.short_description;
  const dept = isTa ? scheme.department_ta || scheme.department : scheme.department;
  const benefitDesc = isTa ? scheme.benefit_amount_desc_ta || scheme.benefit_amount_desc : scheme.benefit_amount_desc;

  // Status Styling
  const getStatusBadge = () => {
    switch (evaluation.eligibility_status) {
      case 'LIKELY_ELIGIBLE':
        return {
          label: isTa ? 'அதிக தகுதி வாய்ப்பு' : 'Likely Eligible',
          className: 'bg-emerald-50 text-emerald-800 border-emerald-200',
          icon: CheckCircle2,
        };
      case 'POSSIBLY_ELIGIBLE':
        return {
          label: isTa ? 'சாத்தியமான தகுதி' : 'Possibly Eligible',
          className: 'bg-amber-50 text-amber-800 border-amber-200',
          icon: AlertCircle,
        };
      case 'MORE_INFO_REQUIRED':
      default:
        return {
          label: isTa ? 'கூடுதல் தகவல் தேவை' : 'More Info Required',
          className: 'bg-blue-50 text-blue-800 border-blue-200',
          icon: HelpCircle,
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
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 mb-4">
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

        {/* Why Matched Points */}
        {evaluation.matched_reasons.length > 0 && (
          <div className="mb-3 space-y-1">
            <span className="text-[11px] font-semibold text-slate-700 block">
              {isTa ? 'நீங்கள் ஏன் தகுதியாகிறீர்கள்:' : 'Why you match:'}
            </span>
            {evaluation.matched_reasons.slice(0, 2).map((reason, idx) => (
              <div key={idx} className="flex items-start gap-1.5 text-xs text-slate-600">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                <span className="line-clamp-1">{reason}</span>
              </div>
            ))}
          </div>
        )}

        {/* Requirements to verify */}
        {evaluation.unverified_conditions.length > 0 && (
          <div className="space-y-1">
            <span className="text-[11px] font-semibold text-amber-800 block">
              {isTa ? 'சரிபார்க்க வேண்டியவை:' : 'To verify officially:'}
            </span>
            {evaluation.unverified_conditions.slice(0, 1).map((cond, idx) => (
              <div key={idx} className="flex items-start gap-1.5 text-xs text-amber-700">
                <AlertCircle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                <span className="line-clamp-1">{cond}</span>
              </div>
            ))}
          </div>
        )}
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
