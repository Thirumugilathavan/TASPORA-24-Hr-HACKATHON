import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';
import { cn } from '../../lib/utils';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  message?: string;
  actionText?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  message,
  actionText,
  actionLabel,
  onAction,
  className,
}) => {
  const desc = description || message;
  const label = actionText || actionLabel;

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center bg-white rounded-xl border border-slate-200/80 shadow-sm',
        className
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500 mb-3">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      {desc && <p className="mt-1 max-w-sm text-sm text-slate-500">{desc}</p>}
      {label && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 inline-flex items-center px-4 py-2 rounded-lg bg-emerald-600 text-sm font-medium text-white hover:bg-emerald-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
        >
          {label}
        </button>
      )}
    </div>
  );
};
