import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { SearchInput } from '../components/common/SearchInput';
import { FacilityCard } from '../components/facilities/FacilityCard';
import { FacilityDetailModal } from '../components/facilities/FacilityDetailModal';
import { BookAppointmentModal } from '../components/appointments/BookAppointmentModal';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Facility, FacilityType } from '../types';
import { facilityService } from '../services/facilityService';
import { Building2, Filter } from 'lucide-react';

const FACILITY_TYPES: { label: string; value: FacilityType | 'ALL' }[] = [
  { label: 'All Centers', value: 'ALL' },
  { label: 'Primary Health (PHC)', value: 'PHC' },
  { label: 'Community Health (CHC)', value: 'CHC' },
  { label: 'Hospitals', value: 'HOSPITAL' },
  { label: 'Pharmacies', value: 'PHARMACY' },
];

export const FacilitiesPage: React.FC = () => {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState<FacilityType | 'ALL'>('ALL');

  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);
  const [bookingFacility, setBookingFacility] = useState<Facility | null>(null);

  useEffect(() => {
    loadFacilities();
  }, []);

  const loadFacilities = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await facilityService.getFacilities();
      setFacilities(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load healthcare facilities.');
    } finally {
      setLoading(false);
    }
  };

  const filteredFacilities = facilities.filter((fac) => {
    const matchesType = selectedType === 'ALL' || fac.facility_type === selectedType;
    const q = search.toLowerCase().trim();
    const matchesSearch =
      !q ||
      fac.name.toLowerCase().includes(q) ||
      (fac.district && fac.district.toLowerCase().includes(q)) ||
      (fac.services || []).some((s) => s.toLowerCase().includes(q));
    return matchesType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Healthcare Facilities Directory"
        subtitle="Locate verified rural primary health centers, community clinics, and public medicine dispensaries"
      />

      {/* Controls: Search and Filters */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="w-full md:w-80">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search by facility name, district, or service..."
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto pb-1 md:pb-0">
          <Filter className="w-4 h-4 text-slate-400 mr-1 flex-shrink-0" />
          {FACILITY_TYPES.map((type) => (
            <button
              key={type.value}
              onClick={() => setSelectedType(type.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-colors ${
                selectedType === type.value
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <LoadingState message="Fetching healthcare facilities..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadFacilities} />
      ) : filteredFacilities.length === 0 ? (
        <EmptyState
          title="No facilities found"
          message="No healthcare facilities matched your query or filter criteria. Try adjusting your search term."
          actionLabel="Clear Filters"
          onAction={() => {
            setSearch('');
            setSelectedType('ALL');
          }}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredFacilities.map((fac) => (
            <FacilityCard
              key={fac.id}
              facility={fac}
              onViewDetails={(f) => setSelectedFacility(f)}
              onBookAppointment={(f) => setBookingFacility(f)}
            />
          ))}
        </div>
      )}

      {/* Facility Detail Modal */}
      {selectedFacility && (
        <FacilityDetailModal
          facility={selectedFacility}
          onClose={() => setSelectedFacility(null)}
          onBookAppointment={(f) => {
            setSelectedFacility(null);
            setBookingFacility(f);
          }}
        />
      )}

      {/* Book Appointment Modal */}
      {bookingFacility && (
        <BookAppointmentModal
          isOpen={!!bookingFacility}
          onClose={() => setBookingFacility(null)}
          initialFacilityId={bookingFacility.id}
        />
      )}
    </div>
  );
};
