import React from 'react';
import {
  X,
  Award,
  ExternalLink,
  Bookmark,
  CheckCircle2,
  FileText,
  Clock,
  ShieldCheck,
  Building,
  HelpCircle,
} from 'lucide-react';
import { GovernmentScheme } from '../../types';
import { useTranslation } from '../../context/LanguageContext';

interface SchemeDetailModalProps {
  scheme: GovernmentScheme | null;
  isOpen: boolean;
  onClose: () => void;
  onToggleSave: (schemeId: string) => void;
  isSaved: boolean;
}

export const SchemeDetailModal: React.FC<SchemeDetailModalProps> = ({
  scheme,
  isOpen,
  onClose,
  onToggleSave,
  isSaved,
}) => {
  const { language } = useTranslation();
  const isTa = language === 'ta';

  if (!isOpen || !scheme) return null;

  const title = isTa ? scheme.name_ta || scheme.name : scheme.name;
  const dept = isTa ? scheme.department_ta || scheme.department : scheme.department;
  const detailedDesc = isTa ? scheme.detailed_description_ta || scheme.detailed_description : scheme.detailed_description;
  const benefitDesc = isTa ? scheme.benefit_amount_desc_ta || scheme.benefit_amount_desc : scheme.benefit_amount_desc;
  const appProcess = isTa ? scheme.application_process_ta || scheme.application_process : scheme.application_process;
  const beneficiaries = isTa ? scheme.target_beneficiaries_ta || scheme.target_beneficiaries : scheme.target_beneficiaries;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-navy-950/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex items-start justify-between gap-3 bg-slate-50/50">
          <div>
            <div className="flex items-center gap-2 mb-2 flex-wrap">
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
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-200 text-slate-700">
                {scheme.category}
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <ShieldCheck className="w-3 h-3" />
                {isTa ? 'அதிகாரப்பூர்வமாக சரிபார்க்கப்பட்டது' : 'Verified Official Source'}
              </span>
            </div>
            <h2 className="text-lg font-bold text-navy-900 tracking-tight leading-snug">
              {title}
            </h2>
            <p className="text-xs text-slate-500 font-medium flex items-center gap-1 mt-1">
              <Building className="w-3.5 h-3.5 text-slate-400" />
              {dept}
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm text-slate-700">
          {/* Benefit Box */}
          <div className="bg-gradient-to-r from-healthcare-50 to-teal-50 border border-healthcare-200 rounded-xl p-4">
            <span className="text-xs font-bold text-healthcare-800 uppercase tracking-wider block mb-1">
              {isTa ? 'நிதி உதவி / நலத்திட்ட சலுகை' : 'Financial Benefit & Assistance'}
            </span>
            <p className="text-base font-bold text-healthcare-900">
              {benefitDesc}
            </p>
            <p className="text-xs text-healthcare-700 mt-1">
              {isTa ? `வழங்கும் முறை: ${scheme.benefit_frequency}` : `Payment Frequency: ${scheme.benefit_frequency}`}
            </p>
          </div>

          {/* Description */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              {isTa ? 'திட்ட விளக்கம்' : 'About the Scheme'}
            </h4>
            <p className="text-slate-600 leading-relaxed text-xs sm:text-sm">
              {detailedDesc}
            </p>
          </div>

          {/* Target Beneficiaries */}
          {beneficiaries && beneficiaries.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                {isTa ? 'பயனாளிகள்' : 'Target Beneficiaries'}
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {beneficiaries.map((b, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 text-slate-700"
                  >
                    {b}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Required Documents */}
          {scheme.required_documents && scheme.required_documents.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2.5 flex items-center justify-between">
                <span>{isTa ? 'தேவையான ஆவணங்கள்' : 'Required Documents'}</span>
                <span className="text-[11px] text-slate-500 font-normal lowercase">
                  ({scheme.required_documents.length} {isTa ? 'ஆவணங்கள்' : 'documents'})
                </span>
              </h4>
              <div className="space-y-2">
                {scheme.required_documents.map((doc, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 flex items-start justify-between gap-3"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-healthcare-600 flex-shrink-0" />
                        <span className="font-semibold text-xs text-navy-900">
                          {isTa ? doc.name_ta || doc.name_en : doc.name_en}
                        </span>
                        {doc.is_mandatory ? (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                            {isTa ? 'கட்டாயம்' : 'Mandatory'}
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
                            {isTa ? 'விருப்பத்திற்குரியது' : 'Optional'}
                          </span>
                        )}
                      </div>
                      {(doc.description_en || doc.description_ta) && (
                        <p className="text-[11px] text-slate-500 mt-1 pl-6">
                          {isTa ? doc.description_ta || doc.description_en : doc.description_en}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Application Steps */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              {isTa ? 'விண்ணப்பிக்கும் முறை' : 'How to Apply'}
            </h4>
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 text-xs text-slate-700 whitespace-pre-line leading-relaxed">
              {appProcess}
            </div>
          </div>

          {/* Official Verification Details */}
          <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              {isTa ? 'கடைசியாக சரிபார்க்கப்பட்ட தேதி:' : 'Last verified date:'}{' '}
              {new Date(scheme.last_verified_at).toLocaleDateString()}
            </span>
            <a
              href={scheme.official_source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-healthcare-700 hover:text-healthcare-800 font-medium inline-flex items-center gap-1 hover:underline"
            >
              <span>{isTa ? 'அரசு மூல தகவல்' : 'Official Source Documentation'}</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between gap-3">
          <button
            onClick={() => onToggleSave(scheme.id)}
            className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold border transition-colors ${
              isSaved
                ? 'bg-healthcare-100 text-healthcare-800 border-healthcare-300'
                : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
            }`}
          >
            <Bookmark className={`w-3.5 h-3.5 ${isSaved ? 'fill-current' : ''}`} />
            <span>{isSaved ? (isTa ? 'சேமிக்கப்பட்டது' : 'Saved in Bookmarks') : (isTa ? 'திட்டத்தை சேமிக்க' : 'Save Scheme')}</span>
          </button>

          <a
            href={scheme.official_portal_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-healthcare-600 text-white hover:bg-healthcare-700 transition-colors shadow-sm"
          >
            <span>{isTa ? 'அதிகாரப்பூர்வ தளத்தில் விண்ணப்பிக்க' : 'Apply on Official Government Portal'}</span>
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>
    </div>
  );
};
