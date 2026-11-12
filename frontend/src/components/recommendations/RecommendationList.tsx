import React from 'react';
import { RecommendationItem } from '../../types';
import { formatCurrency, formatDistance } from '../../lib/utils';
import { StatusBadge } from '../common/StatusBadge';
import { Sparkles, Calendar, Navigation, Coins, ShieldCheck, AlertCircle, Loader2 } from 'lucide-react';

interface RecommendationListProps {
  recommendations: RecommendationItem[];
  loading?: boolean;
  onBookFacility?: (facilityId: string) => void;
  onSelect?: (item: RecommendationItem) => void;
}

export const RecommendationList: React.FC<RecommendationListProps> = ({
  recommendations,
  loading,
  onBookFacility,
  onSelect,
}) => {
  if (loading) {
    return (
      <div className="p-8 bg-white rounded-xl text-center text-xs text-slate-500 border border-slate-200 flex flex-col items-center justify-center gap-2">
        <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
        <span>Evaluating Bayesian facility suitability & travel loss models...</span>
      </div>
    );
  }

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="p-6 bg-slate-50 rounded-xl text-center text-xs text-slate-500 border border-slate-200">
        No facility recommendations currently computed for this request.
      </div>
    );
  }

  const handleAction = (rec: RecommendationItem) => {
    if (onSelect) {
      onSelect(rec);
    } else if (onBookFacility) {
      onBookFacility(rec.facility_id);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-emerald-600" />
          Optimal Facility Recommendations
        </h4>
        <span className="text-xs text-slate-500">
          Ranked by Bayesian suitability & expected travel loss
        </span>
      </div>

      <div className="space-y-3">
        {recommendations.map((rec) => (
          <div
            key={rec.facility_id}
            className={`p-4 rounded-xl border bg-white shadow-xs transition-all ${
              rec.rank === 1
                ? 'border-emerald-400 ring-1 ring-emerald-400/20 bg-emerald-50/20'
                : 'border-slate-200'
            }`}
          >
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold ${
                      rec.rank === 1
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-200 text-slate-700'
                    }`}
                  >
                    #{rec.rank} Optimal Match
                  </span>
                  <h5 className="text-sm font-bold text-slate-900">{rec.facility_name}</h5>
                </div>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">{rec.explanation}</p>
              </div>

              {(onSelect || onBookFacility) && (
                <button
                  type="button"
                  onClick={() => handleAction(rec)}
                  className="flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors shadow-2xs"
                >
                  <Calendar className="h-3.5 w-3.5" /> Book Here
                </button>
              )}
            </div>

            {/* Metrics Breakdown */}
            <div className="mt-3.5 pt-3 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              {rec.travel_distance_km !== undefined && (
                <div className="flex items-center gap-1 text-slate-600">
                  <Navigation className="h-3.5 w-3.5 text-slate-400" />
                  <span>{formatDistance(rec.travel_distance_km)}</span>
                </div>
              )}
              {rec.travel_cost !== undefined && (
                <div className="flex items-center gap-1 text-slate-600">
                  <Coins className="h-3.5 w-3.5 text-slate-400" />
                  <span>Est. Travel: {formatCurrency(rec.travel_cost)}</span>
                </div>
              )}
              {rec.failure_probability !== undefined && (
                <div className="flex items-center gap-1 text-slate-600">
                  <AlertCircle className="h-3.5 w-3.5 text-amber-500" />
                  <span>Stockout Risk: {(rec.failure_probability * 100).toFixed(0)}%</span>
                </div>
              )}
              {rec.expected_loss !== undefined && (
                <div className="flex items-center gap-1 font-medium text-emerald-800">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                  <span>Expected Loss: {rec.expected_loss.toFixed(1)}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
