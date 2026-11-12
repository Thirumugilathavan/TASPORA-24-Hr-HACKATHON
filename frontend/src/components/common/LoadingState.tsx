import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useTranslation } from '../../context/LanguageContext';

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message,
  className,
}) => {
  const { t } = useTranslation();
  const displayMessage = message || t('loadingMessage', 'Loading healthcare information...');

  return (
    <div className={cn('flex flex-col items-center justify-center p-12 text-center', className)}>
      <Loader2 className="h-8 w-8 animate-spin text-healthcare-600 mb-3" />
      <p className="text-sm font-medium text-slate-600">{displayMessage}</p>
    </div>
  );
};
