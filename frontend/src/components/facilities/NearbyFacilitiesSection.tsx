import React, { useState, useEffect, useCallback } from 'react';
import {
  MapPin,
  Navigation,
  ExternalLink,
  ShieldAlert,
  Building2,
  RefreshCw,
  Compass,
  ChevronRight,
  Info,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { Facility, Village, NearbyFacilityListResponse } from '../../types';
import { facilityService } from '../../services/facilityService';
import { getFacilityTypeLabel } from '../../lib/constants';
import { useAuth } from '../../context/AuthContext';
import { useTranslation } from '../../context/LanguageContext';
import { LocationSearchInput } from '../common/LocationSearchInput';

interface NearbyFacilitiesSectionProps {
  onSelectFacility?: (facility: Facility) => void;
  initialRadius?: number;
}

export const NearbyFacilitiesSection: React.FC<NearbyFacilitiesSectionProps> = ({
  onSelectFacility,
  initialRadius = 10,
}) => {
  const { currentPatient } = useAuth();
  const { t } = useTranslation();

  const [activeLocation, setActiveLocation] = useState<Village | null>(null);
  const [isChangingLocation, setIsChangingLocation] = useState(false);
  const [radiusKm, setRadiusKm] = useState<number>(initialRadius);
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [, setResolvedLocation] = useState<NearbyFacilityListResponse['resolved_location'] | null>(null);
  const [pageOffset, setPageOffset] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);

  const PAGE_SIZE = 12;

  // Geolocation state
  const [usingGps, setUsingGps] = useState<boolean>(false);
  const [gpsCoords, setGpsCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [gpsLoading, setGpsLoading] = useState<boolean>(false);
  const [gpsError, setGpsError] = useState<string | null>(null);

  // Sync with registered patient profile
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

  const fetchNearby = useCallback(
    async (offset: number = 0, append: boolean = false) => {
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
        setResolvedLocation(res.resolved_location || null);
        setPageOffset(offset);
        setHasMore((offset + (res.items || []).length) < (res.total || 0));
      } catch (err: any) {
        setError(err.message || t('errorTitle', 'Failed to fetch nearby healthcare facilities.'));
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [radiusKm, selectedType, usingGps, gpsCoords, activeLocation, t]
  );

  useEffect(() => {
    fetchNearby(0, false);
  }, [fetchNearby]);

  const handleShowMore = () => {
    if (!hasMore || loadingMore) return;
    const nextOffset = pageOffset + PAGE_SIZE;
    fetchNearby(nextOffset, true);
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
        let msg = 'Unable to retrieve your location.';
        if (err.code === err.PERMISSION_DENIED) {
          msg = 'Location permission was denied. Using registered village location.';
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          msg = 'Location information is unavailable.';
        } else if (err.code === err.TIMEOUT) {
          msg = 'Location request timed out.';
        }
        setGpsError(msg);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  const radiusOptions = [5, 10, 25, 50, 100];
  const typeFilterOptions = [
    { value: 'ALL', label: t('all', 'All') },
    { value: 'SCE', label: t('typeSubCentres', 'Sub-Centres (SCE)') },
    { value: 'PHC', label: t('typePhcs', 'Primary Health (PHC)') },
    { value: 'CHC', label: t('typeChcs', 'Community Health (CHC)') },
    { value: 'HOSPITAL', label: t('typeHospitals', 'Hospitals (THO/DHO)') },
  ];

  const currentLocationLabel = usingGps
    ? `Device GPS (${gpsCoords?.lat.toFixed(4)}, ${gpsCoords?.lon.toFixed(4)})`
    : activeLocation
    ? `${activeLocation.name}, ${activeLocation.district}${activeLocation.state ? `, ${activeLocation.state}` : ''}`
    : t('empty', 'No location selected');

  const isUserRegisteredVillage =
    !usingGps &&
    activeLocation &&
    currentPatient?.village?.id &&
    activeLocation.id === currentPatient.village.id;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Header Bar */}
      <div className="p-5 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-lg bg-emerald-50 text-emerald-700">
                <Compass className="w-5 h-5 text-emerald-600" />
              </span>
              <div>
                <h2 className="text-lg font-bold text-slate-900">{t('facilitiesNearYou', 'Healthcare Facilities Near You')}</h2>
                <p className="text-xs text-slate-500">
                  {t('facilitiesNearYouSub', 'Automatically ranked by straight-line distance from your registered location (closest facility first)')}
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsChangingLocation(!isChangingLocation)}
              className="px-2.5 py-1.5 rounded-lg text-xs font-semibold border border-slate-300 text-slate-700 bg-white hover:bg-slate-50 transition-colors"
            >
              {isChangingLocation ? t('close', 'Close') : t('selectChangeLocation', 'Select / Change Location')}
            </button>

            <button
              onClick={handleToggleGps}
              disabled={gpsLoading}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                usingGps
                  ? 'bg-sky-50 border-sky-300 text-sky-700 hover:bg-sky-100'
                  : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
              title={usingGps ? 'Click to switch back to registered village' : 'Use live device GPS coordinates'}
            >
              <Navigation className={`w-3.5 h-3.5 ${usingGps ? 'text-sky-600' : 'text-slate-500'}`} />
              {gpsLoading ? t('acquiringGps', 'Acquiring GPS...') : usingGps ? t('usingGpsLocation', 'Using GPS Location') : t('useDeviceGps', 'Use Device GPS')}
            </button>

            <button
              onClick={() => fetchNearby(0, false)}
              disabled={loading}
              className="p-1.5 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
              title={t('refresh', 'Refresh')}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
            </button>
          </div>
        </div>

        {/* Location Resolution Badge */}
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 font-medium">
            <MapPin className="w-3.5 h-3.5 text-emerald-600" />
            <span className="text-slate-500">{t('referenceLocation', 'Reference Location:')}</span> <strong className="text-slate-900">{currentLocationLabel}</strong>
          </span>
          {isUserRegisteredVillage && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-100 text-emerald-800">
              <CheckCircle2 className="w-3 h-3 text-emerald-700" />
              {t('registeredProfileLocation', 'Registered Profile Location')}
            </span>
          )}
          {activeLocation?.latitude && !usingGps && (
            <span className="text-slate-500 font-mono text-[11px]">
              ({activeLocation.latitude.toFixed(4)}, {activeLocation.longitude.toFixed(4)})
            </span>
          )}
        </div>

        {/* Change Location Search Banner */}
        {isChangingLocation && (
          <div className="mt-3 p-3.5 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                {t('selectVillageTitle', 'Select Your Village, Town, or City')}
              </h4>
              <button
                onClick={() => setIsChangingLocation(false)}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                {t('close', 'Close')} ✕
              </button>
            </div>
            <LocationSearchInput
              selectedVillageId={activeLocation?.id || ''}
              onSelect={handleLocationSelect}
              placeholder={t('searchVillagePlaceholder', 'Type village, town, or city name...')}
            />
          </div>
        )}

        {gpsError && (
          <div className="mt-2 text-xs text-amber-700 bg-amber-50 px-3 py-1.5 rounded-md border border-amber-200 flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span>{gpsError}</span>
          </div>
        )}

        {/* Filter Controls: Radius & Facility Type */}
        <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
          {/* Radius Selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-slate-600 mr-1">{t('searchRadius', 'Search Radius:')}</span>
            {radiusOptions.map((r) => (
              <button
                key={r}
                onClick={() => setRadiusKm(r)}
                className={`px-2.5 py-1 text-xs rounded-md font-semibold transition-all ${
                  radiusKm === r
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {r} km
              </button>
            ))}
          </div>

          {/* Type Filter */}
          <div className="flex items-center gap-1.5 overflow-x-auto">
            <span className="text-xs font-semibold text-slate-600 mr-1">{t('filter', 'Filter')}:</span>
            {typeFilterOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setSelectedType(opt.value)}
                className={`px-2.5 py-1 text-xs rounded-md font-semibold transition-all ${
                  selectedType === opt.value
                    ? 'bg-slate-800 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Facilities List Body */}
      <div className="p-5">
        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center text-center">
            <div className="w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin mb-3"></div>
            <p className="text-sm font-medium text-slate-700">{t('calculatingDistancesRegistry', 'Calculating distances to nearby facilities...')}</p>
            <p className="text-xs text-slate-400 mt-1">{t('searchingRegistryWithin', { radius: radiusKm })}</p>
          </div>
        ) : error ? (
          <div className="py-8 text-center bg-rose-50 rounded-lg border border-rose-200 p-4">
            <ShieldAlert className="w-6 h-6 text-rose-600 mx-auto mb-2" />
            <p className="text-sm font-semibold text-rose-800">{error}</p>
            <button
              onClick={() => fetchNearby(0, false)}
              className="mt-3 px-3 py-1.5 text-xs font-medium text-rose-700 bg-rose-100 hover:bg-rose-200 rounded-lg transition-colors"
            >
              {t('retry', 'Retry')}
            </button>
          </div>
        ) : !activeLocation && !usingGps ? (
          <div className="py-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200 p-6 space-y-3">
            <Compass className="w-8 h-8 text-slate-400 mx-auto" />
            <p className="text-sm font-semibold text-slate-800">{t('selectVillageTitle', 'Select Your Village, Town, or City')}</p>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {t('selectVillageDesc', 'Search nationwide database of 625,000+ Indian settlements to dynamically resolve accurate latitude and longitude coordinates.')}
            </p>
            <button
              onClick={() => setIsChangingLocation(true)}
              className="px-3 py-1.5 text-xs font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
            >
              {t('selectVillageCityBtn', 'Select Village / City')}
            </button>
          </div>
        ) : facilities.length === 0 ? (
          <div className="py-10 text-center">
            <Building2 className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-slate-800">{t('noFacilitiesWithin', { radius: radiusKm })}</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              {t('noFacilitiesWithinDesc', { radius: radiusKm, location: currentLocationLabel })}
            </p>
            <div className="mt-4 flex items-center justify-center gap-2">
              {radiusKm < 25 && (
                <button
                  onClick={() => setRadiusKm(25)}
                  className="px-3 py-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg transition-colors"
                >
                  {t('expandTo25km', 'Expand to 25 km')}
                </button>
              )}
              {radiusKm < 50 && (
                <button
                  onClick={() => setRadiusKm(50)}
                  className="px-3 py-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg transition-colors"
                >
                  {t('expandTo50km', 'Expand to 50 km')}
                </button>
              )}
              {radiusKm < 100 && (
                <button
                  onClick={() => setRadiusKm(100)}
                  className="px-3 py-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg transition-colors"
                >
                  {t('expandTo100km', 'Expand to 100 km')}
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
              <span>
                {t('showingFacilitiesWithin', { count: facilities.length, total: totalCount, radius: radiusKm })}
              </span>
              <span className="text-emerald-700 font-medium">{t('rankedClosestTo', { count: facilities.length })}</span>
            </div>

            {facilities.map((fac, idx) => {
              const typeLabel = getFacilityTypeLabel(fac.facility_type, t);
              const isClosest = idx === 0 && pageOffset === 0;

              return (
                <div
                  key={fac.id}
                  className={`p-4 rounded-xl border transition-all duration-200 ${
                    isClosest
                      ? 'border-emerald-300 bg-emerald-50/20 shadow-xs'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {/* Rank Badge */}
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold ${
                            isClosest
                              ? 'bg-emerald-600 text-white'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          #{idx + 1} {isClosest ? t('closest', 'Closest') : ''}
                        </span>

                        {/* Facility Type Badge */}
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                          {typeLabel}
                        </span>

                        {/* Distance Badge */}
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-900 border border-emerald-200">
                          <MapPin className="w-3 h-3 text-emerald-700" />
                          {fac.distance_km !== undefined ? t('kmAway', { dist: fac.distance_km }) : t('nearYou', 'Near you')}
                        </span>
                      </div>

                      {/* Facility Name */}
                      <h3 className="text-base font-bold text-slate-900 leading-snug">
                        {fac.name}
                      </h3>

                      {/* Address */}
                      <p className="text-xs text-slate-600">
                        {fac.address || `${fac.district || ''}, ${fac.state || ''}`}
                      </p>

                      {/* Operational Availability Note */}
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        <span
                          className="inline-flex items-center gap-1 text-[11px] text-slate-500 bg-slate-50 px-2 py-0.5 rounded border border-slate-200"
                          title={t('availabilityTooltip', 'Operational hours and real-time attendance require active staff/ASHA verification')}
                        >
                          <Info className="w-3 h-3 text-slate-400" />
                          {t('availabilityNotVerified', 'Availability not verified')}
                        </span>
                        {fac.ownership && (
                          <span className="text-[11px] text-slate-400">
                            {t('facilityOwnership', 'Facility Ownership:')} <span className="text-slate-600 font-medium">{fac.ownership}</span>
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Actions: Directions and Details */}
                    <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-2 pt-2 sm:pt-0">
                      {fac.directions_url && (
                        <a
                          href={fac.directions_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          {t('directions', 'Directions')}
                        </a>
                      )}
                      {onSelectFacility && (
                        <button
                          onClick={() => onSelectFacility(fac)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
                        >
                          {t('details', 'Details')}
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Show More Facilities / Pagination Action */}
            {hasMore && (
              <div className="py-4 text-center">
                <button
                  onClick={handleShowMore}
                  disabled={loadingMore}
                  className="inline-flex items-center gap-2 px-5 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
                >
                  {loadingMore ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-600" />
                      {t('loadingMore', 'Loading more...')}
                    </>
                  ) : (
                    <>
                      {t('showMoreFacilities', { count: facilities.length, total: totalCount })}
                      <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
