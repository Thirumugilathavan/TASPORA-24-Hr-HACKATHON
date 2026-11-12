import React, { useState, useEffect, useCallback } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { SearchInput } from '../components/common/SearchInput';
import { LocationSearchInput } from '../components/common/LocationSearchInput';
import { FacilityDetailModal } from '../components/facilities/FacilityDetailModal';
import { BookAppointmentModal } from '../components/appointments/BookAppointmentModal';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Facility, Village, NearbyFacilityListResponse } from '../types';
import { facilityService } from '../services/facilityService';
import { FACILITY_TYPE_LABELS } from '../lib/constants';
import { useAuth } from '../context/AuthContext';
import {
  MapPin,
  Navigation,
  ExternalLink,
  ChevronRight,
  RefreshCw,
  Compass,
  Building2,
  AlertCircle,
  Filter,
  Info,
  CheckCircle2,
} from 'lucide-react';

const RADIUS_OPTIONS = [5, 10, 25, 50, 100];

const TYPE_FILTER_OPTIONS = [
  { label: 'All Centers', value: 'ALL' },
  { label: 'Sub-Centres (SCE)', value: 'SCE' },
  { label: 'Primary Health (PHC)', value: 'PHC' },
  { label: 'Community Health (CHC)', value: 'CHC' },
  { label: 'Hospitals (THO/DHO)', value: 'HOSPITAL' },
];

export const FacilitiesPage: React.FC = () => {
  const { user, currentPatient } = useAuth();

  // Location State
  const [activeLocation, setActiveLocation] = useState<Village | null>(null);
  const [isChangingLocation, setIsChangingLocation] = useState(false);
  const [usingGps, setUsingGps] = useState(false);
  const [gpsCoords, setGpsCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsError, setGpsError] = useState<string | null>(null);

  // Filter & Query State
  const [radiusKm, setRadiusKm] = useState<number>(10);
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [search, setSearch] = useState<string>('');

  // Results State
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [resolvedMeta, setResolvedMeta] = useState<NearbyFacilityListResponse['resolved_location'] | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [pageOffset, setPageOffset] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);

  const PAGE_SIZE = 24;

  // Modals
  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);
  const [bookingFacility, setBookingFacility] = useState<Facility | null>(null);

  // Initialize location from registered user profile or session
  useEffect(() => {
    if (currentPatient?.village?.latitude && currentPatient?.village?.longitude) {
      setActiveLocation(currentPatient.village);
      setIsChangingLocation(false);
    } else {
      const saved = sessionStorage.getItem('carebridge_active_village');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          if (parsed && parsed.latitude && parsed.longitude) {
            setActiveLocation(parsed);
            setIsChangingLocation(false);
            return;
          }
        } catch {
          // ignore
        }
      }
      setIsChangingLocation(true);
    }
  }, [currentPatient]);

  const loadFacilities = useCallback(
    async (offset: number = 0, append: boolean = false) => {
      // Require reliable location
      const hasGps = usingGps && gpsCoords;
      const hasVillage = activeLocation && activeLocation.latitude && activeLocation.longitude;

      if (!hasGps && !hasVillage) {
        setFacilities([]);
        setTotalCount(0);
        setLoading(false);
        return;
      }

      try {
        if (append) {
          setLoadingMore(true);
        } else {
          setLoading(true);
        }
        setError(null);

        const params: Parameters<typeof facilityService.getNearbyFacilities>[0] = {
          radius_km: radiusKm,
          facility_type: selectedType === 'ALL' ? undefined : selectedType,
          limit: PAGE_SIZE,
          skip: offset,
        };

        if (hasGps) {
          params.latitude = gpsCoords.lat;
          params.longitude = gpsCoords.lon;
        } else if (hasVillage) {
          params.latitude = activeLocation.latitude;
          params.longitude = activeLocation.longitude;
          params.village_id = activeLocation.id;
        }

        const res = await facilityService.getNearbyFacilities(params);

        if (append) {
          setFacilities((prev) => [...prev, ...(res.items || [])]);
        } else {
          setFacilities(res.items || []);
        }

        setTotalCount(res.total || 0);
        setResolvedMeta(res.resolved_location || null);
        setPageOffset(offset);
        setHasMore((offset + (res.items || []).length) < (res.total || 0));
      } catch (err: any) {
        setError(err.message || 'Failed to fetch nearby facilities from registry.');
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [usingGps, gpsCoords, activeLocation, radiusKm, selectedType]
  );

  useEffect(() => {
    loadFacilities(0, false);
  }, [loadFacilities]);

  const handleShowMore = () => {
    if (!hasMore || loadingMore) return;
    const nextOffset = pageOffset + PAGE_SIZE;
    loadFacilities(nextOffset, true);
  };

  const handleLocationSelect = (village: Village | null) => {
    if (village && village.latitude && village.longitude) {
      setActiveLocation(village);
      setUsingGps(false);
      setGpsCoords(null);
      setIsChangingLocation(false);
      sessionStorage.setItem('carebridge_active_village', JSON.stringify(village));
    }
  };

  const handleToggleGps = () => {
    if (usingGps) {
      setUsingGps(false);
      setGpsCoords(null);
      setGpsError(null);
      return;
    }

    if (!navigator.geolocation) {
      setGpsError('Geolocation is not supported by your browser.');
      return;
    }

    setGpsLoading(true);
    setGpsError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGpsCoords({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        });
        setUsingGps(true);
        setGpsLoading(false);
        setIsChangingLocation(false);
      },
      (err) => {
        setGpsLoading(false);
        let msg = 'Unable to retrieve device GPS location.';
        if (err.code === err.PERMISSION_DENIED) {
          msg = 'Location permission denied. Please select your registered village.';
        } else if (err.code === err.TIMEOUT) {
          msg = 'GPS request timed out. Please select your registered village.';
        }
        setGpsError(msg);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  // Client-side text filter on the currently loaded page/results
  const filteredFacilities = facilities.filter((fac) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase().trim();
    return (
      fac.name.toLowerCase().includes(q) ||
      (fac.district && fac.district.toLowerCase().includes(q)) ||
      (fac.address && fac.address.toLowerCase().includes(q)) ||
      (fac.subdistrict && fac.subdistrict.toLowerCase().includes(q))
    );
  });

  const currentLocationLabel = usingGps
    ? `Device GPS (${gpsCoords?.lat.toFixed(4)}, ${gpsCoords?.lon.toFixed(4)})`
    : activeLocation
    ? `${activeLocation.name}, ${activeLocation.district}${activeLocation.state ? `, ${activeLocation.state}` : ''}`
    : 'No location selected';

  const isUserRegisteredVillage =
    !usingGps &&
    activeLocation &&
    currentPatient?.village?.id &&
    activeLocation.id === currentPatient.village.id;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Healthcare Facilities Directory"
        subtitle="Dynamic straight-line distance ranking from your registered location using official MOHFW/NIC registry"
      />

      {/* Location Resolution Bar */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-start sm:items-center gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-700">
              <Compass className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Reference Location:
                </span>
                {isUserRegisteredVillage && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                    <CheckCircle2 className="w-3 h-3 text-emerald-700" />
                    Registered Profile Location
                  </span>
                )}
                {usingGps && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-sky-100 text-sky-800">
                    <Navigation className="w-3 h-3 text-sky-600" />
                    Live Device GPS
                  </span>
                )}
              </div>
              <h3 className="text-base font-bold text-slate-900 mt-0.5 flex items-center gap-1.5">
                <MapPin className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                {currentLocationLabel}
                {activeLocation?.latitude && !usingGps && (
                  <span className="text-xs font-mono font-normal text-slate-400">
                    ({activeLocation.latitude.toFixed(4)}, {activeLocation.longitude.toFixed(4)})
                  </span>
                )}
              </h3>
            </div>
          </div>

          {/* Location Actions: Change / GPS / Refresh */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setIsChangingLocation(!isChangingLocation)}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 bg-white hover:bg-slate-50 transition-colors"
            >
              {isChangingLocation ? 'Hide Location Selector' : 'Select / Change Location'}
            </button>

            <button
              onClick={handleToggleGps}
              disabled={gpsLoading}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                usingGps
                  ? 'bg-sky-50 border-sky-300 text-sky-700 hover:bg-sky-100'
                  : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <Navigation className={`w-3.5 h-3.5 ${usingGps ? 'text-sky-600' : 'text-slate-500'}`} />
              {gpsLoading ? 'Acquiring GPS...' : usingGps ? 'Using GPS' : 'Use Device GPS'}
            </button>

            <button
              onClick={() => loadFacilities(0, false)}
              disabled={loading}
              className="p-1.5 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
              title="Refresh nearby facilities"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
            </button>
          </div>
        </div>

        {/* Change / Select Location Selector Banner */}
        {isChangingLocation && (
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 animate-in fade-in duration-200">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Select Your Village, Town, or City
              </h4>
              <button
                onClick={() => setIsChangingLocation(false)}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                Close ✕
              </button>
            </div>
            <p className="text-xs text-slate-500 mb-3">
              Search nationwide database of 625,000+ Indian settlements to dynamically resolve accurate latitude and longitude coordinates.
            </p>
            <LocationSearchInput
              selectedVillageId={activeLocation?.id || ''}
              onSelect={handleLocationSelect}
              placeholder="Type village, town, or city name (e.g. Alangulam, Erode, Tiruchirappalli, Bilaspur)..."
            />
          </div>
        )}

        {gpsError && (
          <div className="text-xs text-amber-700 bg-amber-50 px-3 py-2 rounded-lg border border-amber-200 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span>{gpsError}</span>
          </div>
        )}

        {/* Filters & Radius Controls */}
        <div className="pt-3 border-t border-slate-100 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          {/* Radius Selector */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-semibold text-slate-600 mr-1">Search Radius:</span>
            {RADIUS_OPTIONS.map((r) => (
              <button
                key={r}
                onClick={() => setRadiusKm(r)}
                className={`px-3 py-1 text-xs rounded-lg font-semibold transition-all ${
                  radiusKm === r
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {r} km
              </button>
            ))}
          </div>

          {/* Facility Type Filter */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 lg:pb-0">
            <Filter className="w-3.5 h-3.5 text-slate-400 mr-1 flex-shrink-0" />
            {TYPE_FILTER_OPTIONS.map((type) => (
              <button
                key={type.value}
                onClick={() => setSelectedType(type.value)}
                className={`px-3 py-1 text-xs rounded-lg font-semibold whitespace-nowrap transition-colors ${
                  selectedType === type.value
                    ? 'bg-slate-800 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {type.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Search Input Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="w-full md:w-96">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Filter loaded results by name, place, district..."
          />
        </div>

        <div className="text-xs text-slate-500 font-medium w-full md:w-auto text-left md:text-right">
          {totalCount > 0 ? (
            <span>
              Showing <strong>{facilities.length}</strong> of <strong>{totalCount}</strong> facilities within {radiusKm} km (closest first)
            </span>
          ) : (
            <span>Radius: {radiusKm} km</span>
          )}
        </div>
      </div>

      {/* Low Count Progressive Expansion Banner */}
      {!loading && totalCount > 0 && totalCount < 4 && radiusKm < 50 && (
        <div className="p-3.5 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-900 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span>
              Only <strong>{totalCount}</strong> eligible {totalCount === 1 ? 'facility' : 'facilities'} found within {radiusKm} km of your location.
            </span>
          </div>
          <button
            onClick={() => setRadiusKm(radiusKm === 5 ? 10 : radiusKm === 10 ? 25 : 50)}
            className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-lg text-xs transition-colors self-start sm:self-auto"
          >
            Expand Search Radius →
          </button>
        </div>
      )}

      {/* Main Facilities Content */}
      {loading ? (
        <LoadingState message={`Calculating distances from ${currentLocationLabel}...`} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => loadFacilities(0, false)} />
      ) : !activeLocation && !usingGps ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-10 text-center space-y-4">
          <Compass className="w-12 h-12 text-emerald-600 mx-auto" />
          <h3 className="text-lg font-bold text-slate-800">Please Select Your Location</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            To view healthcare facilities automatically ranked by geographic distance, please select your village, town, or city above or enable device GPS.
          </p>
          <button
            onClick={() => setIsChangingLocation(true)}
            className="px-4 py-2 bg-emerald-600 text-white text-xs font-semibold rounded-xl hover:bg-emerald-700 transition-colors"
          >
            Select Village / City
          </button>
        </div>
      ) : filteredFacilities.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-10 text-center space-y-4">
          <Building2 className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-base font-bold text-slate-800">
            No healthcare facilities found within {radiusKm} km
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            There are no matching facilities within {radiusKm} km of {currentLocationLabel}. Try expanding your search radius to locate available regional centers.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
            {radiusKm < 25 && (
              <button
                onClick={() => setRadiusKm(25)}
                className="px-3.5 py-1.5 text-xs font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
              >
                Expand to 25 km
              </button>
            )}
            {radiusKm < 50 && (
              <button
                onClick={() => setRadiusKm(50)}
                className="px-3.5 py-1.5 text-xs font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
              >
                Expand to 50 km
              </button>
            )}
            {radiusKm < 100 && (
              <button
                onClick={() => setRadiusKm(100)}
                className="px-3.5 py-1.5 text-xs font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
              >
                Expand to 100 km
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Facilities Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredFacilities.map((fac, idx) => {
              const typeLabel = FACILITY_TYPE_LABELS[fac.facility_type] || fac.facility_type;
              const isFirst = idx === 0 && pageOffset === 0;

              return (
                <div
                  key={fac.id}
                  className={`bg-white rounded-2xl border p-5 shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between ${
                    isFirst ? 'border-emerald-300 ring-1 ring-emerald-200' : 'border-slate-200/90'
                  }`}
                >
                  <div className="space-y-2.5">
                    {/* Top Row: Rank & Distance Badge */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span
                          className={`text-xs px-2 py-0.5 rounded-md font-bold ${
                            isFirst ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          #{idx + 1} {isFirst ? 'Closest' : ''}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-md font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                          {typeLabel}
                        </span>
                      </div>

                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-900 border border-emerald-200 flex-shrink-0">
                        <MapPin className="w-3 h-3 text-emerald-700" />
                        {fac.distance_km !== undefined ? `${fac.distance_km} km away` : 'Near you'}
                      </span>
                    </div>

                    {/* Facility Name */}
                    <h3 className="text-base font-bold text-slate-900 leading-snug">
                      {fac.name}
                    </h3>

                    {/* Administrative Location & Address */}
                    <p className="text-xs text-slate-600 line-clamp-2">
                      {fac.address || `${fac.district || ''}, ${fac.state || ''}`}
                    </p>

                    {/* Ownership & Availability Notice */}
                    <div className="pt-2 flex flex-wrap items-center gap-2">
                      <span
                        className="inline-flex items-center gap-1 text-[11px] text-slate-500 bg-slate-50 px-2 py-0.5 rounded border border-slate-200"
                        title="Operational attendance and stock require live verification"
                      >
                        <Info className="w-3 h-3 text-slate-400" />
                        Availability not verified
                      </span>
                      {fac.ownership && (
                        <span className="text-[11px] text-slate-400">
                          {fac.ownership}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions: Directions and Details */}
                  <div className="mt-5 pt-3.5 border-t border-slate-100 flex items-center justify-between gap-2">
                    {fac.directions_url ? (
                      <a
                        href={fac.directions_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 hover:text-emerald-800 transition-colors py-1"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        Directions ↗
                      </a>
                    ) : (
                      <div />
                    )}

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setSelectedFacility(fac)}
                        className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center gap-1"
                      >
                        Details
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>

                      <button
                        type="button"
                        onClick={() => setBookingFacility(fac)}
                        className="px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors shadow-xs"
                      >
                        Book Slot
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Show More Facilities / Pagination Action */}
          {hasMore && (
            <div className="py-6 text-center">
              <button
                onClick={handleShowMore}
                disabled={loadingMore}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 text-xs font-bold rounded-xl shadow-xs transition-all hover:border-slate-400"
              >
                {loadingMore ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-emerald-600" />
                    Loading additional facilities...
                  </>
                ) : (
                  <>
                    Show More Nearby Facilities ({facilities.length} of {totalCount})
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  </>
                )}
              </button>
            </div>
          )}
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
