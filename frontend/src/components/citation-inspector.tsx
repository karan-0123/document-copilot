import React, { useState, useEffect } from 'react';
import { X, ExternalLink, FileText } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { IconButton } from './icon-button';
import { api } from '@/lib/api';
import { MarkdownRenderer } from './markdown-renderer';

interface CitationInspectorProps {
  citation: {
    index: number;
    chunk_id: string | null;
    company: string;
    filing_type: string;
    year: number;
    section: string;
    page: string;
    excerpt: string;
  };
  onClose: () => void;
}

export const CitationInspector: React.FC<CitationInspectorProps> = ({
  citation,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [chunks, setChunks] = useState<
    { id: string; text: string; chunk_index: number }[]
  >([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!citation.chunk_id) {
      setChunks([]);
      setError('No source chunk ID available for context lookup.');
      return;
    }

    setLoading(true);
    setError(null);
    setChunks([]);

    api
      .getChunkContext(citation.chunk_id)
      .then((data) => {
        setChunks(data.sort((a, b) => a.chunk_index - b.chunk_index));
      })
      .catch(() => {
        setError('Could not retrieve sequential chunk context.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [citation]);

  const getSecLink = () => {
    const query = `${citation.company} ${citation.filing_type} ${citation.year} ${citation.section}`;
    return `https://www.sec.gov/edgar/search/#/q=${encodeURIComponent(query)}`;
  };

  return (
    <div className="w-[360px] border-l border-[var(--border-subtle)] bg-[var(--surface-0)] flex flex-col h-full overflow-hidden text-[var(--text-primary)] shrink-0 animate-in slide-in-from-right-4 duration-200">
      {/* Header */}
      <div className="flex h-12 items-center justify-between px-4 border-b border-[var(--border-subtle)] shrink-0">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-[var(--text-tertiary)]" />
          <h4 className="text-xs font-medium text-[var(--text-secondary)]">
            Citation Inspector
          </h4>
        </div>
        <IconButton
          icon={<X size={14} />}
          label="Close inspector"
          onClick={onClose}
          size="sm"
        />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto min-h-0 select-text">
        <div className="p-5 space-y-5">
          {/* Source metadata card */}
          <div className="rounded-lg border border-[var(--border-default)] bg-[var(--surface-1)] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-bold tracking-wider text-[var(--text-tertiary)] border border-[var(--border-default)] bg-[var(--surface-2)] px-1.5 py-0.5 rounded font-mono">
                Citation {citation.index}
              </span>
              <a
                href={getSecLink()}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[10px] text-[var(--text-quaternary)] hover:text-[var(--text-primary)] transition-colors"
              >
                SEC EDGAR <ExternalLink size={10} />
              </a>
            </div>

            <div className="space-y-0.5">
              <h3 className="font-medium text-sm text-[var(--text-primary)]">
                {citation.company}
              </h3>
              <p className="text-xs text-[var(--text-tertiary)]">
                {citation.filing_type} · Fiscal Year {citation.year}
              </p>
            </div>

            <Separator className="bg-[var(--border-subtle)]" />

            <div className="flex items-center justify-between text-xs text-[var(--text-tertiary)]">
              <span>{citation.section || 'General Section'}</span>
              <span className="font-medium text-[var(--text-secondary)]">
                Page {citation.page}
              </span>
            </div>
          </div>

          {/* Verbatim excerpt */}
          <div className="space-y-2">
            <h5 className="text-[10px] font-semibold text-[var(--text-quaternary)] uppercase tracking-wider">
              Verbatim Excerpt
            </h5>
            <div className="border-l-2 border-[var(--border-strong)] bg-[var(--surface-1)] rounded-r-lg p-3 italic text-sm text-[var(--text-secondary)] leading-relaxed select-text">
              <MarkdownRenderer content={citation.excerpt} />
            </div>
          </div>

          {/* Surrounding context */}
          <div className="space-y-3">
            <h5 className="text-[10px] font-semibold text-[var(--text-quaternary)] uppercase tracking-wider">
              Surrounding Context
            </h5>

            {loading && (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="space-y-2 p-3 rounded-lg border border-[var(--border-subtle)]">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="h-3 w-full" />
                    <Skeleton className="h-3 w-4/5" />
                  </div>
                ))}
              </div>
            )}

            {error && (
              <div className="text-xs text-[var(--text-quaternary)] italic p-3 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-1)]">
                {error}
              </div>
            )}

            {!loading && !error && chunks.length > 0 && (
              <div className="space-y-2">
                {chunks.map((chunk) => {
                  const isTarget = chunk.id === citation.chunk_id;
                  return (
                    <div
                      key={chunk.id}
                      className={`rounded-lg p-3 text-xs leading-relaxed transition-colors ${
                        isTarget
                          ? 'border border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text-secondary)]'
                          : 'border border-[var(--border-subtle)] bg-[var(--surface-1)] text-[var(--text-tertiary)]'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5 text-[10px] text-[var(--text-quaternary)]">
                        <span>Paragraph {chunk.chunk_index}</span>
                        {isTarget && (
                          <span className="font-semibold text-[var(--text-secondary)] uppercase tracking-wider text-[9px]">
                            Cited
                          </span>
                        )}
                      </div>
                      <div className="select-text">
                        <MarkdownRenderer content={chunk.text} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
