import React from 'react';
import { cn } from '../../lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  subtitle?: string;
  className?: string;
  onClick?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  subtitle,
  className,
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm transition-all duration-200',
        onClick && 'cursor-pointer hover:border-healthcare-400 hover:shadow-md',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{title}</p>
          <p className="mt-1 text-2xl font-bold text-navy-900">{value}</p>
          {subtitle && <p className="mt-1 text-xs text-slate-600">{subtitle}</p>}
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-healthcare-50 text-healthcare-700">
          {icon}
        </div>
      </div>
    </div>
  );
};
