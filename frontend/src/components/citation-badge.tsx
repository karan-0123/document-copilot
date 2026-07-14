import React from 'react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface CitationBadgeProps {
  index: number;
  company?: string;
  filingType?: string;
  year?: number | string;
  onClick?: () => void;
}

/**
 * Small inline [n] badge with tooltip preview.
 * Shows company/filing/year on hover. Click navigates to citation inspector.
 */
export const CitationBadge: React.FC<CitationBadgeProps> = ({
  index,
  company,
  filingType,
  year,
  onClick,
}) => {
  const hasPreview = company || filingType || year;

  const badge = (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
      className="inline-flex items-center justify-center px-1.5 py-0.5 mx-0.5 text-[9px] font-bold rounded border border-[var(--border-default)] bg-[var(--surface-2)] text-[var(--text-secondary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)] transition-colors cursor-pointer select-none align-super font-mono tabular-nums"
    >
      {index}
    </button>
  );

  if (!hasPreview) return badge;

  return (
    <Tooltip>
      <TooltipTrigger asChild>{badge}</TooltipTrigger>
      <TooltipContent side="top" className="text-xs max-w-[220px]">
        <span className="font-medium text-[var(--text-primary)]">
          {company || 'Source'}
        </span>
        {(filingType || year) && (
          <span className="text-[var(--text-tertiary)]">
            {' '}· {filingType} {year}
          </span>
        )}
      </TooltipContent>
    </Tooltip>
  );
};
