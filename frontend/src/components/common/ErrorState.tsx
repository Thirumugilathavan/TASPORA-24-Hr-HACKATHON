import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useTranslation } from '../../context/LanguageContext';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title,
  message,
  onRetry,
  className,
}) => {
  const { t } = useTranslation();
  const displayTitle = title || t('errorTitle', 'Connection or Data Error');

  return (
    <div className={cn('p-6 rounded-xl border border-rose-200 bg-rose-50/70 text-rose-900', className)}>
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-rose-600 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <h4 className="text-sm font-semibold">{displayTitle}</h4>
          <p className="mt-1 text-sm text-rose-800 leading-relaxed">{message}</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white border border-rose-300 text-xs font-semibold text-rose-700 hover:bg-rose-100/50 shadow-sm transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" /> {t('retryRequest', 'Retry Request')}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
