import React, { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '@/lib/api';
import { Send, AlertTriangle, Bot, Square } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { MessageBubble } from './message-bubble';
import { TypingIndicator } from './typing-indicator';

interface ChatAreaProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  isLoading: boolean;
  threadTitle: string;
  selectedCitation: any | null;
  onSelectCitation: (citation: any) => void;
  onStopGeneration?: () => void;
  streamError?: string | null;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  onSendMessage,
  isLoading,
  threadTitle,
  selectedCitation,
  onSelectCitation,
  onStopGeneration,
  streamError,
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-resize textarea
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  // Check if streaming has started (last message is an assistant with content)
  const isStreaming =
    isLoading &&
    messages.length > 0 &&
    messages[messages.length - 1].role === 'assistant' &&
    !messages[messages.length - 1].content.startsWith('3:');

  // Waiting = loading but no assistant token yet
  const isWaiting = isLoading && !isStreaming;

  return (
    <div className="flex flex-col flex-1 bg-background text-foreground overflow-hidden h-full">
      {/* Header */}
      <div className="flex h-12 items-center px-5 border-b border-border shrink-0">
        <h3 className="text-xs font-medium text-muted-foreground truncate">
          {threadTitle}
        </h3>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1">
        <div className="max-w-3xl mx-auto p-6 space-y-5">
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              selectedCitation={selectedCitation}
              onCitationClick={onSelectCitation}
            />
          ))}

          {/* Stream Error */}
          {streamError && (
            <div className="flex gap-3 max-w-3xl mr-auto">
              <Avatar className="h-7 w-7 shrink-0 border border-destructive bg-destructive/10">
                <AvatarFallback className="bg-destructive/10 text-destructive">
                  <AlertTriangle size={14} />
                </AvatarFallback>
              </Avatar>
              <div className="rounded-xl px-4 py-3 border border-destructive bg-destructive/10 text-xs leading-relaxed space-y-1">
                <h5 className="font-medium text-destructive">
                  Processing Error
                </h5>
                <p className="text-muted-foreground">{streamError}</p>
              </div>
            </div>
          )}

          {/* Waiting indicator (before first token) */}
          {isWaiting && !streamError && (
            <div className="flex gap-3 max-w-3xl mr-auto">
              <Avatar className="h-7 w-7 shrink-0 border border-border bg-muted">
                <AvatarFallback className="bg-muted text-muted-foreground">
                  <Bot size={14} />
                </AvatarFallback>
              </Avatar>
              <div className="rounded-xl px-4 py-3 border border-border bg-muted/50">
                <TypingIndicator />
              </div>
            </div>
          )}

          {/* Skeleton for loading history */}
          {isLoading && messages.length === 0 && !streamError && (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-3">
                  <Skeleton className="h-7 w-7 rounded-full shrink-0" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input Bar */}
      <div className="p-4 bg-background shrink-0">
        <div className="relative max-w-3xl mx-auto">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
            className="w-full rounded-2xl border border-input bg-muted/50 px-4 py-3 pr-12 text-sm text-foreground placeholder-muted-foreground focus:border-ring focus:outline-none transition-colors resize-none shadow-sm"
            style={{ minHeight: '44px', maxHeight: '200px' }}
            placeholder="Ask about SEC filings..."
          />

          <div className="absolute right-2 bottom-2 flex items-center gap-1">
            {/* Stop button */}
            {isLoading && onStopGeneration && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onStopGeneration}
                className="h-8 w-8 text-muted-foreground hover:text-foreground rounded-full"
                aria-label="Stop generation"
              >
                <Square size={12} fill="currentColor" />
              </Button>
            )}

            {/* Send button */}
            <Button
              onClick={handleSubmit}
              disabled={isLoading || !input.trim()}
              size="icon"
              className="h-8 w-8 rounded-full shadow-md"
              aria-label="Send message"
            >
              <Send size={14} />
            </Button>
          </div>

          {/* Keyboard hint */}
          {!isLoading && (
            <div className="mt-2 flex items-center justify-center gap-1 text-[10px] text-muted-foreground">
              <kbd className="px-1.5 py-0.5 rounded-md border border-border bg-muted text-[9px] font-medium">
                Enter
              </kbd>{' '}
              to send ·{' '}
              <kbd className="px-1.5 py-0.5 rounded-md border border-border bg-muted text-[9px] font-medium">
                Shift + Enter
              </kbd>{' '}
              for newline
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
