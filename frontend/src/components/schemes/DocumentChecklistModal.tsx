import React, { useState } from 'react';
import { X, FileText, CheckCircle2, ShieldCheck, AlertCircle } from 'lucide-react';
import { DocumentChecklistResponse } from '../../types';
import { useTranslation } from '../../context/LanguageContext';

interface DocumentChecklistModalProps {
  isOpen: boolean;
  onClose: () => void;
  checklist: DocumentChecklistResponse | null;
}

export const DocumentChecklistModal: React.FC<DocumentChecklistModalProps> = ({
  isOpen,
  onClose,
  checklist,
}) => {
  const { language } = useTranslation();
  const isTa = language === 'ta';

  const [checkedDocs, setCheckedDocs] = useState<Record<string, boolean>>({});

  if (!isOpen || !checklist) return null;

  const toggleCheck = (docName: string) => {
    setCheckedDocs((prev) => ({
      ...prev,
      [docName]: !prev[docName],
    }));
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-navy-950/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-emerald-50 text-emerald-700 rounded-xl">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-navy-900 tracking-tight">
                {isTa ? 'அரசு திட்டங்களுக்கான ஆவணங்கள் சரிபார்ப்புப் பட்டியல்' : 'Government Schemes Document Checklist'}
              </h2>
              <p className="text-xs text-slate-500">
                {isTa
                  ? `மொத்தம் ${checklist.total_documents} ஆவணங்கள் தேவைப்படுகின்றன`
                  : `Total ${checklist.total_documents} unique documents across your eligible schemes`}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6 text-xs text-slate-700">
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-amber-900 flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
            <span>
              {isTa
                ? 'பாதுகாப்பு உறுதி: உங்கள் ஆவணங்களின் எண்கள் அல்லது நகல்கள் நலம் தளத்தில் பதிவேற்றப்பட வேண்டியதில்லை. அரசு இ-சேவை அல்லது நேர்முக விண்ணப்பத்தின் போது சமர்ப்பிக்க இந்த பட்டியலை தயாராக வைத்திருக்கவும்.'
                : 'Security Notice: Document copies and numbers are never stored on NALAM AI. Keep these physical documents ready for verification at your local e-Sevai or District Taluk Office.'}
            </span>
          </div>

          {/* Mandatory Documents */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-rose-700 mb-3 flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4" />
              <span>{isTa ? 'கட்டாய ஆவணங்கள் (Mandatory Documents)' : 'Mandatory Documents'}</span>
            </h4>
            <div className="space-y-2">
              {checklist.mandatory_documents.map((doc, idx) => {
                const name = isTa ? doc.name_ta || doc.name_en : doc.name_en;
                const desc = isTa ? doc.description_ta || doc.description_en : doc.description_en;
                const schemes = isTa ? doc.required_for_schemes_ta : doc.required_for_schemes;
                const isChecked = !!checkedDocs[doc.name_en];

                return (
                  <div
                    key={idx}
                    onClick={() => toggleCheck(doc.name_en)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                      isChecked
                        ? 'bg-emerald-50/50 border-emerald-300'
                        : 'bg-white border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}}
                      className="mt-0.5 h-4 w-4 text-emerald-600 rounded focus:ring-emerald-500"
                    />
                    <div className="flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className={`font-bold text-xs ${isChecked ? 'line-through text-slate-400' : 'text-navy-900'}`}>
                          {name}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                          {isTa ? 'கட்டாயம்' : 'Mandatory'}
                        </span>
                      </div>
                      {desc && <p className="text-[11px] text-slate-500 mt-0.5">{desc}</p>}
                      <div className="mt-2 flex flex-wrap items-center gap-1">
                        <span className="text-[10px] text-slate-400 font-medium">
                          {isTa ? 'தேவைப்படும் திட்டங்கள்:' : 'Required for:'}
                        </span>
                        {schemes.map((sName, sIdx) => (
                          <span
                            key={sIdx}
                            className="inline-flex px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600"
                          >
                            {sName}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Optional Supporting Documents */}
          {checklist.optional_documents.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-slate-400" />
                <span>{isTa ? 'கூடுதல் ஆதரவு ஆவணங்கள் (Optional Supporting Documents)' : 'Optional Supporting Documents'}</span>
              </h4>
              <div className="space-y-2">
                {checklist.optional_documents.map((doc, idx) => {
                  const name = isTa ? doc.name_ta || doc.name_en : doc.name_en;
                  const desc = isTa ? doc.description_ta || doc.description_en : doc.description_en;
                  const schemes = isTa ? doc.required_for_schemes_ta : doc.required_for_schemes;
                  const isChecked = !!checkedDocs[doc.name_en];

                  return (
                    <div
                      key={idx}
                      onClick={() => toggleCheck(doc.name_en)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                        isChecked
                          ? 'bg-emerald-50/50 border-emerald-300'
                          : 'bg-slate-50/60 border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {}}
                        className="mt-0.5 h-4 w-4 text-emerald-600 rounded focus:ring-emerald-500"
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className={`font-semibold text-xs ${isChecked ? 'line-through text-slate-400' : 'text-slate-800'}`}>
                            {name}
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded font-medium bg-slate-200 text-slate-600">
                            {isTa ? 'விருப்பத்திற்குரியது' : 'Optional'}
                          </span>
                        </div>
                        {desc && <p className="text-[11px] text-slate-500 mt-0.5">{desc}</p>}
                        <div className="mt-2 flex flex-wrap items-center gap-1">
                          <span className="text-[10px] text-slate-400 font-medium">
                            {isTa ? 'தேவைப்படும் திட்டங்கள்:' : 'Required for:'}
                          </span>
                          {schemes.map((sName, sIdx) => (
                            <span
                              key={sIdx}
                              className="inline-flex px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600"
                            >
                              {sName}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            {Object.values(checkedDocs).filter(Boolean).length} / {checklist.total_documents}{' '}
            {isTa ? 'ஆவணங்கள் தயார்' : 'documents ready'}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-healthcare-600 text-white hover:bg-healthcare-700 transition-colors shadow-xs"
          >
            {isTa ? 'சரி' : 'Done'}
          </button>
        </div>
      </div>
    </div>
  );
};
