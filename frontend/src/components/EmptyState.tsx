import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  action,
  className = '',
}) => (
  <div className={`p-12 text-center text-text-secondary text-sm flex flex-col items-center ${className}`}>
    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-large border border-border bg-bg text-text-secondary shadow-2xs">
      <Icon size={22} />
    </div>
    <p className="font-semibold text-text-primary mb-0.5">{title}</p>
    <p className="text-xs text-text-secondary max-w-sm">{description}</p>
    {action && <div className="mt-5">{action}</div>}
  </div>
);
