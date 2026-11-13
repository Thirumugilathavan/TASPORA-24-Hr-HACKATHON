import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  Pill,
  ClipboardList,
  Calendar,
  PlusCircle,
  MapPin,
  ArrowRight,
  Sparkles,
  PhoneCall,
  Activity,
  HeartPulse,
  Bot,
  Mic,
  Tent,
  Landmark,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { StatCard } from '../components/common/StatCard';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { AppointmentCard } from '../components/appointments/AppointmentCard';
import { BookAppointmentModal } from '../components/appointments/BookAppointmentModal';
import { CreateRequestModal } from '../components/requests/CreateRequestModal';
import { RequestCard } from '../components/requests/RequestCard';
import { FacilityDetailModal } from '../components/facilities/FacilityDetailModal';
import { NearbyFacilitiesSection } from '../components/facilities/NearbyFacilitiesSection';
import { Facility, HealthcareRequest, Appointment } from '../types';
import { facilityService } from '../services/facilityService';
import { requestService } from '../services/requestService';
import { appointmentService } from '../services/appointmentService';
import { useNotification } from '../context/NotificationContext';
import { ConfirmDialog } from '../components/common/ConfirmDialog';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, currentPatient } = useAuth();
  const { notify } = useNotification();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [requests, setRequests] = useState<HealthcareRequest[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);

  // Modals state
  const [isBookModalOpen, setIsBookModalOpen] = useState(false);
  const [isRequestModalOpen, setIsRequestModalOpen] = useState(false);
  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);

  // Cancel dialog
  const [cancelTarget, setCancelTarget] = useState<Appointment | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [nearbyRes, reqData, apptData] = await Promise.all([
        facilityService.getNearbyFacilities({
          latitude: currentPatient?.village?.latitude,
          longitude: currentPatient?.village?.longitude,
          village_id: currentPatient?.village?.id,
          radius_km: 15,
          limit: 10,
        }).catch(() => ({ items: [], total: 0 })),
        requestService.getRequests().catch(() => []),
        appointmentService.getAppointments().catch(() => []),
      ]);

      setFacilities(nearbyRes.items || []);
      setRequests(reqData);
      setAppointments(apptData);
    } catch (err: any) {
      setError(err.message || 'Unable to load dashboard data. Please check connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmCancel = async () => {
    if (!cancelTarget) return;
    try {
      await appointmentService.cancelAppointment(cancelTarget.id);
      notify('Appointment cancelled successfully.', 'info');
      setCancelTarget(null);
      // Refresh appointments
      const updated = await appointmentService.getAppointments();
      setAppointments(updated);
    } catch (err: any) {
      notify(err.message || 'Failed to cancel appointment', 'error');
    }
  };

  if (loading) {
    return <LoadingState message="Loading your healthcare dashboard..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadDashboardData} />;
  }

  const upcomingAppointments = appointments.filter(
    (a) => a.status === 'BOOKED' || a.status === 'CONFIRMED'
  );
  const pendingRequests = requests.filter((r) => r.status === 'PENDING' || r.status === 'RECOMMENDED');

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-700 rounded-2xl p-6 text-white shadow-lg shadow-emerald-700/10 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/15 backdrop-blur-sm text-xs font-medium text-emerald-100 mb-2">
            <HeartPulse className="w-3.5 h-3.5" />
            Rural Healthcare Coordination Active
          </div>
          <h1 className="text-2xl font-bold tracking-tight">
            Welcome back, {user?.name || 'Patient'}!
          </h1>
          <p className="text-emerald-100 text-sm mt-1 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-emerald-300" />
            Home Village: <strong>{currentPatient?.village?.name || 'Thiruvallur District'}</strong>
            <span className="text-emerald-300">•</span>
            Registered Phone: <strong>{user?.phone || '9876543210'}</strong>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => window.dispatchEvent(new CustomEvent('open-nalam-ai'))}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-teal-500 to-emerald-600 hover:from-teal-600 hover:to-emerald-700 text-white font-semibold text-sm rounded-xl shadow-md hover:shadow-lg transition-all border border-emerald-400/30 cursor-pointer"
          >
            <Bot className="w-4 h-4 text-emerald-100" />
            <Mic className="w-3.5 h-3.5 text-teal-200" />
            Talk to NALAM (AI Voice)
          </button>
          <button
            onClick={() => setIsRequestModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-white text-emerald-800 font-medium text-sm rounded-xl shadow-sm hover:bg-emerald-50 transition-colors"
          >
            <PlusCircle className="w-4 h-4 text-emerald-600" />
            Create Request
          </button>
          <button
            onClick={() => setIsBookModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-800/60 hover:bg-emerald-800/80 text-white font-medium text-sm rounded-xl border border-white/20 transition-colors"
          >
            <Calendar className="w-4 h-4" />
            Book Visit
          </button>
        </div>
      </div>

      {/* Prominent NALAM Voice & Chatbot Banner */}
      <div className="bg-gradient-to-r from-teal-900 via-teal-800 to-slate-900 rounded-2xl p-4 sm:p-5 text-white shadow-md border border-teal-700/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-xl bg-teal-500/20 border border-teal-400/30 flex items-center justify-center shrink-0">
            <Bot className="w-6 h-6 text-teal-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-base tracking-wide">NALAM Multilingual Voice Assistant</h3>
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 rounded-full">
                Gnani.ai Voice Cloud
              </span>
            </div>
            <p className="text-xs text-teal-100/80 mt-0.5">
              Speak or type in Tamil (தமிழ்) or English to find nearby PHCs, verify doctor attendance, or check medicine stock.
            </p>
          </div>
        </div>
        <button
          onClick={() => window.dispatchEvent(new CustomEvent('open-nalam-ai'))}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-bold text-xs sm:text-sm rounded-xl shadow-md transition-all shrink-0 cursor-pointer"
        >
          <Mic className="w-4 h-4" />
          Speak to NALAM
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Nearby Facilities"
          value={facilities.length}
          subtitle={currentPatient?.village?.name ? `Near ${currentPatient.village.name}` : 'Ranked by distance'}
          icon={<Building2 className="w-5 h-5 text-emerald-600" />}
        />
        <StatCard
          title="Active Requests"
          value={pendingRequests.length}
          subtitle="Awaiting dispatch or visits"
          icon={<ClipboardList className="w-5 h-5 text-sky-600" />}
        />
        <StatCard
          title="Upcoming Visits"
          value={upcomingAppointments.length}
          subtitle="Confirmed doctor slots"
          icon={<Calendar className="w-5 h-5 text-amber-600" />}
        />
        <StatCard
          title="ASHA Support"
          value="Online"
          subtitle="Village health coordinator"
          icon={<Activity className="w-5 h-5 text-purple-600" />}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Healthcare Facilities Near You (Distance-Ranked NIC Facilities) */}
          <NearbyFacilitiesSection
            onSelectFacility={(fac) => setSelectedFacility(fac)}
            initialRadius={10}
          />

          {/* Upcoming Appointments */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Upcoming Appointments</h2>
                <p className="text-xs text-slate-500">Scheduled consultations at primary centers</p>
              </div>
              <button
                onClick={() => navigate('/appointments')}
                className="text-xs font-medium text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
              >
                View all ({appointments.length})
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {upcomingAppointments.length === 0 ? (
              <div className="py-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                <Calendar className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-medium text-slate-600">No appointments scheduled</p>
                <p className="text-xs text-slate-400 mt-0.5">Need to see a doctor at the local PHC?</p>
                <button
                  onClick={() => setIsBookModalOpen(true)}
                  className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-700 bg-emerald-100/70 hover:bg-emerald-100 rounded-lg transition-colors"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  Book an Appointment
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {upcomingAppointments.slice(0, 2).map((appt) => (
                  <AppointmentCard
                    key={appt.id}
                    appointment={appt}
                    onCancel={(target) => setCancelTarget(target)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Recent Requests */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Recent Healthcare Requests</h2>
                <p className="text-xs text-slate-500">Refill, consultation, and diagnostic requests</p>
              </div>
              <button
                onClick={() => navigate('/requests')}
                className="text-xs font-medium text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
              >
                View all ({requests.length})
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {requests.length === 0 ? (
              <div className="py-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                <ClipboardList className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-medium text-slate-600">No recent requests</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  Submit a request for medicine refills or specialist checks
                </p>
                <button
                  onClick={() => setIsRequestModalOpen(true)}
                  className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-700 bg-emerald-100/70 hover:bg-emerald-100 rounded-lg transition-colors"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  Create Request
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {requests.slice(0, 3).map((req) => (
                  <RequestCard
                    key={req.id}
                    request={req}
                    onViewRecommendations={() => navigate('/requests')}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (1 col) */}
        <div className="space-y-6">
          {/* No Wasted Trips Travel Advisory */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-700">
                <HeartPulse className="w-4 h-4 text-emerald-600" />
              </span>
              <h2 className="text-sm font-bold text-slate-900">No Wasted Trips Policy</h2>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              NALAM ranks nearby healthcare facilities by precise geographic distance from your registered village or device GPS.
            </p>
            <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs space-y-1.5 text-slate-600">
              <p className="font-semibold text-slate-800 flex items-center gap-1.5">
                <span className="text-emerald-600">✓</span> 147k+ Government Health Centers
              </p>
              <p className="font-semibold text-slate-800 flex items-center gap-1.5">
                <span className="text-emerald-600">✓</span> Real Census coordinate resolution
              </p>
              <p className="text-[11px] text-slate-500 pt-1">
                Before travelling for urgent medication or specialist care, create a request or confirm attendance.
              </p>
            </div>
            <button
              onClick={() => navigate('/facilities')}
              className="mt-3.5 w-full py-2 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg transition-colors flex items-center justify-center gap-1.5"
            >
              Browse All Facilities Directory
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Quick Helpline Box */}
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl p-5 text-white shadow-sm">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <PhoneCall className="w-4 h-4 text-emerald-400" />
              Emergency Help Desks
            </h3>
            <p className="text-xs text-slate-300 mt-1">
              Direct hotlines for ambulance and maternal support:
            </p>

            <div className="mt-4 space-y-2">
              <a
                href="tel:108"
                className="flex items-center justify-between p-2.5 rounded-lg bg-white/10 hover:bg-white/15 transition-colors text-sm"
              >
                <span className="font-medium">108 Emergency Ambulance</span>
                <span className="px-2 py-0.5 rounded bg-rose-500/80 text-white font-bold text-xs">FREE</span>
              </a>
              <a
                href="tel:102"
                className="flex items-center justify-between p-2.5 rounded-lg bg-white/10 hover:bg-white/15 transition-colors text-sm"
              >
                <span className="font-medium">102 Janani Shishu Helpline</span>
                <span className="px-2 py-0.5 rounded bg-emerald-500/80 text-white font-bold text-xs">FREE</span>
              </a>
            </div>
          </div>

          {/* Health Camps Quick Access */}
          <div className="bg-gradient-to-br from-teal-50 to-cyan-50 border border-teal-200 rounded-xl p-5 shadow-sm">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-teal-600 flex items-center justify-center shrink-0">
                  <Tent className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-slate-900">Health Camps</h3>
                  <p className="text-xs text-slate-500">Free camps near your area</p>
                </div>
              </div>
            </div>
            <p className="text-xs text-slate-600 mb-3">
              Discover official Tamil Nadu health camps, Mobile Medical Units, and free screening drives. Book follow-up appointments directly.
            </p>
            <button
              onClick={() => navigate('/camps')}
              className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-lg transition-colors"
            >
              <Tent className="w-3.5 h-3.5" />
              View Health Camps & Follow-up
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Government Schemes Quick Access */}
          <div className="bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-5 shadow-sm">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-amber-600 flex items-center justify-center shrink-0">
                  <Landmark className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-slate-900">அரசு நலத்திட்டங்கள்</h3>
                  <p className="text-xs text-slate-500">Government Welfare Schemes</p>
                </div>
              </div>
            </div>
            <p className="text-xs text-slate-600 mb-3">
              Find Central & Tamil Nadu state schemes you may be eligible for — health insurance, financial aid, scholarships, and more.
            </p>
            <button
              onClick={() => navigate('/schemes')}
              className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-lg transition-colors"
            >
              <Landmark className="w-3.5 h-3.5" />
              Find Schemes for Me
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Modals */}
      <CreateRequestModal
        isOpen={isRequestModalOpen}
        onClose={() => setIsRequestModalOpen(false)}
        onCreated={(req) => {
          setRequests([req, ...requests]);
          notify('Request submitted successfully with AI routing!', 'success');
        }}
      />

      <BookAppointmentModal
        isOpen={isBookModalOpen}
        onClose={() => setIsBookModalOpen(false)}
        onSuccess={(appt) => {
          setAppointments([appt, ...appointments]);
        }}
      />

      {selectedFacility && (
        <FacilityDetailModal
          facility={selectedFacility}
          onClose={() => setSelectedFacility(null)}
          onBookAppointment={() => {
            setSelectedFacility(null);
            setIsBookModalOpen(true);
          }}
        />
      )}

      {/* Cancel Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!cancelTarget}
        title="Cancel Appointment"
        message={`Are you sure you want to cancel your appointment at ${cancelTarget?.facility_name} on ${cancelTarget?.appointment_date}?`}
        confirmLabel="Yes, Cancel"
        cancelLabel="Keep Appointment"
        isDestructive
        onConfirm={handleConfirmCancel}
        onCancel={() => setCancelTarget(null)}
      />
    </div>
  );
};
