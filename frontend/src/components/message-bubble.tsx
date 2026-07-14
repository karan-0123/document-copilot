import React, { useState } from 'react';
import type { ChatMessage } from '@/lib/api';
import { Bot, User, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { MarkdownRenderer } from './markdown-renderer';
import { CitationCard } from './citation-card';

interface MessageBubbleProps {
  message: ChatMessage;
  selectedCitation: any | null;
  onCitationClick: (citation: any) => void;
}

/**
 * Individual message bubble with avatar, content rendering,
 * citation list, and copy-to-clipboard action.
 */
export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  selectedCitation,
  onCitationClick,
}) => {
  const [copied, setCopied] = useState(false);
  const [citationsOpen, setCitationsOpen] = useState(false);
  const isAi = message.role === 'assistant';

  // Skip raw error parts from rendering
  if (isAi && message.content.startsWith('3:')) return null;

  const hasCitations =
    isAi && message.payload?.citations && message.payload.citations.length > 0;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCitationBadgeClick = (citationNum: number) => {
    if (message.payload?.citations) {
      const target = message.payload.citations.find(
        (c: any) => c.index === citationNum,
      );
      if (target) {
        onCitationClick({ ...target, messageId: message.id });
      }
    }
  };

  return (
    <div
      className={`flex gap-3 max-w-3xl ${isAi ? 'mr-auto' : 'ml-auto flex-row-reverse'}`}
    >
      {/* Avatar */}
      <Avatar className={`h-8 w-8 shrink-0 border ${isAi ? 'border-border bg-muted/50' : 'border-primary/20 bg-primary/10'}`}>
        <AvatarFallback className={isAi ? "bg-muted/50 text-muted-foreground" : "bg-primary/10 text-primary"}>
          {isAi ? <Bot size={16} /> : <User size={16} />}
        </AvatarFallback>
      </Avatar>

      {/* Content */}
      <div className="flex flex-col gap-2 max-w-full min-w-0">
        <div
          className={`group relative rounded-2xl px-5 py-3.5 transition-colors ${
            isAi
              ? 'bg-muted/30 border border-border text-foreground shadow-sm'
              : 'bg-primary text-primary-foreground shadow-md'
          }`}
        >
          {isAi ? (
            <MarkdownRenderer
              content={message.content}
              onCitationClick={handleCitationBadgeClick}
            />
          ) : (
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {message.content}
            </p>
          )}

          {/* Copy button — assistant messages only */}
          {isAi && message.content && (
            <button
              onClick={handleCopy}
              className="absolute -bottom-3 right-2 opacity-0 group-hover:opacity-100 flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-background border border-border text-[10px] text-muted-foreground hover:text-foreground transition-all shadow-sm"
            >
              {copied ? (
                <>
                  <Check size={12} /> Copied
                </>
              ) : (
                <>
                  <Copy size={12} /> Copy
                </>
              )}
            </button>
          )}
        </div>

        {/* Citation collapsible */}
        {hasCitations && (
          <Collapsible open={citationsOpen} onOpenChange={setCitationsOpen} className="mt-1">
            <div className="border border-border rounded-xl bg-muted/20 overflow-hidden shadow-sm">
              <CollapsibleTrigger className="flex items-center justify-between w-full px-3 py-2.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors">
                <span className="flex items-center gap-1.5">
                  Sources ({message.payload.citations.length})
                </span>
                {citationsOpen ? (
                  <ChevronUp size={14} />
                ) : (
                  <ChevronDown size={14} />
                )}
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="px-2 pb-2 space-y-1.5 border-t border-border pt-2 bg-background">
                  {message.payload.citations.map((c: any, idx: number) => {
                    const isSelected =
                      selectedCitation?.messageId === message.id &&
                      selectedCitation?.index === c.index;
                    return (
                      <CitationCard
                        key={idx}
                        index={c.index}
                        company={c.company}
                        filingType={c.filing_type}
                        year={c.year}
                        section={c.section}
                        page={c.page}
                        excerpt={c.excerpt}
                        isSelected={isSelected}
                        onClick={() =>
                          onCitationClick({ ...c, messageId: message.id })
                        }
                      />
                    );
                  })}
                </div>
              </CollapsibleContent>
            </div>
          </Collapsible>
        )}
      </div>
    </div>
  );
};
