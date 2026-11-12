import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { SearchInput } from '../components/common/SearchInput';
import { MedicineCard } from '../components/medicines/MedicineCard';
import { CreateRequestModal } from '../components/requests/CreateRequestModal';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Medicine, StockAvailabilityItem } from '../types';
import { medicineService } from '../services/medicineService';
import { useNotification } from '../context/NotificationContext';
import { useTranslation } from '../context/LanguageContext';
import { Info } from 'lucide-react';

export const MedicinesPage: React.FC = () => {
  const { notify } = useNotification();
  const { t } = useTranslation();

  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  // Stock availability state
  const [stockMap, setStockMap] = useState<Record<string, StockAvailabilityItem[]>>({});
  const [loadingStock, setLoadingStock] = useState<Record<string, boolean>>({});

  // Request Refill Modal
  const [refillMedicine, setRefillMedicine] = useState<Medicine | null>(null);

  useEffect(() => {
    loadMedicines();
  }, []);

  const loadMedicines = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await medicineService.getMedicines();
      setMedicines(data);

      // Pre-fetch stock availability for the initial items
      data.slice(0, 4).forEach((med) => {
        fetchStockForMedicine(med.id);
      });
    } catch (err: any) {
      setError(err.message || t('errorTitle', 'Failed to load medicine directory.'));
    } finally {
      setLoading(false);
    }
  };

  const fetchStockForMedicine = async (medicineId: string) => {
    if (stockMap[medicineId] || loadingStock[medicineId]) return;
    try {
      setLoadingStock((prev) => ({ ...prev, [medicineId]: true }));
      const items = await medicineService.getStockAvailability(medicineId);
      setStockMap((prev) => ({ ...prev, [medicineId]: items }));
    } catch (err) {
      console.error('Failed to fetch stock for medicine', medicineId, err);
    } finally {
      setLoadingStock((prev) => ({ ...prev, [medicineId]: false }));
    }
  };

  const categories = ['ALL', ...Array.from(new Set(medicines.map((m) => m.category)))];

  const filteredMedicines = medicines.filter((med) => {
    const matchesCat = selectedCategory === 'ALL' || med.category === selectedCategory;
    const q = search.toLowerCase().trim();
    const matchesSearch =
      !q ||
      med.name.toLowerCase().includes(q) ||
      med.code.toLowerCase().includes(q) ||
      med.category.toLowerCase().includes(q);
    return matchesCat && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('medicinesTitle', 'Essential Medicines & Inventory Availability')}
        subtitle={t('medicinesSubtitle', 'Check probabilistic stock levels across primary health centers and verified Jan Aushadhi stores')}
      />

      {/* Probabilistic Stock Disclaimer Box */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-emerald-900 text-xs flex items-start gap-3">
        <Info className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong>{t('bayesianStockEstimation', 'Bayesian Stock Estimation:')} </strong>
          {t('bayesianStockDesc', 'NALAM AI computes medicine availability probabilities combining physical dispensary reports, facility stock audits, and ASHA refill logs.')}{' '}
          {t('statusTagsExplanation', 'Status tags indicate Likely (p ≥ 0.65), Uncertain (0.35 < p < 0.65), or Unlikely (p ≤ 0.35) in stock.')}
        </div>
      </div>

      {/* Search & Category Filter */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="w-full md:w-80">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder={t('searchMedicinesPlaceholder', 'Search by medicine name, generic code, or category...')}
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto pb-1 md:pb-0">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-colors ${
                selectedCategory === cat
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {cat === 'ALL' ? t('allCategories', 'All Categories') : cat}
            </button>
          ))}
        </div>
      </div>

      {/* Medicine Grid */}
      {loading ? (
        <LoadingState message={t('fetchingMedicines', 'Fetching verified medicine catalog...')} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadMedicines} />
      ) : filteredMedicines.length === 0 ? (
        <EmptyState
          title={t('noMedicinesFound', 'No medicines found')}
          message={t('noMedicinesFoundDesc', 'No essential medicines matched your search query or category filter. Try clearing filters.')}
          actionLabel={t('clearFilters', 'Clear Filters')}
          onAction={() => {
            setSearch('');
            setSelectedCategory('ALL');
          }}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredMedicines.map((med) => {
            // Lazy load stock if not loaded
            if (!stockMap[med.id] && !loadingStock[med.id]) {
              fetchStockForMedicine(med.id);
            }

            return (
              <MedicineCard
                key={med.id}
                medicine={med}
                availability={stockMap[med.id] || []}
                onRequestRefill={(m) => setRefillMedicine(m)}
              />
            );
          })}
        </div>
      )}

      {/* Refill Request Modal */}
      {refillMedicine && (
        <CreateRequestModal
          isOpen={!!refillMedicine}
          onClose={() => setRefillMedicine(null)}
          initialRequestType="REFILL"
          initialMedicineId={refillMedicine.id}
          onCreated={() => {
            notify(t('requestSubmittedNotify', 'Healthcare request submitted successfully with AI routing!'), 'success');
            setRefillMedicine(null);
          }}
        />
      )}
    </div>
  );
};
