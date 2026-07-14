import React from 'react';
import { CitationBadge } from './citation-badge';

interface MarkdownRendererProps {
  content: string;
  onCitationClick?: (index: number) => void;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  onCitationClick,
}) => {
  const citationRegex = /\[(\d+)\]/g;

  // Replace citation markers with CitationBadge components
  const renderTextWithCitations = (text: string) => {
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;

    citationRegex.lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = citationRegex.exec(text)) !== null) {
      const matchIndex = match.index;
      const citationNum = parseInt(match[1], 10);

      if (matchIndex > lastIndex) {
        parts.push(text.substring(lastIndex, matchIndex));
      }

      parts.push(
        <CitationBadge
          key={`cit-${citationNum}-${matchIndex}`}
          index={citationNum}
          onClick={() => onCitationClick?.(citationNum)}
        />,
      );

      lastIndex = citationRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  // Inline formatting: bold, italic, inline code
  const formatInline = (text: string): React.ReactNode => {
    // Process bold: **text**
    const boldParts = text.split(/\*\*([^*]+)\*\*/g);
    if (boldParts.length > 1) {
      return boldParts.map((part, idx) => {
        if (idx % 2 === 1) {
          return (
            <strong key={idx} className="font-semibold text-[var(--text-primary)]">
              {renderTextWithCitations(part)}
            </strong>
          );
        }
        return <React.Fragment key={idx}>{renderTextWithCitations(part)}</React.Fragment>;
      });
    }

    // Process inline code: `code`
    const codeParts = text.split(/`([^`]+)`/g);
    if (codeParts.length > 1) {
      return codeParts.map((part, idx) => {
        if (idx % 2 === 1) {
          return (
            <code
              key={idx}
              className="px-1.5 py-0.5 rounded border border-[var(--border-default)] bg-[var(--surface-2)] text-xs font-mono text-[var(--text-primary)]"
            >
              {part}
            </code>
          );
        }
        return <React.Fragment key={idx}>{renderTextWithCitations(part)}</React.Fragment>;
      });
    }

    return renderTextWithCitations(text);
  };

  // Main block parser
  const parseBlocks = () => {
    const rawBlocks = content.split(/\n\s*\n/);
    return rawBlocks.map((block, idx) => {
      const trimmedBlock = block.trim();
      if (!trimmedBlock) return null;

      const lines = trimmedBlock.split('\n').map((l) => l.trim());

      // Heading detection: ## or ###
      if (lines.length === 1 && lines[0].startsWith('## ')) {
        return (
          <h3
            key={idx}
            className="text-sm font-semibold text-[var(--text-primary)] mt-4 mb-2"
          >
            {formatInline(lines[0].substring(3))}
          </h3>
        );
      }
      if (lines.length === 1 && lines[0].startsWith('### ')) {
        return (
          <h4
            key={idx}
            className="text-xs font-semibold text-[var(--text-primary)] mt-3 mb-1.5 uppercase tracking-wide"
          >
            {formatInline(lines[0].substring(4))}
          </h4>
        );
      }

      // Horizontal rule
      if (lines.length === 1 && /^[-*_]{3,}$/.test(lines[0])) {
        return (
          <hr
            key={idx}
            className="border-t border-[var(--border-subtle)] my-4"
          />
        );
      }

      // Code block: ```...```
      if (trimmedBlock.startsWith('```') && trimmedBlock.endsWith('```')) {
        const codeContent = trimmedBlock
          .replace(/^```\w*\n?/, '')
          .replace(/\n?```$/, '');
        return (
          <pre
            key={idx}
            className="rounded-lg border border-[var(--border-default)] bg-[var(--surface-2)] p-3 overflow-x-auto my-3"
          >
            <code className="text-xs font-mono text-[var(--text-secondary)] leading-relaxed whitespace-pre">
              {codeContent}
            </code>
          </pre>
        );
      }

      // Table detector
      const isTable =
        lines.length >= 2 &&
        lines.every((line) => line.startsWith('|') && line.endsWith('|'));
      if (isTable) {
        const tableRows = lines.map((line) =>
          line
            .split('|')
            .slice(1, -1)
            .map((cell) => cell.trim()),
        );
        const filteredRows = tableRows.filter(
          (row) => !row.every((cell) => /^:?-+:?$/.test(cell)),
        );

        if (filteredRows.length > 0) {
          const headers = filteredRows[0];
          const dataRows = filteredRows.slice(1);

          return (
            <div
              key={idx}
              className="overflow-x-auto w-full my-4 rounded-lg border border-[var(--border-default)]"
            >
              <table className="min-w-full divide-y divide-[var(--border-default)] text-left text-xs">
                <thead className="bg-[var(--surface-2)]">
                  <tr>
                    {headers.map((header, hIdx) => (
                      <th
                        key={hIdx}
                        className="px-3 py-2.5 font-semibold text-[var(--text-primary)] border-b border-[var(--border-default)]"
                      >
                        {formatInline(header)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)] text-[var(--text-secondary)]">
                  {dataRows.map((row, rIdx) => (
                    <tr
                      key={rIdx}
                      className="hover:bg-[var(--surface-1)] transition-colors"
                    >
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="px-3 py-2.5 whitespace-nowrap">
                          {formatInline(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
      }

      // Unordered list
      const isUnorderedList = lines.every(
        (line) => line.startsWith('- ') || line.startsWith('* '),
      );
      if (isUnorderedList) {
        return (
          <ul
            key={idx}
            className="list-disc pl-5 my-3 space-y-1.5 text-[var(--text-secondary)] text-sm leading-relaxed marker:text-[var(--text-quaternary)]"
          >
            {lines.map((line, lIdx) => (
              <li key={lIdx}>{formatInline(line.substring(2))}</li>
            ))}
          </ul>
        );
      }

      // Ordered list
      const isOrderedList = lines.every((line) => /^\d+\.\s/.test(line));
      if (isOrderedList) {
        return (
          <ol
            key={idx}
            className="list-decimal pl-5 my-3 space-y-1.5 text-[var(--text-secondary)] text-sm leading-relaxed marker:text-[var(--text-tertiary)] marker:font-medium"
          >
            {lines.map((line, lIdx) => {
              const m = line.match(/^\d+\.\s(.*)/);
              const textContent = m ? m[1] : line;
              return <li key={lIdx}>{formatInline(textContent)}</li>;
            })}
          </ol>
        );
      }

      // Standard paragraph
      return (
        <p
          key={idx}
          className="text-[var(--text-secondary)] text-sm leading-relaxed whitespace-pre-line mb-2.5"
        >
          {formatInline(trimmedBlock)}
        </p>
      );
    });
  };

  return <div className="space-y-1">{parseBlocks()}</div>;
};
