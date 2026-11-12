import React, { useState, useEffect } from 'react';
import { HealthcareRequest, Medicine, RequestType, Urgency } from '../../types';
import { medicineService } from '../../services/medicineService';
import { requestService } from '../../services/requestService';
import { useAuth } from '../../context/AuthContext';
import { useTranslation } from '../../context/LanguageContext';
import { X, Send, AlertCircle, Loader2 } from 'lucide-react';

interface CreateRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit?: (data: {
    request_type: RequestType;
    description: string;
    urgency: Urgency;
    medicine_id?: string;
  }) => Promise<void>;
  onCreated?: (request: HealthcareRequest) => void;
  initialRequestType?: RequestType;
  initialMedicineId?: string;
  preselectedMedicineId?: string;
}

export const CreateRequestModal: React.FC<CreateRequestModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  onCreated,
  initialRequestType,
  initialMedicineId,
  preselectedMedicineId,
}) => {
  const { currentPatient, user } = useAuth();
  const { t } = useTranslation();

  const initMed = initialMedicineId || preselectedMedicineId || '';
  const initType = initialRequestType || (initMed ? 'REFILL' : 'CONSULTATION');

  const [requestType, setRequestType] = useState<RequestType>(initType);
  const [description, setDescription] = useState('');
  const [urgency, setUrgency] = useState<Urgency>('NORMAL');
  const [medicineId, setMedicineId] = useState(initMed);
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      medicineService.getMedicines().then(setMedicines).catch(() => {});
      const med = initialMedicineId || preselectedMedicineId || '';
      if (med) {
        setRequestType('REFILL');
        setMedicineId(med);
      } else if (initialRequestType) {
        setRequestType(initialRequestType);
      }
    }
  }, [isOpen, initialMedicineId, preselectedMedicineId, initialRequestType]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) {
      setError(t('describeSymptomsPlaceholder', 'Please provide a brief description of your healthcare request.'));
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      if (onSubmit) {
        await onSubmit({
          request_type: requestType,
          description: description.trim(),
          urgency,
          medicine_id: requestType === 'REFILL' && medicineId ? medicineId : undefined,
        });
      } else {
        const patientId = currentPatient?.id || user?.id || 'pat-sample-1';
        const newReq = await requestService.createRequest({
          patient_id: patientId,
          request_type: requestType,
          description: description.trim(),
          urgency,
          medicine_id: requestType === 'REFILL' && medicineId ? medicineId : undefined,
        });
        if (onCreated) {
          onCreated(newReq);
        }
      }
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('errorTitle', 'Failed to submit healthcare request');
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-100 bg-slate-50/60">
          <div>
            <h3 className="text-lg font-bold text-slate-900">{t('submitRequestTitle', 'Submit Healthcare Request')}</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {t('createRequestSubtitle', 'CareBridge will analyze nearby facilities and available medicines.')}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/60 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-rose-600 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Request Type */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              {t('whatKindOfService', 'What kind of healthcare service do you need?')}
            </label>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {[
                { type: 'CONSULTATION', label: t('reqConsultation', 'Doctor Consultation') },
                { type: 'REFILL', label: t('reqRefill', 'Medicine Refill') },
                { type: 'CHECKUP', label: t('reqCheckup', 'Routine Checkup') },
                { type: 'DIAGNOSTIC', label: t('reqDiagnostic', 'Diagnostic Test') },
              ].map((opt) => (
                <button
                  key={opt.type}
                  type="button"
                  onClick={() => setRequestType(opt.type as RequestType)}
                  className={`p-2.5 rounded-lg border text-left font-medium transition-colors ${
                    requestType === opt.type
                      ? 'border-emerald-600 bg-emerald-50 text-emerald-900 font-semibold shadow-xs'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Medicine Selection if Refill */}
          {requestType === 'REFILL' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                {t('selectMedicineRefill', 'Select Medicine to Refill')}
              </label>
              <select
                value={medicineId}
                onChange={(e) => setMedicineId(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-300 p-2.5 bg-white text-slate-800 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              >
                <option value="">{t('selectMedicinePlaceholder', 'Select from essential medicine list...')}</option>
                {medicines.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.code})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              {t('describeSymptoms', 'Description / Symptoms')}
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('describeSymptomsPlaceholder', 'e.g. Need monthly diabetes medication, or persistent fever and body ache since yesterday...')}
              className="w-full text-xs rounded-lg border border-slate-300 p-2.5 text-slate-800 placeholder-slate-400 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          {/* Urgency */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              {t('urgencyLevel', 'Urgency Level')}
            </label>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {[
                { val: 'NORMAL', label: t('urgencyNormal', 'Routine (Normal)') },
                { val: 'PRIORITY', label: t('urgencyPriority', 'Priority (Within 1-2 days)') },
                { val: 'URGENT', label: t('urgencyUrgent', 'Urgent (Today)') },
              ].map((u) => (
                <button
                  key={u.val}
                  type="button"
                  onClick={() => setUrgency(u.val as Urgency)}
                  className={`p-2 rounded-lg border text-center font-medium transition-colors ${
                    urgency === u.val
                      ? 'border-emerald-600 bg-emerald-50 text-emerald-900 font-bold'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {u.label}
                </button>
              ))}
            </div>
            <p className="mt-1 text-[11px] text-slate-400 italic">
              {t('urgencyGuidanceNote', 'Note: Urgency selection guides routing and does not replace emergency medical triage.')}
            </p>
          </div>

          {/* Buttons */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              {t('cancel', 'Cancel')}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 shadow-sm flex items-center gap-1.5 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> {t('submittingRequest', 'Submitting...')}
                </>
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" /> {t('submitRequestBtn', 'Submit Request')}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
