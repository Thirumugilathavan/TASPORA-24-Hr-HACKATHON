import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { RequestCard } from '../components/requests/RequestCard';
import { CreateRequestModal } from '../components/requests/CreateRequestModal';
import { RecommendationList } from '../components/recommendations/RecommendationList';
import { BookAppointmentModal } from '../components/appointments/BookAppointmentModal';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { HealthcareRequest, RecommendationItem } from '../types';
import { requestService } from '../services/requestService';
import { recommendationService } from '../services/recommendationService';
import { useNotification } from '../context/NotificationContext';
import { PlusCircle, Sparkles, Filter, X } from 'lucide-react';

const STATUS_FILTERS = ['ALL', 'PENDING', 'RECOMMENDED', 'BOOKED', 'COMPLETED'];

export const RequestsPage: React.FC = () => {
  const { notify } = useNotification();

  const [requests, setRequests] = useState<HealthcareRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Selected request for viewing recommendations
  const [selectedRequest, setSelectedRequest] = useState<HealthcareRequest | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [loadingRecs, setLoadingRecs] = useState(false);

  // Booking from recommendation
  const [bookingDetails, setBookingDetails] = useState<{
    facilityId: string;
    requestId: string;
  } | null>(null);

  useEffect(() => {
    loadRequests();
  }, []);

  const loadRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await requestService.getRequests();
      setRequests(data);
      if (data.length > 0 && !selectedRequest) {
        handleSelectRequest(data[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load requests.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectRequest = async (req: HealthcareRequest) => {
    setSelectedRequest(req);
    try {
      setLoadingRecs(true);
      const recs = await recommendationService.getRecommendations(req.id);
      setRecommendations(recs);
    } catch (err) {
      console.error('Failed to load recommendations', err);
      setRecommendations([]);
    } finally {
      setLoadingRecs(false);
    }
  };

  const handleSelectRecommendation = (item: RecommendationItem) => {
    if (!selectedRequest) return;
    setBookingDetails({
      facilityId: item.facility_id,
      requestId: selectedRequest.id,
    });
  };

  const filteredRequests = requests.filter((r) => {
    if (statusFilter === 'ALL') return true;
    return r.status === statusFilter;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <PageHeader
          title="Care Requests & AI Optimization"
          subtitle="Smart routing minimizing travel cost and avoiding stockout risk for rural patients"
        />
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-xl shadow-sm transition-colors flex-shrink-0"
        >
          <PlusCircle className="w-4 h-4" />
          Create Care Request
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm flex items-center gap-1.5 overflow-x-auto">
        <Filter className="w-4 h-4 text-slate-400 mr-2 flex-shrink-0" />
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-colors ${
              statusFilter === s
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Main Two-Column Layout */}
      {loading ? (
        <LoadingState message="Loading care requests..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadRequests} />
      ) : filteredRequests.length === 0 ? (
        <EmptyState
          title="No requests found"
          message="No healthcare requests found for this filter. Create one to get started."
          actionLabel="Create Request"
          onAction={() => setIsCreateModalOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Requests List (5 cols on large screens) */}
          <div className="lg:col-span-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-700 px-1">
              Requests List ({filteredRequests.length})
            </h3>
            {filteredRequests.map((req) => (
              <div
                key={req.id}
                onClick={() => handleSelectRequest(req)}
                className={`cursor-pointer transition-all rounded-xl ${
                  selectedRequest?.id === req.id
                    ? 'ring-2 ring-emerald-500 shadow-md'
                    : 'hover:border-slate-300'
                }`}
              >
                <RequestCard
                  request={req}
                  onViewRecommendations={(r) => handleSelectRequest(r)}
                />
              </div>
            ))}
          </div>

          {/* Recommendations Detail Panel (7 cols on large screens) */}
          <div className="lg:col-span-7">
            {selectedRequest ? (
              <div className="space-y-4">
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
                  <div>
                    <span className="text-xs font-medium text-emerald-600 uppercase tracking-wider">
                      Selected Request
                    </span>
                    <h3 className="text-base font-semibold text-slate-900 mt-0.5">
                      {selectedRequest.request_type} — {selectedRequest.description}
                    </h3>
                  </div>
                  <span className="text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 font-medium">
                    ID: #{selectedRequest.id.slice(-6).toUpperCase()}
                  </span>
                </div>

                <RecommendationList
                  recommendations={recommendations}
                  loading={loadingRecs}
                  onSelect={handleSelectRecommendation}
                />
              </div>
            ) : (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-8 text-center text-slate-500">
                <Sparkles className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-medium">Select a request from the list</p>
                <p className="text-xs text-slate-400 mt-1">
                  View automated Bayesian facility suitability and expected travel loss rankings
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modals */}
      <CreateRequestModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreated={(newReq) => {
          setRequests([newReq, ...requests]);
          handleSelectRequest(newReq);
          notify('Request created and optimized route calculated!', 'success');
        }}
      />

      {bookingDetails && (
        <BookAppointmentModal
          isOpen={!!bookingDetails}
          onClose={() => setBookingDetails(null)}
          initialFacilityId={bookingDetails.facilityId}
          requestId={bookingDetails.requestId}
          onSuccess={() => {
            // Update request status to BOOKED
            setRequests((prev) =>
              prev.map((r) =>
                r.id === bookingDetails.requestId ? { ...r, status: 'BOOKED' as const } : r
              )
            );
          }}
        />
      )}
    </div>
  );
};
