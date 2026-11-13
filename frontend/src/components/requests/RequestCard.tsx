import React from 'react';
import { HealthcareRequest } from '../../types';
import { getRequestTypeLabel } from '../../lib/constants';
import { formatDate } from '../../lib/utils';
import { StatusBadge } from '../common/StatusBadge';
import { useTranslation } from '../../context/LanguageContext';
import { Calendar, ChevronRight, FileText, Sparkles } from 'lucide-react';

interface RequestCardProps {
  request: HealthcareRequest;
  onViewRecommendations?: (request: HealthcareRequest) => void;
}

export const RequestCard: React.FC<RequestCardProps> = ({
  request,
  onViewRecommendations,
}) => {
  const { t } = useTranslation();
  const typeLabel = getRequestTypeLabel(request.request_type, t);
  const hasRecommendations = request.recommendations && request.recommendations.length > 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm p-5 hover:border-healthcare-300 transition-all duration-200 flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            <span
              className="text-xs font-mono font-bold text-slate-500 uppercase bg-slate-100 px-2 py-0.5 rounded"
              title={request.id}
            >
              #{request.id.length > 12 ? request.id.slice(0, 8) : request.id}
            </span>
            <span className="text-xs font-semibold text-navy-900">{typeLabel}</span>
          </div>
          <StatusBadge status={request.urgency} type="urgency" />
        </div>

        {request.title && (
          <h4 className="text-sm font-bold text-slate-900 mt-1 mb-0.5">
            {request.title}
          </h4>
        )}

        <p className="text-xs text-slate-700 leading-relaxed font-normal">
          {request.description}
        </p>

        {request.camp_id && (
          <span className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200 mr-2">
            Health Camp Follow-up
          </span>
        )}

        {request.preferred_date && (
          <span className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-slate-700 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
            Target: {request.preferred_date}
          </span>
        )}

        {request.medicine_name && (
          <p className="mt-2 text-xs font-medium text-healthcare-800 bg-healthcare-50/70 p-2 rounded-lg border border-healthcare-100 inline-block">
            {t('targetMedicine', { name: request.medicine_name })}
          </p>
        )}

        <div className="mt-3.5 flex items-center gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5 text-slate-400" />
            {t('createdOn', 'Created')} {formatDate(request.created_at, t)}
          </span>
          <span className="flex items-center gap-1">
            <FileText className="h-3.5 w-3.5 text-slate-400" />
            {t('statusLabel', 'Status:')} <strong className="text-slate-800">{request.status}</strong>
          </span>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
        {hasRecommendations ? (
          <span className="text-xs font-medium text-emerald-700 flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
            {t('recommendedFacilitiesReady', { count: request.recommendations!.length })}
          </span>
        ) : (
          <span className="text-xs text-slate-400">{t('processingFacilityAvailability', 'Processing facility availability...')}</span>
        )}

        {onViewRecommendations && (
          <button
            type="button"
            onClick={() => onViewRecommendations(request)}
            className="text-xs font-semibold text-healthcare-700 hover:text-healthcare-800 flex items-center gap-1 transition-colors px-2 py-1 rounded hover:bg-healthcare-50"
          >
            {t('reviewRecommendations', 'Review Recommendations')} <ChevronRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};
