import React, { useState, useEffect, useMemo } from 'react';
import {
  Calendar,
  Clock,
  MapPin,
  Search,
  Filter,
  RefreshCw,
  Building2,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ShieldCheck,
  Navigation,
  Globe,
  SlidersHorizontal,
  ChevronRight,
  Database,
  Layers,
  HeartPulse,
  Truck,
  Eye,
  Activity,
  Award,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { campService, CampQueryParams } from '../services/campService';
import {
  HealthCamp,
  DistrictCoverageItem,
  DistrictCoverageResponse,
  HealthCampSource,
} from '../types';
import { CampDetailModal } from '../components/camps/CampDetailModal';

export const CampsPage: React.FC = () => {
  const { currentPatient } = useAuth();
  const { t } = useTranslation();

  const [activeTab, setActiveTab] = useState<'camps' | 'coverage' | 'sources'>('camps');

  // Camps list state
  const [camps, setCamps] = useState<HealthCamp[]>([]);
  const [totalCamps, setTotalCamps] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('ALL');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [dateRange, setDateRange] = useState<string>('upcoming');
  const [verifiedOnly, setVerifiedOnly] = useState<boolean>(true);

  // District list and coverage
  const [coverageData, setCoverageData] = useState<DistrictCoverageResponse | null>(null);
  const [coverageLoading, setCoverageLoading] = useState<boolean>(false);
  const [coverageSearch, setCoverageSearch] = useState<string>('');

  // Sources list
  const [sources, setSources] = useState<HealthCampSource[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState<boolean>(false);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  // Selected camp for detail modal
  const [selectedCamp, setSelectedCamp] = useState<HealthCamp | null>(null);

  // Patient coordinates
  const userLat = currentPatient?.village?.latitude;
  const userLng = currentPatient?.village?.longitude;
  const userDistrict = currentPatient?.village?.district;

  // Load camps
  const loadCamps = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: CampQueryParams = {
        query: searchQuery || undefined,
        district: selectedDistrict !== 'ALL' ? selectedDistrict : undefined,
        category: selectedCategory !== 'ALL' ? selectedCategory : undefined,
        verification_status: verifiedOnly ? 'VERIFIED' : 'ALL',
        date_range: dateRange,
        user_lat: userLat,
        user_lng: userLng,
        limit: 50,
      };
      const res = await campService.getHealthCamps(params);
      setCamps(res.items || []);
      setTotalCamps(res.total || 0);
    } catch (err: any) {
      console.error('Error loading health camps:', err);
      setError('Unable to load health camp notices. Please verify connection.');
    } finally {
      setLoading(false);
    }
  };

  // Load coverage
  const loadCoverage = async () => {
    setCoverageLoading(true);
    try {
      const res = await campService.getDistrictCoverage();
      setCoverageData(res);
    } catch (err) {
      console.error('Error loading district coverage:', err);
    } finally {
      setCoverageLoading(false);
    }
  };

  // Load sources
  const loadSources = async () => {
    setSourcesLoading(true);
    try {
      const res = await campService.getSources();
      setSources(res);
    } catch (err) {
      console.error('Error loading sources:', err);
    } finally {
      setSourcesLoading(false);
    }
  };

  useEffect(() => {
    loadCamps();
  }, [searchQuery, selectedDistrict, selectedCategory, dateRange, verifiedOnly]);

  useEffect(() => {
    if (activeTab === 'coverage') {
      loadCoverage();
    } else if (activeTab === 'sources') {
      loadSources();
    }
  }, [activeTab]);

  // Handle sync trigger
  const handleTriggerSync = async () => {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const res = await campService.triggerSync();
      setSyncMessage(
        `Successfully synced ${res.sources_succeeded} of ${res.sources_processed} official sources. ${res.total_new_events} events updated.`
      );
      await loadCamps();
      if (activeTab === 'coverage') await loadCoverage();
      if (activeTab === 'sources') await loadSources();
    } catch (err: any) {
      setSyncMessage('Failed to trigger source synchronization.');
    } finally {
      setSyncing(false);
    }
  };

  // Filtered districts in coverage view
  const filteredCoverageDistricts = useMemo(() => {
    if (!coverageData?.districts) return [];
    if (!coverageSearch.trim()) return coverageData.districts;
    const q = coverageSearch.toLowerCase();
    return coverageData.districts.filter(
      (d) =>
        d.district.toLowerCase().includes(q) ||
        d.district_ta.toLowerCase().includes(q) ||
        d.headquarters.toLowerCase().includes(q)
    );
  }, [coverageData, coverageSearch]);

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'MOBILE_MEDICAL_UNIT':
        return <Truck className="w-4 h-4 text-teal-600" />;
      case 'NCD_SCREENING':
        return <Activity className="w-4 h-4 text-emerald-600" />;
      case 'EYE_CAMP':
        return <Eye className="w-4 h-4 text-blue-600" />;
      default:
        return <HeartPulse className="w-4 h-4 text-rose-600" />;
    }
  };

  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case 'MOBILE_MEDICAL_UNIT':
        return 'bg-teal-50 text-teal-800 border-teal-200';
      case 'NCD_SCREENING':
        return 'bg-emerald-50 text-emerald-800 border-emerald-200';
      case 'EYE_CAMP':
        return 'bg-blue-50 text-blue-800 border-blue-200';
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  const categoryOptions = [
    { id: 'ALL', label: 'All Health Outreach' },
    { id: 'MOBILE_MEDICAL_UNIT', label: 'Mobile Medical Units' },
    { id: 'NCD_SCREENING', label: 'NCD & Chronic Screening' },
    { id: 'EYE_CAMP', label: 'Eye & Cataract Camps' },
    { id: 'GENERAL_HEALTH_CAMP', label: 'General Health Camps' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1">
              <Award className="w-3.5 h-3.5" />
              Statewide Tamil Nadu Coverage
            </span>
            <span className="text-xs text-slate-500 font-medium">38 Districts Monitored</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Government Health Camps & Outreach
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Statewide discovery of official Tamil Nadu health camps, Mobile Medical Units, and follow-up care
          </p>
        </div>

        {/* Sync & Refresh Controls */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleTriggerSync}
            disabled={syncing}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 disabled:opacity-50 transition-colors shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing Sources...' : 'Sync Official Sources'}
          </button>

          <button
            onClick={() => loadCamps()}
            className="p-2 text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors border border-slate-300"
            title="Refresh camp listings"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {syncMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            {syncMessage}
          </span>
          <button
            onClick={() => setSyncMessage(null)}
            className="text-xs text-emerald-700 font-bold hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Location Proximity Banner */}
      {userLat && userLng && (
        <div className="p-4 rounded-xl bg-linear-to-r from-emerald-50 to-teal-50 border border-emerald-200 text-xs text-emerald-950 flex flex-wrap items-center justify-between gap-3 shadow-2xs">
          <div className="flex items-center gap-2.5">
            <Navigation className="w-4 h-4 text-emerald-700 shrink-0" />
            <div>
              <span className="font-bold">Proximity Ranking Active:</span> Health camps are dynamically ranked by
              true geographic road distance from your registered village (
              <strong>{currentPatient?.village?.name || 'Home Village'}</strong>, {userDistrict}).
            </div>
          </div>
          <button
            onClick={() => {
              if (userDistrict) setSelectedDistrict(userDistrict);
            }}
            className="px-3 py-1 rounded-md bg-white border border-emerald-300 text-emerald-800 font-semibold hover:bg-emerald-100 transition-colors shadow-2xs"
          >
            Filter My District ({userDistrict})
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 text-sm font-medium">
        <button
          onClick={() => setActiveTab('camps')}
          className={`py-3 px-5 border-b-2 font-semibold transition-colors flex items-center gap-2 ${
            activeTab === 'camps'
              ? 'border-emerald-600 text-emerald-700 bg-emerald-50/40'
              : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
          }`}
        >
          <Calendar className="w-4 h-4" />
          Upcoming Camps & Outreach Sessions ({totalCamps})
        </button>

        <button
          onClick={() => setActiveTab('coverage')}
          className={`py-3 px-5 border-b-2 font-semibold transition-colors flex items-center gap-2 ${
            activeTab === 'coverage'
              ? 'border-emerald-600 text-emerald-700 bg-emerald-50/40'
              : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
          }`}
        >
          <Globe className="w-4 h-4" />
          Statewide District Coverage (38 Districts)
        </button>

        <button
          onClick={() => setActiveTab('sources')}
          className={`py-3 px-5 border-b-2 font-semibold transition-colors flex items-center gap-2 ${
            activeTab === 'sources'
              ? 'border-emerald-600 text-emerald-700 bg-emerald-50/40'
              : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
          }`}
        >
          <Database className="w-4 h-4" />
          Official Government Sources Registry
        </button>
      </div>

      {/* TAB 1: CAMPS DISCOVERY VIEW */}
      {activeTab === 'camps' && (
        <div className="space-y-5">
          {/* Search & Filter Toolbar */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex flex-col md:flex-row gap-3">
              {/* Search text input */}
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by camp name, medical service, venue, or locality..."
                  className="w-full pl-10 pr-4 py-2 text-sm rounded-xl border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>

              {/* District Filter Dropdown */}
              <div className="w-full md:w-64">
                <select
                  value={selectedDistrict}
                  onChange={(e) => setSelectedDistrict(e.target.value)}
                  aria-label="Filter by district"
                  className="w-full py-2 px-3 text-sm rounded-xl border border-slate-300 bg-white focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="ALL">All Tamil Nadu Districts</option>
                  {coverageData?.districts ? (
                    coverageData.districts.map((d) => (
                      <option key={d.district} value={d.district}>
                        {d.district} ({d.district_ta})
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="Salem">Salem (சேலம்)</option>
                      <option value="Erode">Erode (ஈரோடு)</option>
                      <option value="Coimbatore">Coimbatore (கோயம்புத்தூர்)</option>
                      <option value="Tiruchirappalli">Tiruchirappalli (திருச்சிராப்பள்ளி)</option>
                      <option value="Chennai">Chennai (சென்னை)</option>
                      <option value="Dharmapuri">Dharmapuri (தருமபுரி)</option>
                      <option value="Namakkal">Namakkal (நாமக்கல்)</option>
                      <option value="Nilgiris">Nilgiris (நீலகிரி)</option>
                      <option value="Thoothukudi">Thoothukudi (தூத்துக்குடி)</option>
                    </>
                  )}
                </select>
              </div>

              {/* Date Range Selector */}
              <div className="w-full md:w-44">
                <select
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value)}
                  aria-label="Filter by date range"
                  className="w-full py-2 px-3 text-sm rounded-xl border border-slate-300 bg-white focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="upcoming">Upcoming Dates</option>
                  <option value="today">Today Only</option>
                  <option value="this_week">Next 7 Days</option>
                  <option value="all">All Dates</option>
                </select>
              </div>
            </div>

            {/* Category Pills & Verified Toggle */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
              <div className="flex flex-wrap items-center gap-1.5">
                {categoryOptions.map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`px-3 py-1 text-xs rounded-lg font-semibold transition-colors ${
                      selectedCategory === cat.id
                        ? 'bg-emerald-700 text-white shadow-2xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>

              <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={verifiedOnly}
                  onChange={(e) => setVerifiedOnly(e.target.checked)}
                  className="w-4 h-4 rounded-sm border-slate-300 text-emerald-600 focus:ring-emerald-500"
                />
                Verified Official Notices Only
              </label>
            </div>
          </div>

          {/* Camps Grid */}
          {loading ? (
            <div className="p-12 text-center text-slate-500 bg-white rounded-2xl border border-slate-200">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
              <p className="text-sm font-medium">Loading verified health camp notices...</p>
            </div>
          ) : error ? (
            <div className="p-8 text-center bg-rose-50 border border-rose-200 rounded-2xl text-rose-800 text-sm">
              <AlertTriangle className="w-6 h-6 mx-auto mb-2 text-rose-600" />
              <p className="font-semibold">{error}</p>
              <button
                onClick={() => loadCamps()}
                className="mt-3 px-4 py-1.5 text-xs font-bold rounded-lg bg-rose-600 text-white hover:bg-rose-700"
              >
                Retry
              </button>
            </div>
          ) : camps.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-2xl border border-slate-200 text-slate-600">
              <Calendar className="w-10 h-10 mx-auto mb-3 text-slate-400" />
              <h3 className="font-bold text-base text-slate-800">No Upcoming Health Camps Found</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
                No active outreach sessions match your current district or category filters. You can broaden your search or inspect statewide district coverage.
              </p>
              <div className="mt-4 flex justify-center gap-2">
                <button
                  onClick={() => {
                    setSelectedDistrict('ALL');
                    setSelectedCategory('ALL');
                    setSearchQuery('');
                  }}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-700 text-white hover:bg-emerald-800"
                >
                  Clear Filters
                </button>
                <button
                  onClick={() => setActiveTab('coverage')}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300"
                >
                  View 38 Districts Status
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {camps.map((camp) => (
                <div
                  key={camp.id}
                  className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between"
                >
                  <div>
                    {/* Top Badges */}
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getCategoryBadgeClass(
                            camp.category
                          )}`}
                        >
                          {getCategoryIcon(camp.category)}
                          {camp.category === 'MOBILE_MEDICAL_UNIT'
                            ? 'Hospital on Wheels'
                            : camp.category === 'NCD_SCREENING'
                            ? 'NCD Screening'
                            : camp.category === 'EYE_CAMP'
                            ? 'Eye Camp'
                            : 'Health Camp'}
                        </span>
                        {camp.verification_status === 'VERIFIED' && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full">
                            <ShieldCheck className="w-3 h-3 text-emerald-600" />
                            Verified
                          </span>
                        )}
                      </div>

                      {camp.distance_km !== undefined && camp.distance_km !== null && (
                        <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-900 border border-emerald-200">
                          {camp.distance_km.toFixed(1)} km away
                        </span>
                      )}
                    </div>

                    {/* Title */}
                    <h3 className="font-bold text-slate-900 text-base leading-snug line-clamp-2">
                      {camp.title}
                    </h3>

                    {/* Schedule & Venue */}
                    <div className="mt-3 space-y-1.5 text-xs text-slate-600">
                      <div className="flex items-center gap-2 font-medium text-slate-800">
                        <Calendar className="w-3.5 h-3.5 text-emerald-700 shrink-0" />
                        <span>
                          {formatDate(camp.start_date)} • {formatTime(camp.start_date)}
                        </span>
                      </div>
                      <div className="flex items-start gap-2">
                        <MapPin className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" />
                        <span className="line-clamp-1">
                          {camp.venue_name}, {camp.district}
                        </span>
                      </div>
                    </div>

                    {/* Services Pills */}
                    {camp.services_offered && camp.services_offered.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {camp.services_offered.slice(0, 3).map((svc, i) => (
                          <span
                            key={i}
                            className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium border border-slate-200"
                          >
                            {svc}
                          </span>
                        ))}
                        {camp.services_offered.length > 3 && (
                          <span className="text-[11px] px-1.5 py-0.5 text-slate-500 font-medium">
                            +{camp.services_offered.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Card Action Row */}
                  <div className="mt-5 pt-3.5 border-t border-slate-100 flex items-center justify-between gap-2">
                    <span className="text-[11px] text-slate-500 flex items-center gap-1 line-clamp-1">
                      <Building2 className="w-3 h-3 text-slate-400 shrink-0" />
                      {camp.source_org.replace(', Government of Tamil Nadu', '')}
                    </span>

                    <button
                      onClick={() => setSelectedCamp(camp)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 transition-colors shadow-2xs"
                    >
                      Details & Follow-up
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: STATEWIDE DISTRICT COVERAGE */}
      {activeTab === 'coverage' && (
        <div className="space-y-5">
          {/* Summary Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-xs text-slate-500 font-medium">Monitored Districts</span>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {coverageData?.total_districts || 38}
              </p>
              <span className="text-[11px] text-emerald-700 font-semibold">100% TN Revenue Coverage</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-xs text-slate-500 font-medium">Districts with Events</span>
              <p className="text-2xl font-bold text-emerald-700 mt-1">
                {coverageData?.districts_with_events_count || 0}
              </p>
              <span className="text-[11px] text-slate-500">Scheduled Camps Active</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-xs text-slate-500 font-medium">Total Verified Camps</span>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {coverageData?.total_verified_camps || 0}
              </p>
              <span className="text-[11px] text-teal-700 font-semibold">Official Notices Verified</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-xs text-slate-500 font-medium">Monitored Sources</span>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {coverageData?.monitored_sources_count || 8}
              </p>
              <span className="text-[11px] text-slate-500">NHM & District Portals</span>
            </div>
          </div>

          {/* District Coverage Table & Search */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Tamil Nadu 38 Districts Registry</h2>
                <p className="text-xs text-slate-500">
                  Authoritative status classification: Verified Event Coverage vs No Published Events vs Insufficient Data
                </p>
              </div>

              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={coverageSearch}
                  onChange={(e) => setCoverageSearch(e.target.value)}
                  placeholder="Filter by district name..."
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            {coverageLoading ? (
              <div className="p-8 text-center text-slate-500">
                <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-emerald-600" />
                Loading statewide district coverage...
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {filteredCoverageDistricts.map((d) => (
                  <div
                    key={d.district}
                    className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-white hover:border-emerald-300 transition-colors flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <div className="font-bold text-slate-900 text-sm">
                          {d.district}{' '}
                          <span className="text-xs font-normal text-slate-500">({d.district_ta})</span>
                        </div>
                        {d.verified_events_count > 0 ? (
                          <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                            {d.verified_events_count} {d.verified_events_count === 1 ? 'Camp' : 'Camps'}
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-200 text-slate-600">
                            0 Camps
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-slate-500 mb-2">HQ: {d.headquarters}</p>

                      {/* Coverage state badge */}
                      <div className="mb-2">
                        {d.coverage_status === 'VERIFIED_EVENTS_AVAILABLE' ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            Verified Events Available
                          </span>
                        ) : d.coverage_status === 'NO_PUBLISHED_EVENTS' ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                            Sources Monitored · No Upcoming Events
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200">
                            <AlertTriangle className="w-3 h-3 text-amber-600" />
                            Insufficient Data / Pending Check
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-xs">
                      <a
                        href={d.portal_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-slate-600 hover:text-emerald-700 inline-flex items-center gap-1 font-medium"
                      >
                        {d.portal_url.replace('https://', '')}
                        <ExternalLink className="w-3 h-3 text-slate-400" />
                      </a>

                      <button
                        onClick={() => {
                          setSelectedDistrict(d.district);
                          setActiveTab('camps');
                        }}
                        className="text-emerald-700 hover:text-emerald-900 font-bold hover:underline"
                      >
                        View Camps →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: OFFICIAL GOVERNMENT SOURCES */}
      {activeTab === 'sources' && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">Configured Official Health Sources</h2>
              <p className="text-xs text-slate-500">
                Authoritative government endpoints polled at configurable intervals with field-level provenance.
              </p>
            </div>
            <button
              onClick={handleTriggerSync}
              disabled={syncing}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 disabled:opacity-50 transition-colors shadow-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? 'Synchronizing...' : 'Sync All Sources Now'}
            </button>
          </div>

          {sourcesLoading ? (
            <div className="p-8 text-center text-slate-500">
              <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-emerald-600" />
              Loading sources registry...
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {sources.map((src) => (
                <div key={src.id} className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-sm">{src.name}</span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                          src.last_status === 'SUCCESS'
                            ? 'bg-emerald-100 text-emerald-800'
                            : src.last_status === 'ERROR'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {src.last_status}
                      </span>
                      {src.district && (
                        <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700">
                          {src.district}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-600">{src.organization}</p>
                    <a
                      href={src.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-emerald-700 hover:underline inline-flex items-center gap-1"
                    >
                      {src.source_url}
                      <ExternalLink className="w-3 h-3 text-slate-400" />
                    </a>
                  </div>

                  <div className="text-xs text-right text-slate-500 shrink-0 space-y-1">
                    <p>
                      <strong>Discovered:</strong> {src.events_discovered_count} verified events
                    </p>
                    <p>
                      <strong>Check Frequency:</strong> Every {src.check_interval_hours} hrs
                    </p>
                    {src.last_checked_at && (
                      <p className="text-[11px] text-slate-400">
                        Last checked: {new Date(src.last_checked_at).toLocaleTimeString()}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Camp Detail Modal */}
      <CampDetailModal camp={selectedCamp} onClose={() => setSelectedCamp(null)} />
    </div>
  );
};
