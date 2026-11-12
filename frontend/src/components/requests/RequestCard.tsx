import React from 'react';
import { HealthcareRequest } from '../../types';
import { REQUEST_TYPE_LABELS } from '../../lib/constants';
import { formatDate } from '../../lib/utils';
import { StatusBadge } from '../common/StatusBadge';
import { Calendar, ChevronRight, FileText, Sparkles } from 'lucide-react';

interface RequestCardProps {
  request: HealthcareRequest;
  onViewRecommendations?: (request: HealthcareRequest) => void;
}

export const RequestCard: React.FC<RequestCardProps> = ({
  request,
  onViewRecommendations,
}) => {
  const typeLabel = REQUEST_TYPE_LABELS[request.request_type] || request.request_type;
  const hasRecommendations = request.recommendations && request.recommendations.length > 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm p-5 hover:border-healthcare-300 transition-all duration-200 flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold text-slate-500 uppercase bg-slate-100 px-2 py-0.5 rounded">
              #{request.id}
            </span>
            <span className="text-xs font-semibold text-navy-900">{typeLabel}</span>
          </div>
          <StatusBadge status={request.urgency} type="urgency" />
        </div>

        <p className="text-sm text-slate-700 mt-2 leading-relaxed font-normal">
          {request.description}
        </p>

        {request.medicine_name && (
          <p className="mt-2 text-xs font-medium text-healthcare-800 bg-healthcare-50/70 p-2 rounded-lg border border-healthcare-100 inline-block">
            Target Medicine: {request.medicine_name}
          </p>
        )}

        <div className="mt-3.5 flex items-center gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5 text-slate-400" />
            Created {formatDate(request.created_at)}
          </span>
          <span className="flex items-center gap-1">
            <FileText className="h-3.5 w-3.5 text-slate-400" />
            Status: <strong className="text-slate-800">{request.status}</strong>
          </span>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
        {hasRecommendations ? (
          <span className="text-xs font-medium text-emerald-700 flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
            {request.recommendations!.length} Recommended Facilities Ready
          </span>
        ) : (
          <span className="text-xs text-slate-400">Processing facility availability...</span>
        )}

        {onViewRecommendations && (
          <button
            type="button"
            onClick={() => onViewRecommendations(request)}
            className="text-xs font-semibold text-healthcare-700 hover:text-healthcare-800 flex items-center gap-1 transition-colors px-2 py-1 rounded hover:bg-healthcare-50"
          >
            Review Recommendations <ChevronRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};
