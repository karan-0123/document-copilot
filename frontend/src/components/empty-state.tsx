import React from 'react';

interface EmptyStateProps {
  icon: React.ReactNode;
  heading: string;
  description?: string;
  action?: React.ReactNode;
}

/**
 * Generic empty state component.
 * Used for: no threads, no messages, loading failures.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  heading,
  description,
  action,
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center select-none">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-[var(--border-default)] bg-[var(--surface-2)] text-[var(--text-tertiary)] mb-4">
        {icon}
      </div>
      <h3 className="text-sm font-medium text-[var(--text-primary)] mb-1">
        {heading}
      </h3>
      {description && (
        <p className="text-xs text-[var(--text-tertiary)] max-w-[240px] leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
};
