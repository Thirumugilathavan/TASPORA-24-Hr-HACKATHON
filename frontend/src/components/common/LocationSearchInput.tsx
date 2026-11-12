import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MapPin, Search, X, Loader2, CheckCircle2, AlertCircle, PlusCircle, Building } from 'lucide-react';
import { Village } from '../../types';
import { authService } from '../../services/authService';
import { useTranslation } from '../../context/LanguageContext';

interface LocationSearchInputProps {
  selectedVillageId: string;
  onSelect: (village: Village | null) => void;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export const LocationSearchInput: React.FC<LocationSearchInputProps> = ({
  selectedVillageId,
  onSelect,
  required = false,
  disabled = false,
  placeholder,
  className = '',
}) => {
  const { t } = useTranslation();
  const effectivePlaceholder =
    placeholder ||
    t(
      'searchVillagePlaceholder',
      'Type village, town, or PIN code (e.g. Rampur, Ariyalur, 637211)...'
    );

  const [query, setQuery] = useState('');
  const [selectedVillage, setSelectedVillage] = useState<Village | null>(null);
  const [suggestions, setSuggestions] = useState<Village[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [hasInteracted, setHasInteracted] = useState(false);

  // Manual Locality Fallback Modal State
  const [showManualModal, setShowManualModal] = useState(false);
  const [manualName, setManualName] = useState('');
  const [manualDistrict, setManualDistrict] = useState('');
  const [manualState, setManualState] = useState('Tamil Nadu');
  const [manualPincode, setManualPincode] = useState('');
  const [manualLoading, setManualLoading] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Initialize selected village label if ID is provided
  useEffect(() => {
    if (!selectedVillageId) {
      if (selectedVillage) {
        setSelectedVillage(null);
        setQuery('');
      }
    }
  }, [selectedVillageId]);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        if (selectedVillage) {
          setQuery(formatVillageLabel(selectedVillage));
        } else if (query.trim() && !selectedVillageId) {
          setHasInteracted(true);
        }
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [selectedVillage, selectedVillageId, query]);

  // Debounced server search
  const performSearch = useCallback(async (searchTerm: string) => {
    const cleanTerm = searchTerm.trim();
    if (cleanTerm.length < 1) {
      setSuggestions([]);
      setIsLoading(false);
      setIsOpen(false);
      return;
    }

    setIsLoading(true);
    try {
      const results = await authService.searchVillages(cleanTerm, 20);
      setSuggestions(results);
      setIsOpen(true);
      setHighlightedIndex(results.length > 0 ? 0 : -1);
    } catch (err) {
      console.error('Failed to search locations:', err);
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newText = e.target.value;
    setQuery(newText);
    setHasInteracted(true);

    if (selectedVillage || selectedVillageId) {
      setSelectedVillage(null);
      onSelect(null);
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (!newText.trim()) {
      setSuggestions([]);
      setIsOpen(false);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    debounceTimerRef.current = setTimeout(() => {
      performSearch(newText);
    }, 250);
  };

  const handleSelectVillage = (village: Village) => {
    setSelectedVillage(village);
    setQuery(formatVillageLabel(village));
    setIsOpen(false);
    setSuggestions([]);
    setHighlightedIndex(-1);
    setHasInteracted(true);
    onSelect(village);
  };

  const handleClear = () => {
    setQuery('');
    setSelectedVillage(null);
    setSuggestions([]);
    setIsOpen(false);
    setHighlightedIndex(-1);
    setHasInteracted(true);
    onSelect(null);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || suggestions.length === 0) {
      if (e.key === 'ArrowDown' && query.trim().length > 0) {
        performSearch(query);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
          handleSelectVillage(suggestions[highlightedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        break;
      case 'Tab':
        setIsOpen(false);
        break;
      default:
        break;
    }
  };

  const formatVillageLabel = (v: Village): string => {
    const hierarchy = [];
    if (v.subdistrict && v.subdistrict !== v.name && v.subdistrict !== v.district) {
      hierarchy.push(v.subdistrict);
    }
    if (v.district) {
      hierarchy.push(v.district);
    }
    if (v.state) {
      hierarchy.push(v.state);
    }
    if (hierarchy.length > 0) {
      return `${v.name} (${hierarchy.join(', ')})`;
    }
    return v.name;
  };

  const renderHighlightedText = (text: string, highlight: string) => {
    if (!highlight.trim()) return <span>{text}</span>;
    const regex = new RegExp(`(${highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);
    return (
      <span>
        {parts.map((part, i) =>
          regex.test(part) ? (
            <mark key={i} className="bg-emerald-100 text-emerald-900 font-semibold rounded px-0.5">
              {part}
            </mark>
          ) : (
            part
          )
        )}
      </span>
    );
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualName.trim() || !manualDistrict.trim()) {
      setManualError('Please provide both locality name and district.');
      return;
    }

    if (manualPincode.trim() && !/^[1-9]\d{5}$/.test(manualPincode.trim())) {
      setManualError('Please provide a valid 6-digit Indian PIN code (e.g. 600001).');
      return;
    }

    try {
      setManualLoading(true);
      setManualError(null);
      const customV = await authService.registerCustomVillage({
        name: manualName.trim(),
        district: manualDistrict.trim(),
        state: manualState.trim() || 'Tamil Nadu',
        pincode: manualPincode.trim() || undefined,
      });

      handleSelectVillage(customV);
      setShowManualModal(false);
    } catch (err: any) {
      setManualError(err.message || 'Failed to register custom location.');
    } finally {
      setManualLoading(false);
    }
  };

  const isInvalid = required && hasInteracted && !selectedVillageId;

  return (
    <div ref={containerRef} className={`relative w-full ${className}`}>
      <div className="relative">
        <MapPin
          className={`w-4 h-4 absolute left-3 top-3 pointer-events-none transition-colors ${
            selectedVillage ? 'text-emerald-600' : 'text-slate-400'
          }`}
          aria-hidden="true"
        />

        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          aria-autocomplete="list"
          aria-controls="location-autocomplete-list"
          aria-required={required}
          aria-invalid={isInvalid}
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (suggestions.length > 0 && !selectedVillage) {
              setIsOpen(true);
            }
          }}
          disabled={disabled}
          placeholder={effectivePlaceholder}
          className={`w-full pl-9 pr-16 py-2 border rounded-lg text-sm bg-white focus:outline-none transition-all ${
            isInvalid
              ? 'border-rose-300 focus:ring-2 focus:ring-rose-400'
              : selectedVillage
              ? 'border-emerald-400 ring-1 ring-emerald-400/30 text-slate-900 font-medium'
              : 'border-slate-300 focus:ring-2 focus:ring-emerald-500 text-slate-800'
          }`}
        />

        <div className="absolute right-2.5 top-2.5 flex items-center gap-1">
          {isLoading && <Loader2 className="w-4 h-4 text-emerald-600 animate-spin" />}

          {query && !isLoading && (
            <button
              type="button"
              onClick={handleClear}
              title={t('clear', 'Clear')}
              aria-label={t('clear', 'Clear')}
              className="p-0.5 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100"
            >
              <X className="w-4 h-4" />
            </button>
          )}

          {selectedVillage && !isLoading && (
            <CheckCircle2 className="w-4 h-4 text-emerald-600" aria-label={t('verified', 'Verified')} />
          )}
        </div>
      </div>

      {/* Autocomplete Dropdown List */}
      {isOpen && (
        <ul
          id="location-autocomplete-list"
          role="listbox"
          aria-label={t('selectVillageTitle', 'Location suggestions')}
          className="absolute z-50 left-0 right-0 mt-1 max-h-64 overflow-y-auto bg-white border border-slate-200 rounded-xl shadow-xl shadow-slate-300/40 divide-y divide-slate-100 focus:outline-none"
        >
          {suggestions.length > 0 ? (
            suggestions.map((village, idx) => {
              const isSelected = highlightedIndex === idx;
              return (
                <li
                  key={village.id}
                  id={`location-option-${idx}`}
                  role="option"
                  aria-selected={isSelected}
                  onMouseEnter={() => setHighlightedIndex(idx)}
                  onClick={() => handleSelectVillage(village)}
                  className={`px-3.5 py-2.5 cursor-pointer text-left transition-colors flex flex-col gap-0.5 ${
                    isSelected ? 'bg-emerald-50 text-slate-900' : 'hover:bg-slate-50 text-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm text-slate-900">
                      {renderHighlightedText(village.name, query)}
                    </span>
                    <span className="text-[11px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                      {village.district}
                    </span>
                  </div>

                  <div className="text-xs text-slate-500 flex items-center gap-1.5 flex-wrap">
                    {village.subdistrict && village.subdistrict !== village.name && (
                      <span>
                        {t('taluk', 'Taluk:')} {village.subdistrict}
                      </span>
                    )}
                    {village.subdistrict && village.state && <span>•</span>}
                    {village.state && <span className="font-medium text-slate-600">{village.state}</span>}
                  </div>
                </li>
              );
            })
          ) : !isLoading && query.trim().length >= 2 ? (
            <li className="px-4 py-4 text-center text-xs text-slate-500">
              <Search className="w-5 h-5 mx-auto text-slate-300 mb-1.5" />
              <span>{t('noLocationsFound', `No verified locations found matching "${query}"`)}</span>
              <p className="mt-1 text-[11px] text-slate-400">
                {t('trySearchingDistrict', 'Check for spelling or try searching by district or PIN code.')}
              </p>
              <button
                type="button"
                onClick={() => {
                  setManualName(query.trim());
                  setShowManualModal(true);
                  setIsOpen(false);
                }}
                className="mt-2.5 px-3 py-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg border border-emerald-200 transition-colors inline-flex items-center gap-1"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                {t('manualLocationFallback', 'Enter locality & PIN code manually')}
              </button>
            </li>
          ) : null}
        </ul>
      )}

      {/* Validation status feedback & Manual Fallback Link */}
      <div className="mt-1.5 flex items-center justify-between text-xs">
        {selectedVillage ? (
          <div className="flex items-center gap-1.5 text-emerald-700">
            <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 text-emerald-600" />
            <span>
              {t('verified', 'Verified:')} <strong>{selectedVillage.name}</strong> ({selectedVillage.district}
              {selectedVillage.state ? `, ${selectedVillage.state}` : ''})
            </span>
          </div>
        ) : isInvalid ? (
          <div className="flex items-center gap-1.5 text-rose-600">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{t('selectValidLocationError', 'Please select a location or enter manually below.')}</span>
          </div>
        ) : (
          <span className="text-[11px] text-slate-400">
            {t('searchVillagesHelper', 'Search 625k+ Census settlements or enter 6-digit PIN.')}
          </span>
        )}

        <button
          type="button"
          onClick={() => setShowManualModal(true)}
          className="text-[11px] text-emerald-700 hover:text-emerald-800 font-semibold hover:underline inline-flex items-center gap-1 ml-auto"
        >
          <Building className="w-3 h-3" />
          <span>{t('manualFallbackBtn', 'Locality not listed?')}</span>
        </button>
      </div>

      {/* Manual Locality Entry Modal */}
      {showManualModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-2xs animate-in fade-in">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-emerald-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  {t('manualLocationTitle', 'Enter Unlisted Village or Locality')}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowManualModal(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-500">
              {t(
                'manualLocationDesc',
                'If your specific village, hamlet, or town is unlisted, enter its details with postal PIN code for geographic resolution.'
              )}
            </p>

            {manualError && (
              <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                <span>{manualError}</span>
              </div>
            )}

            <form onSubmit={handleManualSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  {t('localityName', 'Locality / Village / Town Name')} *
                </label>
                <input
                  type="text"
                  required
                  value={manualName}
                  onChange={(e) => setManualName(e.target.value)}
                  placeholder="e.g. Chitlapakkam, Periyakulam, Rampur"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    {t('district', 'District')} *
                  </label>
                  <input
                    type="text"
                    required
                    value={manualDistrict}
                    onChange={(e) => setManualDistrict(e.target.value)}
                    placeholder="e.g. Madurai, Namakkal"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    {t('pincode', 'PIN Code (6 digits)')}
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    value={manualPincode}
                    onChange={(e) => setManualPincode(e.target.value.replace(/\D/g, ''))}
                    placeholder="e.g. 625001"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  {t('state', 'State')}
                </label>
                <input
                  type="text"
                  value={manualState}
                  onChange={(e) => setManualState(e.target.value)}
                  placeholder="e.g. Tamil Nadu"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowManualModal(false)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  {t('cancel', 'Cancel')}
                </button>
                <button
                  type="submit"
                  disabled={manualLoading}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-colors inline-flex items-center gap-1.5"
                >
                  {manualLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>{t('saving', 'Resolving...')}</span>
                    </>
                  ) : (
                    <span>{t('confirmLocation', 'Confirm & Select Locality')}</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
