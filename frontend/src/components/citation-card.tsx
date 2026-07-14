import React from 'react';
import { ChevronRight, FileText } from 'lucide-react';

interface CitationCardProps {
  index: number;
  company: string;
  filingType: string;
  year: number | string;
  section: string;
  page: string | number;
  excerpt: string;
  isSelected?: boolean;
  onClick?: () => void;
}

/**
 * Reusable citation row used in both the collapsible citation list
 * within message bubbles and the citation inspector panel.
 */
export const CitationCard: React.FC<CitationCardProps> = ({
  index,
  company,
  filingType,
  year,
  section,
  page,
  excerpt,
  isSelected = false,
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      className={`text-xs cursor-pointer p-3 rounded-lg border transition-colors flex flex-col gap-1.5 ${
        isSelected
          ? 'bg-[var(--surface-3)] border-[var(--border-strong)] text-[var(--text-primary)]'
          : 'border-[var(--border-subtle)] hover:bg-[var(--surface-2)] hover:border-[var(--border-default)]'
      }`}
    >
      <div className="font-medium text-[var(--text-primary)] flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <FileText size={11} className="text-[var(--text-quaternary)]" />
          <span className="font-mono text-[10px] text-[var(--text-tertiary)] border border-[var(--border-default)] bg-[var(--surface-2)] rounded px-1 py-px">
            {index}
          </span>
          <span>
            {company} · {filingType} {year}
          </span>
        </span>
        <ChevronRight size={10} className="text-[var(--text-quaternary)]" />
      </div>
      <div className="flex items-center gap-2 text-[var(--text-tertiary)]">
        <span>{section}</span>
        <span>·</span>
        <span>Page {page}</span>
      </div>
      {excerpt && (
        <div className="pl-3 border-l-2 border-[var(--border-default)] text-[var(--text-quaternary)] italic line-clamp-1 text-[11px]">
          "{excerpt}"
        </div>
      )}
    </div>
  );
};
