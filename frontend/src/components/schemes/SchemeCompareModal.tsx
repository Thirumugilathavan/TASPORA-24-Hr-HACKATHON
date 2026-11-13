import React from 'react';
import { X, Scale, ExternalLink, Award, FileText } from 'lucide-react';
import { GovernmentScheme } from '../../types';
import { useTranslation } from '../../context/LanguageContext';

interface SchemeCompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  schemes: GovernmentScheme[];
  onRemoveScheme: (schemeId: string) => void;
  onClearAll: () => void;
}

export const SchemeCompareModal: React.FC<SchemeCompareModalProps> = ({
  isOpen,
  onClose,
  schemes,
  onRemoveScheme,
  onClearAll,
}) => {
  const { language } = useTranslation();
  const isTa = language === 'ta';

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-navy-950/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-50 text-indigo-700 rounded-xl">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-navy-900 tracking-tight">
                {isTa ? 'அரசு நலத்திட்டங்களை ஒப்பிடுக' : 'Compare Government Schemes'}
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? `${schemes.length} திட்டங்கள் தேர்ந்தெடுக்கப்பட்டுள்ளன (அதிகபட்சம் 3)`
                  : `${schemes.length} schemes selected for side-by-side comparison`}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {schemes.length > 0 && (
              <button
                onClick={onClearAll}
                className="text-xs text-rose-600 hover:text-rose-700 font-semibold px-2.5 py-1.5 rounded-lg hover:bg-rose-50"
              >
                {isTa ? 'அனைத்தையும் நீக்கு' : 'Clear All'}
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Table / Columns */}
        <div className="p-6 overflow-x-auto flex-1 text-xs">
          {schemes.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Scale className="w-10 h-10 mx-auto mb-2 text-slate-300" />
              <p>{isTa ? 'ஒப்பிடுவதற்கு திட்டங்கள் எதுவும் தேர்ந்தெடுக்கப்படவில்லை.' : 'No schemes selected for comparison.'}</p>
            </div>
          ) : (
            <div className="min-w-[600px] grid grid-cols-4 gap-4">
              {/* Labels Column */}
              <div className="space-y-6 pt-12 font-bold text-slate-400 uppercase tracking-wider text-[11px]">
                <div className="h-10 flex items-center">{isTa ? 'அரசு நிலை' : 'Govt Level'}</div>
                <div className="h-14 flex items-center">{isTa ? 'நிதி உதவி / சலுகை' : 'Financial Benefit'}</div>
                <div className="h-14 flex items-center">{isTa ? 'அரசுத் துறை' : 'Department'}</div>
                <div className="h-10 flex items-center">{isTa ? 'வழங்கும் முறை' : 'Frequency'}</div>
                <div className="h-12 flex items-center">{isTa ? 'விண்ணப்பிக்கும் முறை' : 'Application Mode'}</div>
                <div className="h-10 flex items-center">{isTa ? 'அதிகாரப்பூர்வ தளம்' : 'Official Portal'}</div>
              </div>

              {/* Scheme Columns */}
              {schemes.map((s) => {
                const title = isTa ? s.name_ta || s.name : s.name;
                const dept = isTa ? s.department_ta || s.department : s.department;
                const benefit = isTa ? s.benefit_amount_desc_ta || s.benefit_amount_desc : s.benefit_amount_desc;

                return (
                  <div
                    key={s.id}
                    className="bg-slate-50/80 rounded-xl p-4 border border-slate-200 relative flex flex-col justify-between"
                  >
                    {/* Remove button */}
                    <button
                      onClick={() => onRemoveScheme(s.id)}
                      className="absolute top-2 right-2 p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md"
                      title={isTa ? 'நீக்கு' : 'Remove'}
                    >
                      <X className="w-4 h-4" />
                    </button>

                    <div>
                      {/* Title */}
                      <div className="h-12 mb-4 pr-6">
                        <h4 className="font-bold text-navy-900 text-xs line-clamp-2 leading-tight">
                          {title}
                        </h4>
                      </div>

                      <div className="space-y-6 text-slate-700">
                        {/* Govt Level */}
                        <div className="h-10 flex items-center">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-semibold border ${
                              s.level === 'STATE'
                                ? 'bg-healthcare-50 text-healthcare-800 border-healthcare-200'
                                : 'bg-indigo-50 text-indigo-800 border-indigo-200'
                            }`}
                          >
                            <Award className="w-3 h-3" />
                            {s.level === 'STATE' ? (isTa ? 'தமிழ்நாடு அரசு' : 'Tamil Nadu State') : (isTa ? 'மத்திய அரசு' : 'Central Govt')}
                          </span>
                        </div>

                        {/* Financial Benefit */}
                        <div className="h-14 flex items-center font-bold text-healthcare-800">
                          {benefit}
                        </div>

                        {/* Department */}
                        <div className="h-14 flex items-center text-slate-600 line-clamp-2">
                          {dept}
                        </div>

                        {/* Frequency */}
                        <div className="h-10 flex items-center font-medium">
                          {s.benefit_frequency}
                        </div>

                        {/* Application Mode */}
                        <div className="h-12 flex items-center font-medium">
                          {s.application_mode}
                        </div>

                        {/* Portal Link */}
                        <div className="h-10 flex items-center">
                          <a
                            href={s.official_portal_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-healthcare-700 font-bold hover:underline"
                          >
                            <span>{isTa ? 'விண்ணப்பிக்க' : 'Apply'}</span>
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
