import React from 'react';
import { config } from '../../lib/config';
import { Database, Sparkles, ToggleLeft, ToggleRight } from 'lucide-react';

export const DemoBanner: React.FC = () => {
  return (
    <div
      className={`w-full py-1.5 px-4 text-xs font-medium flex items-center justify-between border-b ${
        config.isMockMode
          ? 'bg-amber-50/90 text-amber-900 border-amber-200'
          : 'bg-emerald-50/90 text-emerald-900 border-emerald-200'
      }`}
    >
      <div className="flex items-center gap-2">
        {config.isMockMode ? (
          <Sparkles className="h-3.5 w-3.5 text-amber-600" />
        ) : (
          <Database className="h-3.5 w-3.5 text-emerald-600" />
        )}
        <span>
          {config.isMockMode ? (
            <>
              <strong>Demo Evaluation Mode:</strong> Displaying simulated rural healthcare and stock data for demonstration.
            </>
          ) : (
            <>
              <strong>Live Backend Connected:</strong> Targeting API server at <code className="font-mono">{config.apiBaseUrl}</code>.
            </>
          )}
        </span>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-[11px] text-slate-500 hidden sm:inline">
          Backend Integration Switch:
        </span>
        <button
          type="button"
          onClick={() => config.setMockMode(!config.isMockMode)}
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[11px] font-semibold transition-colors ${
            config.isMockMode
              ? 'bg-amber-100/70 border-amber-300 text-amber-900 hover:bg-amber-200'
              : 'bg-emerald-100/70 border-emerald-300 text-emerald-900 hover:bg-emerald-200'
          }`}
          title="Toggle between mock demonstration data and live backend calls"
        >
          {config.isMockMode ? (
            <>
              <ToggleLeft className="h-3.5 w-3.5 text-amber-700" /> Switch to Live Backend
            </>
          ) : (
            <>
              <ToggleRight className="h-3.5 w-3.5 text-emerald-700" /> Switch to Demo Mode
            </>
          )}
        </button>
      </div>
    </div>
  );
};
